"""Run from Source with python -m unittest discover -s tests -v."""
import itertools
import unittest
from dataclasses import replace
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

import models
from benchmark import run
from cnf_encoder import CNFEncoder
from dpll_solver import DPLLSolver
from engine import GameEngine, evaluate_clue_directly, load_puzzle, resolve_region, save_puzzle
from logic_agent import DeductiveAgent, SemanticSearch, uniqueness
from models import BINARY, Clue, SolverStats, Status, Verdict, board_ids
from puzzle_generator import CASES, PUZZLES, generate, region

C, I = Status.CRIMINAL, Status.INNOCENT


def clue(kind, **params):
    return Clue("test","A1",kind,params,kind)


class Semantics(unittest.TestCase):
    def test_rectangular_regions(self):
        def cells(kind, target=None):
            return set(resolve_region(region(kind,target), 5, 4))
        self.assertEqual(cells("CORNERS"), {"A1","D1","A5","D5"})
        self.assertEqual(len(cells("BOUNDARY")), 14)
        self.assertEqual(cells("NEIGHBORS","A1"), {"A2","B1","B2"})
        self.assertEqual(len(cells("NEIGHBORS","B2")), 8)
        self.assertEqual(cells("COMMON_NEIGHBORS",["A1","C1"]),{"B1","B2"})
        self.assertEqual(len(cells("COL","B")),5)
        self.assertEqual(len(cells("ROW",5)),4)
        self.assertEqual(cells("CELLS",["A2","B1","A2"]),{"A2","B1"})
        self.assertEqual(resolve_region(region("CORNERS"),1,1),("A1",))
        self.assertIn("AA2",board_ids(2,27))
        with self.assertRaises(ValueError):
            cells("COL","E")

    def test_all_predicates_against_arithmetic_and_partial_assignments(self):
        a,b,c = ids = board_ids(1,3)
        R = region("CELLS",[a,b])
        S = region("CELLS",[b,c])
        predicates = [
            (clue("FACT",target=b,status=C),lambda x,y,z:y),
            (clue("SAME",target1=a,target2=b),lambda x,y,z:x==y),
            (clue("DIFFERENT",target1=a,target2=c),lambda x,y,z:x!=z),
            (clue("EXACTLY",region=R,k=1),lambda x,y,z:x+y==1),
            (clue("AT_MOST",region=R,k=0),lambda x,y,z:x+y==0),
            (clue("AT_LEAST",region=R,k=2),lambda x,y,z:x+y==2),
            (clue("PARITY",region=R,parity="ODD"),lambda x,y,z:(x+y)%2==1),
            (clue("PARITY",region=region("CELLS",[]),parity="EVEN"),lambda x,y,z:True),
            (clue("COMPARE_REGIONS",region1=R,region2=S,op=">"),lambda x,y,z:x+y>y+z),
            (clue("COMPARE_REGIONS",region1=R,region2=S,op="<"),lambda x,y,z:x+y<y+z),
            (clue("COMPARE_REGIONS",region1=R,region2=S,op="=="),lambda x,y,z:x+y==y+z),
        ]
        for item, pred in predicates:
            search = SemanticSearch(1,3,[item])
            solutions = []
            for bits in itertools.product((False,True),repeat=3):
                states = {i:C if bit else I for i,bit in zip(ids,bits)}
                self.assertEqual(evaluate_clue_directly(item,states,1,3),bool(pred(*bits)))
                if pred(*bits):
                    solutions.append(states)
            for partial in itertools.product((None,I,C),repeat=3):
                known = {i:s for i,s in zip(ids,partial) if s}
                expected = any(all(m[i]==s for i,s in known.items()) for m in solutions)
                self.assertEqual(search.witness(known) is not None,expected)

    def test_uniqueness(self):
        f = clue("FACT",target="A1",status=C)
        self.assertTrue(uniqueness([f],1,1))
        self.assertFalse(uniqueness([f],1,2))
        self.assertFalse(uniqueness([f,clue("FACT",target="A1",status=I)],1,1))

    def test_validation(self):
        p = load_puzzle(PUZZLES/(CASES[0][0]+".json"))
        c = p.cells[0]
        opposite = I if c.true_status==C else C
        wrong = replace(c.clue,clue_type="FACT",params=dict(target=c.cell_id,status=opposite))
        with self.assertRaisesRegex(ValueError,"False clue"):
            GameEngine(replace(p,cells=(replace(c,clue=wrong),*p.cells[1:])))
        with self.assertRaises(ValueError):
            CNFEncoder(1,1).encode_clue(clue("EXACTLY",region=region("ROW",1),k=2))


