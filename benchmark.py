"""Replay each case through the agent; optional CSV uses the same fields as stdout."""
import argparse
import csv
import sys
from pathlib import Path
from time import perf_counter

import models
from engine import GameEngine, load_puzzle
from logic_agent import DeductiveAgent
from puzzle_generator import CASES, PUZZLES


def run(path):
    puzzle = load_puzzle(path)
    engine = GameEngine(puzzle)
    agent = DeductiveAgent(engine)
    starters = len(engine.public_state().known)
    start = perf_counter()
    solved = agent.auto_solve()
    wall_ms = 1000*(perf_counter()-start)
    state = engine.public_state()
    stats = agent.stats
    return dict(case=puzzle.puzzle_id, grid=f"{puzzle.num_rows}x{puzzle.num_cols}",
                mode=stats.mode, initial=starters, deductions=len(agent.trace.entries),
                revealed=len(state.known), total=len(state.people), solved=solved,
                primary_vars=stats.primary_vars, aux_vars=stats.aux_vars,
                cnf_clauses=stats.cnf_clauses, sat_calls=stats.sat_calls,
                decisions=stats.decisions, propagations=stats.propagations, backtracks=stats.backtracks,
                inference_ms=round(stats.runtime_sec*1000,3), wall_ms=round(wall_ms,3))


def write_csv(rows, stream):
    writer = csv.DictWriter(stream,fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv",type=Path)
    parser.add_argument("--require-dpll", action="store_true",
                        help="Disable the semantic fallback for the experiment.")
    args = parser.parse_args()
    if args.require_dpll:
        models.USE_FALLBACK_WHEN_TODO_NOT_IMPLEMENTED = False
    results = [run(PUZZLES / (case[0]+".json")) for case in CASES]
    write_csv(results, sys.stdout)
    if args.csv:
        with args.csv.open("w",newline="",encoding="utf-8") as file:
            write_csv(results,file)
    sys.exit(0 if all(row["solved"] for row in results) else 1)