class Gameplay(unittest.TestCase):
    def setUp(self):
        self.puzzle = load_puzzle(PUZZLES/(CASES[1][0]+".json"))
        self.engine = GameEngine(self.puzzle)
        self.agent = DeductiveAgent(self.engine)

    def test_public_boundary_and_verdicts(self):
        state = self.engine.public_state()
        self.assertFalse(any(hasattr(p,"true_status") or hasattr(p,"clue") for p in state.people))
        self.assertEqual(set(state.known),{c.owner_cell for c in state.clues})
        candidates = {p.cell_id:self.agent.classify(state,p.cell_id) for p in state.people if p.cell_id not in state.known}
        unknown = next(i for i,s in candidates.items() if s==Status.UNKNOWN)
        hidden_true = next(c.true_status for c in self.puzzle.cells if c.cell_id==unknown)
        self.assertEqual(self.agent.submit(unknown,hidden_true),Verdict.NOT_PROVABLE)
        hint = self.agent.get_hint()
        self.assertEqual(self.agent.submit(hint.cell_id,I if hint.status==C else C),Verdict.CONTRADICTED)
        self.assertEqual(self.engine.public_state(),state)
        for single in state.clues:
            self.assertEqual(self.agent.classify(replace(state,clues=(single,)),hint.cell_id),Status.UNKNOWN)
        self.assertEqual(self.agent.submit(hint.cell_id,hint.status),Verdict.ACCEPTED)
        self.assertEqual(self.agent.submit(hint.cell_id,hint.status),Verdict.ALREADY_REVEALED)
        self.assertEqual(len(self.agent.trace.entries),1)

    def test_inconsistent_public_kb(self):
        state = self.engine.public_state()
        k,s = next(iter(state.known.items()))
        false_fact = clue("FACT",target=k,status=I if s==C else C)
        broken = replace(state,clues=(*state.clues,false_fact))
        self.assertEqual(self.agent.classify(broken,k),Status.INCONSISTENT)

    def test_fallback_selection_and_strict_mode(self):
        state = self.engine.public_state()
        with patch("logic_agent.classify_cell",return_value=(C,SolverStats(mode="DPLL",sat_calls=2))):
            self.assertEqual(self.agent.classify(state,"A1"),C)
            self.assertEqual(self.agent.stats.sat_calls,2)
        with patch("logic_agent.classify_cell",side_effect=NotImplementedError), patch.object(models,"USE_FALLBACK_WHEN_TODO_NOT_IMPLEMENTED",False):
            with self.assertRaises(NotImplementedError):
                self.agent.classify(state,"B1")

    def test_eight_shipped_cases(self):
        for key,*_ in CASES:
            with self.subTest(key=key):
                result = run(PUZZLES/(key+".json"))
                self.assertTrue(result["solved"])
                puzzle = load_puzzle(PUZZLES/(key+".json"))
                self.assertTrue(uniqueness([c.clue for c in puzzle.cells], puzzle.num_rows, puzzle.num_cols))
                self.assertEqual(result["deductions"]+result["initial"],result["total"])

    def test_generation_and_round_trip(self):
        for shape in ((1,1),(2,3),(3,3),(4,4),(5,4),(4,5),(5,5)):
            for ext in (False,True):
                with self.subTest(shape=shape,extensions=ext):
                    p = generate(*shape,77,extensions=ext)
                    self.assertEqual(p,generate(*shape,77,extensions=ext))
                    with TemporaryDirectory() as d:
                        path=Path(d)/"case.json"
                        save_puzzle(p,path)
                        self.assertEqual(p,load_puzzle(path))

    def test_cnf_interface_without_student_algorithms(self):
        enc = CNFEncoder(5,4)
        self.assertEqual(enc.cell_to_var["D5"],20)
        self.assertEqual(enc.var_to_cell[6],"B2")
        state = replace(self.engine.public_state(),known={"B2":C},clues=(clue("FACT",target="D5",status=I),))
        self.assertEqual(enc.build_kb(state),[[6],[-20]])
        self.assertEqual((enc.num_clauses,enc.fresh_var(),enc.aux_vars),(2,21,1))
        enc.build_kb(state)
        self.assertEqual(enc.aux_vars,0)
        with self.assertRaises(ValueError):
            DPLLSolver().solve([[0]],1)
