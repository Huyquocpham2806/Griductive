"""Deduction-guided puzzle generator producing natural, multi-clue Griductive cases."""
from __future__ import annotations

import argparse
from collections import Counter, deque
from dataclasses import dataclass
from math import comb
from pathlib import Path
import random

from engine import GameEngine, clue_groups, resolve_region, save_puzzle, validate_puzzle
from logic_agent import DeductiveAgent
from models import BINARY, ROSTER, Cell, Clue, Puzzle, Status, board_ids, column_label

PUZZLES = Path(__file__).resolve().parent / "puzzles"
CASES = (
    ("01_classic_5x4_normal", 5, 4, "The Column B Inquiry", "Normal", False),
    ("02_classic_5x4_hard", 5, 4, "Two Witnesses", "Hard", True),
    ("03_grid_3x3_easy", 3, 3, "The First Witness", "Easy", False),
    ("04_grid_3x3_extensions", 3, 3, "Odd Company", "Medium", True),
    ("05_grid_4x4_medium", 4, 4, "The Corner Office", "Medium", False),
    ("06_grid_4x4_hard", 4, 4, "A Shared Alibi", "Hard", True),
    ("07_grid_5x5_stress_1", 5, 5, "The Night Shift", "Stress", False),
    ("08_grid_5x5_stress_2", 5, 5, "The Last Comparison", "Stress", True),
)

MAX_CLUE_CLAUSES = 180
MAX_COMPARE_DIFF = 8
MAX_PARITY_SIZE = 7
MAX_PARITY_UNKNOWN = 4

DIFFICULTY_PROFILES = {
    "Easy": {
        "synergy_rate": 0.15,
        "chain_bonus": 1.5,
        "multi_bonus": 2.0,
        "prefer_simple": True,
        "allow_boundary": False,
        "allow_parity_base": False,
    },
    "Normal": {
        "synergy_rate": 0.40,
        "chain_bonus": 5.0,
        "multi_bonus": 3.5,
        "prefer_simple": False,
        "allow_boundary": True,
        "allow_parity_base": False,
    },
    "Medium": {
        "synergy_rate": 0.60,
        "chain_bonus": 7.0,
        "multi_bonus": 4.0,
        "prefer_simple": False,
        "allow_boundary": True,
        "allow_parity_base": False,
    },
    "Hard": {
        "synergy_rate": 0.85,
        "chain_bonus": 9.5,
        "multi_bonus": 4.5,
        "prefer_simple": False,
        "allow_boundary": True,
        "allow_parity_base": False,
    },
    "Stress": {
        "synergy_rate": 0.85,
        "chain_bonus": 9.5,
        "multi_bonus": 4.5,
        "prefer_simple": False,
        "allow_boundary": True,
        "allow_parity_base": False,
    },
}


def region(kind, target=None):
    return {"region_type": kind, "target": target}


def region_name(r):
    kind, t = r["region_type"], r["target"]
    if kind == "CELLS":
        return "{" + ", ".join(t) + "}"
    if kind == "COMMON_NEIGHBORS":
        return f"common neighbors of {t[0]} and {t[1]}"
    if kind == "NEIGHBORS":
        return f"neighbors of {t}"
    return kind.lower() if t is None else f"{kind.lower()} {t}"


@dataclass(frozen=True)
class _NamedRegion:
    spec: dict
    cells: frozenset[str]
    category: str
    meta: object = None


@dataclass(frozen=True)
class _Candidate:
    clue_type: str
    params: dict
    text: str
    scope: frozenset[str]
    category: str
    region_key: object
    cnf_cost: int
    natural_score: float


def _opposite(status: Status) -> Status:
    return Status.INNOCENT if status == Status.CRIMINAL else Status.CRIMINAL


def _possessive(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _person_label(cid: str, roster_map: dict[str, tuple[str, str]]) -> str:
    name, _ = roster_map[cid]
    if name.startswith("Resident "):
        return cid
    return f"{name} ({cid})"


def _plural_prof(prof: str) -> str:
    return f"{prof}s"


def _cnf_cost(clue_type: str, params: dict, rows: int, cols: int) -> int:
    if clue_type == "FACT":
        return 1
    if clue_type in ("SAME", "DIFFERENT"):
        return 2
    if clue_type == "PARITY":
        n = len(resolve_region(params["region"], rows, cols))
        return 1 if n <= 1 else 4 * (n - 1) + 1
    if clue_type in ("EXACTLY", "AT_LEAST", "AT_MOST"):
        n = len(resolve_region(params["region"], rows, cols))
        k = params["k"]
        at_most = 0 if k >= n else (1 if k < 0 else comb(n, k + 1))
        at_least = 0 if k <= 0 else (1 if k > n else comb(n, n - k + 1))
        if clue_type == "AT_MOST":
            return at_most
        if clue_type == "AT_LEAST":
            return at_least
        return at_most + at_least
    if clue_type == "COMPARE_REGIONS":
        r1 = set(resolve_region(params["region1"], rows, cols))
        r2 = set(resolve_region(params["region2"], rows, cols))
        a, b = len(r1 - r2), len(r2 - r1)
        m = a + b
        op = params["op"]
        if op == "==":
            k = b
            at_most = 0 if k >= m else comb(m, k + 1)
            at_least = 0 if k <= 0 else comb(m, m - k + 1)
            return at_most + at_least
        if op == ">":
            k = b + 1
            return 1 if k > m else (0 if k <= 0 else comb(m, m - k + 1))
        k = b - 1
        return 1 if k < 0 else (0 if k >= m else comb(m, k + 1))
    return 999999


def _compare_subject(nr: _NamedRegion, roster_map: dict[str, tuple[str, str]]) -> tuple[str, str, bool]:
    """Return (Capitalized subject, lowercase subject, is_plural)."""
    cat, meta = nr.category, nr.meta
    if cat == "ROW":
        return f"Row {meta}", f"row {meta}", False
    if cat == "COL":
        return f"Column {meta}", f"column {meta}", False
    if cat == "PROFESSION":
        pl = _plural_prof(meta)
        return f"The {pl}", f"the {pl}", True
    if cat == "CORNERS":
        return "The corners", "the corners", True
    if cat == "BOUNDARY":
        return "The edges", "the edges", True
    if cat == "NEIGHBORS":
        return f"{meta}'s neighbors", f"{meta}'s neighbors", True
    if cat == "COMMON_NEIGHBORS":
        u, v = meta
        return f"{u} & {v}'s common neighbors", f"{u} & {v}'s common neighbors", True
    cells = sorted(nr.cells)
    lbl = "{" + ", ".join(cells) + "}"
    return lbl, lbl, True


def _format_region_clue(nr: _NamedRegion, kind: str, k: int | None, parity: str | None,
                        roster_map: dict[str, tuple[str, str]]) -> str:
    cat, meta, size = nr.category, nr.meta, len(nr.cells)

    if cat == "PROFESSION":
        sg, pl = meta, _plural_prof(meta)
        all_word = "Both" if size == 2 else "All"
        if kind == "EXACTLY":
            if k == 0:
                return f"{all_word} {pl} are innocent."
            if k == size:
                return f"{all_word} {pl} are criminals."
            return f"Exactly 1 {sg} is a criminal." if k == 1 else f"Exactly {k} {pl} are criminals."
        if kind == "AT_LEAST":
            return f"At least 1 {sg} is a criminal." if k == 1 else f"At least {k} {pl} are criminals."
        if kind == "AT_MOST":
            return f"At most 1 {sg} is a criminal." if k == 1 else f"At most {k} {pl} are criminals."
        art = "An odd" if parity == "ODD" else "An even"
        return f"{art} number of {pl} are criminals."

    if cat in ("ROW", "COL"):
        name_cap = f"Row {meta}" if cat == "ROW" else f"Column {meta}"
        name_lo = name_cap.lower()
        if kind == "EXACTLY":
            if k == 0:
                return f"{name_cap} has no criminals."
            if k == size:
                return f"Everyone in {name_lo} is a criminal."
            return f"{name_cap} has exactly {k} {'criminal' if k == 1 else 'criminals'}."
        if kind == "AT_LEAST":
            return f"{name_cap} has at least {k} {'criminal' if k == 1 else 'criminals'}."
        if kind == "AT_MOST":
            return f"{name_cap} has at most {k} {'criminal' if k == 1 else 'criminals'}."
        art = "an odd" if parity == "ODD" else "an even"
        return f"{name_cap} has {art} number of criminals."

    if cat == "NEIGHBORS":
        cid = meta
        name, _ = roster_map[cid]
        who = _person_label(cid, roster_map)
        who_poss = f"{cid}'s" if name.startswith("Resident ") else f"{_possessive(name)} ({cid})"
        if kind == "EXACTLY":
            if k == 0:
                return f"None of {who_poss} neighbors are criminals."
            if k == size:
                return f"All of {who_poss} neighbors are criminals."
            return f"{who} has exactly {k} criminal {'neighbor' if k == 1 else 'neighbors'}."
        if kind == "AT_LEAST":
            return f"{who} has at least {k} criminal {'neighbor' if k == 1 else 'neighbors'}."
        if kind == "AT_MOST":
            return f"{who} has at most {k} criminal {'neighbor' if k == 1 else 'neighbors'}."
        art = "an odd" if parity == "ODD" else "an even"
        return f"{who} has {art} number of criminal neighbors."

    if cat == "COMMON_NEIGHBORS":
        u, v = meta
        if kind == "EXACTLY":
            if k == 0:
                return f"{u} and {v} share no criminal neighbors."
            if k == size:
                return f"All common neighbors of {u} & {v} are criminals."
            return f"{u} and {v} share exactly {k} criminal {'neighbor' if k == 1 else 'neighbors'}."
        if kind == "AT_LEAST":
            return f"{u} and {v} share at least {k} criminal {'neighbor' if k == 1 else 'neighbors'}."
        if kind == "AT_MOST":
            return f"{u} and {v} share at most {k} criminal {'neighbor' if k == 1 else 'neighbors'}."
        art = "an odd" if parity == "ODD" else "an even"
        return f"{u} and {v} share {art} number of criminal neighbors."

    if cat == "CORNERS":
        if kind == "EXACTLY":
            if k == 0:
                return "All corners are innocent."
            if k == size:
                return "All corners are criminals."
            return "Exactly 1 corner is a criminal." if k == 1 else f"Exactly {k} corners are criminals."
        if kind == "AT_LEAST":
            return "At least 1 corner is a criminal." if k == 1 else f"At least {k} corners are criminals."
        if kind == "AT_MOST":
            return "At most 1 corner is a criminal." if k == 1 else f"At most {k} corners are criminals."
        art = "An odd" if parity == "ODD" else "An even"
        return f"{art} number of corners are criminals."

    if cat == "BOUNDARY":
        if kind == "EXACTLY":
            if k == 0:
                return "No one on the edges is a criminal."
            if k == size:
                return "Everyone on the edges is a criminal."
            return f"The edges have exactly {k} {'criminal' if k == 1 else 'criminals'}."
        if kind == "AT_LEAST":
            return f"The edges have at least {k} {'criminal' if k == 1 else 'criminals'}."
        if kind == "AT_MOST":
            return f"The edges have at most {k} {'criminal' if k == 1 else 'criminals'}."
        art = "an odd" if parity == "ODD" else "an even"
        return f"The edges have {art} number of criminals."

    cells = sorted(nr.cells)
    joined = f"{cells[0]} and {cells[1]}" if len(cells) == 2 else ", ".join(cells)
    if kind == "EXACTLY":
        if k == 0:
            return f"None of {joined} are criminals."
        if k == size:
            return f"All of {joined} are criminals."
        return f"Exactly 1 of {joined} is a criminal." if k == 1 else f"Exactly {k} of {joined} are criminals."
    if kind == "AT_LEAST":
        return f"At least 1 of {joined} is a criminal." if k == 1 else f"At least {k} of {joined} are criminals."
    if kind == "AT_MOST":
        return f"At most 1 of {joined} is a criminal." if k == 1 else f"At most {k} of {joined} are criminals."
    art = "An odd" if parity == "ODD" else "An even"
    return f"{art} number of {joined} are criminals."


def _format_compare_clue(r1: _NamedRegion, r2: _NamedRegion, op: str,
                         roster_map: dict[str, tuple[str, str]]) -> str:
    if r1.category == "PROFESSION" and r2.category == "PROFESSION":
        p1, p2 = _plural_prof(r1.meta), _plural_prof(r2.meta)
        if op == ">":
            return f"More {p1} than {p2} are criminals."
        if op == "<":
            return f"Fewer {p1} than {p2} are criminals."
        return f"{p1} and {p2} have equally many criminals."
    s1_cap, _, plural1 = _compare_subject(r1, roster_map)
    _, s2_lo, _ = _compare_subject(r2, roster_map)
    verb = "have" if plural1 else "has"
    if op == ">":
        return f"{s1_cap} {verb} more criminals than {s2_lo}."
    if op == "<":
        return f"{s1_cap} {verb} fewer criminals than {s2_lo}."
    return f"{s1_cap} and {s2_lo} have equally many criminals."


def _format_pair_clue(a: str, b: str, same: bool, roster_map: dict[str, tuple[str, str]]) -> str:
    la, lb = _person_label(a, roster_map), _person_label(b, roster_map)
    if same:
        return f"{la} and {lb} share the same status."
    return f"{la} and {lb} have opposite statuses."


def _format_fact_clue(target: str, status: Status, roster_map: dict[str, tuple[str, str]]) -> str:
    who = _person_label(target, roster_map)
    return f"{who} is {'a criminal' if status == Status.CRIMINAL else 'innocent'}."


def _compile_constraint(clue_type: str, params: dict, rows: int, cols: int):
    """Precompile a clue into a lightweight tuple for fast propagation & backtracking."""
    if clue_type == "FACT":
        return ("FACT", params["target"], Status(params["status"]))
    if clue_type in ("SAME", "DIFFERENT"):
        return (clue_type, params["target1"], params["target2"])
    if clue_type == "COMPARE_REGIONS":
        g1 = set(resolve_region(params["region1"], rows, cols))
        g2 = set(resolve_region(params["region2"], rows, cols))
        return ("COMPARE_REGIONS", params["op"], tuple(sorted(g1 - g2)), tuple(sorted(g2 - g1)))
    grp = resolve_region(params["region"], rows, cols)
    if clue_type == "PARITY":
        return ("PARITY", 1 if params["parity"] == "ODD" else 0, grp)
    return (clue_type, params["k"], grp)


def _constraint_scope(compiled) -> tuple[str, ...]:
    kind = compiled[0]
    if kind == "FACT":
        return (compiled[1],)
    if kind in ("SAME", "DIFFERENT"):
        return (compiled[1], compiled[2])
    if kind == "COMPARE_REGIONS":
        return compiled[2] + compiled[3]
    return compiled[2]


def _propagate(constraints, assignment: dict[str, Status]) -> bool:
    """Sound constraint propagation to fixed point; mutates assignment and returns False on conflict."""
    changed = True
    while changed:
        changed = False
        for item in constraints:
            kind = item[0]
            if kind == "FACT":
                _, target, want = item
                cur = assignment.get(target)
                if cur is None:
                    assignment[target] = want
                    changed = True
                elif cur != want:
                    return False
            elif kind == "SAME":
                _, a, b = item
                sa, sb = assignment.get(a), assignment.get(b)
                if sa is not None and sb is not None:
                    if sa != sb:
                        return False
                elif sa is not None:
                    assignment[b] = sa
                    changed = True
                elif sb is not None:
                    assignment[a] = sb
                    changed = True
            elif kind == "DIFFERENT":
                _, a, b = item
                if a == b:
                    return False
                sa, sb = assignment.get(a), assignment.get(b)
                if sa is not None and sb is not None:
                    if sa == sb:
                        return False
                elif sa is not None:
                    assignment[b] = _opposite(sa)
                    changed = True
                elif sb is not None:
                    assignment[a] = _opposite(sb)
                    changed = True
            elif kind in ("EXACTLY", "AT_MOST", "AT_LEAST"):
                _, k, grp = item
                crim = 0
                unk = []
                for cid in grp:
                    st = assignment.get(cid)
                    if st is None:
                        unk.append(cid)
                    elif st == Status.CRIMINAL:
                        crim += 1
                rem = len(unk)
                if kind == "EXACTLY":
                    if crim > k or crim + rem < k:
                        return False
                    if rem:
                        if crim == k:
                            for cid in unk:
                                assignment[cid] = Status.INNOCENT
                            changed = True
                        elif crim + rem == k:
                            for cid in unk:
                                assignment[cid] = Status.CRIMINAL
                            changed = True
                elif kind == "AT_MOST":
                    if crim > k:
                        return False
                    if rem and crim == k:
                        for cid in unk:
                            assignment[cid] = Status.INNOCENT
                        changed = True
                else:
                    if crim + rem < k:
                        return False
                    if rem and crim + rem == k:
                        for cid in unk:
                            assignment[cid] = Status.CRIMINAL
                        changed = True
            elif kind == "PARITY":
                _, want, grp = item
                crim = 0
                unk = []
                for cid in grp:
                    st = assignment.get(cid)
                    if st is None:
                        unk.append(cid)
                    elif st == Status.CRIMINAL:
                        crim += 1
                if not unk:
                    if (crim & 1) != want:
                        return False
                elif len(unk) == 1:
                    assignment[unk[0]] = Status.CRIMINAL if (crim & 1) != want else Status.INNOCENT
                    changed = True
            else:  # COMPARE_REGIONS
                _, op, a_grp, b_grp = item
                ca = 0
                ua = []
                for cid in a_grp:
                    st = assignment.get(cid)
                    if st is None:
                        ua.append(cid)
                    elif st == Status.CRIMINAL:
                        ca += 1
                cb = 0
                ub = []
                for cid in b_grp:
                    st = assignment.get(cid)
                    if st is None:
                        ub.append(cid)
                    elif st == Status.CRIMINAL:
                        cb += 1
                lo = ca - (cb + len(ub))
                hi = (ca + len(ua)) - cb
                if op == ">":
                    if hi < 1:
                        return False
                    if hi == 1 and (ua or ub):
                        for cid in ua:
                            assignment[cid] = Status.CRIMINAL
                        for cid in ub:
                            assignment[cid] = Status.INNOCENT
                        changed = True
                elif op == "<":
                    if lo > -1:
                        return False
                    if lo == -1 and (ua or ub):
                        for cid in ua:
                            assignment[cid] = Status.INNOCENT
                        for cid in ub:
                            assignment[cid] = Status.CRIMINAL
                        changed = True
                else:
                    if lo > 0 or hi < 0:
                        return False
                    if lo == 0 and (ua or ub):
                        for cid in ua:
                            assignment[cid] = Status.INNOCENT
                        for cid in ub:
                            assignment[cid] = Status.CRIMINAL
                        changed = True
                    elif hi == 0 and (ua or ub):
                        for cid in ua:
                            assignment[cid] = Status.CRIMINAL
                        for cid in ub:
                            assignment[cid] = Status.INNOCENT
                        changed = True
    return True


def _find_witness(constraints, order: tuple[str, ...], facts: dict[str, Status]) -> dict[str, Status] | None:
    """Exact witness search with constraint propagation at every node."""
    base = dict(facts)
    if not _propagate(constraints, base):
        return None

    def backtrack(assign: dict[str, Status]) -> dict[str, Status] | None:
        var = next((v for v in order if v not in assign), None)
        if var is None:
            return assign
        for st in BINARY:
            branch = assign.copy()
            branch[var] = st
            if _propagate(constraints, branch):
                sol = backtrack(branch)
                if sol is not None:
                    return sol
        return None

    return backtrack(base)


class _FastDeductor:
    """Backbone & uniqueness engine exploiting ground truth for witness filtering."""

    def __init__(self, rows: int, cols: int, truth: dict[str, Status]):
        self.rows = rows
        self.cols = cols
        self.truth = truth
        self.all_ids = board_ids(rows, cols)

    def forced_cells(self, known: set[str], compiled_clues: list) -> set[str]:
        active = []
        freq = Counter()
        for item in compiled_clues:
            scope = _constraint_scope(item)
            unk = [cid for cid in scope if cid not in known]
            if unk:
                active.append(item)
                freq.update(unk)
        if not active:
            return set()

        base = {cid: self.truth[cid] for cid in known}
        if not _propagate(active, base):
            raise RuntimeError("Inconsistent generated clue set")

        forced = {cid for cid in base if cid not in known}
        order = tuple(sorted((v for v in freq if v not in base), key=lambda v: (-freq[v], v)))
        remaining = list(order)

        while remaining:
            cid = remaining.pop(0)
            if cid in base:
                continue
            probe = base.copy()
            probe[cid] = _opposite(self.truth[cid])
            model = _find_witness(active, order, probe)
            if model is None:
                forced.add(cid)
                base[cid] = self.truth[cid]
                _propagate(active, base)
                forced.update(v for v in base if v not in known)
            else:
                remaining = [v for v in remaining if model.get(v) == self.truth[v]]
        return forced

    def find_alt_model(self, compiled_clues: list, priority_ids: list[str] | None = None) -> dict[str, Status] | None:
        freq = Counter()
        for item in compiled_clues:
            freq.update(_constraint_scope(item))
        # Any unmentioned cell automatically breaks uniqueness.
        unmentioned = [cid for cid in self.all_ids if cid not in freq]
        if unmentioned:
            alt = dict(self.truth)
            alt[unmentioned[0]] = _opposite(self.truth[unmentioned[0]])
            return alt

        order = tuple(sorted(freq, key=lambda v: (-freq[v], v)))
        check_order = list(dict.fromkeys((priority_ids or []) + list(self.all_ids)))
        for cid in check_order:
            model = _find_witness(compiled_clues, order, {cid: _opposite(self.truth[cid])})
            if model is not None:
                for v in self.all_ids:
                    model.setdefault(v, self.truth[v])
                return model
        return None


def _build_region_catalog(num_rows: int, num_cols: int, ids: tuple[str, ...],
                          roster_map: dict[str, tuple[str, str]],
                          allow_boundary: bool) -> list[_NamedRegion]:
    catalog: list[_NamedRegion] = []
    seen_specs: set[tuple] = set()

    def add(spec: dict, category: str, meta=None):
        cells = frozenset(resolve_region(spec, num_rows, num_cols))
        if len(cells) < 2:
            return
        key = (category, cells)
        if key in seen_specs:
            return
        seen_specs.add(key)
        catalog.append(_NamedRegion(spec, cells, category, meta))

    for r in range(1, num_rows + 1):
        add(region("ROW", r), "ROW", r)
    for c in range(1, num_cols + 1):
        lbl = column_label(c)
        add(region("COL", lbl), "COL", lbl)

    if num_rows >= 2 and num_cols >= 2:
        add(region("CORNERS"), "CORNERS", None)
    if allow_boundary and num_rows >= 3 and num_cols >= 3:
        add(region("BOUNDARY"), "BOUNDARY", None)

    for cid in ids:
        add(region("NEIGHBORS", cid), "NEIGHBORS", cid)

    # Real common-neighbor pairs that actually share 2..4 neighbors.
    nbr_map = {cid: frozenset(resolve_region(region("NEIGHBORS", cid), num_rows, num_cols)) for cid in ids}
    seen_common: set[frozenset[str]] = set()
    for idx, u in enumerate(ids):
        nu = nbr_map[u]
        for v in ids[idx + 1:]:
            common = nu & nbr_map[v]
            if 2 <= len(common) <= 4 and common not in seen_common:
                seen_common.add(common)
                add(region("COMMON_NEIGHBORS", [u, v]), "COMMON_NEIGHBORS", (u, v))

    # Profession groups encoded transparently via CELLS.
    by_prof: dict[str, list[str]] = {}
    for cid in ids:
        _, prof = roster_map[cid]
        by_prof.setdefault(prof, []).append(cid)
    for prof, members in sorted(by_prof.items()):
        if 2 <= len(members) <= 6:
            add(region("CELLS", members), "PROFESSION", prof)

    return catalog


def _build_meaningful_pairs(num_rows: int, num_cols: int, ids: tuple[str, ...],
                            roster_map: dict[str, tuple[str, str]]) -> list[tuple[str, str, float]]:
    """Return pairs (a, b, natural_bonus) related by adjacency, row/col, or profession."""
    coords = {cid: divmod(idx, num_cols) for idx, cid in enumerate(ids)}
    pairs: list[tuple[str, str, float]] = []
    for i, a in enumerate(ids):
        ra, ca = coords[a]
        pa = roster_map[a][1]
        for b in ids[i + 1:]:
            rb, cb = coords[b]
            pb = roster_map[b][1]
            dist = max(abs(ra - rb), abs(ca - cb))
            if dist == 1:
                pairs.append((a, b, 2.6))
            elif pa == pb:
                pairs.append((a, b, 2.3))
            elif ra == rb or ca == cb:
                pairs.append((a, b, 1.9))
    return pairs


def _build_compare_pairs(catalog: list[_NamedRegion], num_rows: int, num_cols: int,
                         rng: random.Random) -> list[tuple[_NamedRegion, _NamedRegion]]:
    """Preselect clean, compact pairs of named regions for COMPARE_REGIONS."""
    eligible = [
        nr for nr in catalog
        if nr.category in ("ROW", "COL", "PROFESSION", "CORNERS", "NEIGHBORS", "COMMON_NEIGHBORS")
        and 2 <= len(nr.cells) <= 5
    ]
    pairs: list[tuple[_NamedRegion, _NamedRegion]] = []
    for i, r1 in enumerate(eligible):
        for r2 in eligible[i + 1:]:
            if r1.cells <= r2.cells or r2.cells <= r1.cells:
                continue
            diff = len(r1.cells ^ r2.cells)
            if diff < 2 or diff > MAX_COMPARE_DIFF:
                continue
            # Prefer intuitive pairings (row vs row, col vs col, row vs col, prof vs prof/row/col).
            cats = {r1.category, r2.category}
            if cats <= {"ROW", "COL"} or cats == {"PROFESSION"} or (
                "PROFESSION" in cats and cats & {"ROW", "COL", "CORNERS"}
            ) or ("CORNERS" in cats and cats & {"ROW", "COL"}) or (
                cats <= {"NEIGHBORS", "ROW", "COL"} and diff <= 7
            ):
                pairs.append((r1, r2))
    rng.shuffle(pairs)
    return pairs[:220]


def _canonical_key(clue_type: str, params: dict) -> tuple:
    if clue_type == "FACT":
        return ("FACT", params["target"], str(params["status"]))
    if clue_type in ("SAME", "DIFFERENT"):
        a, b = sorted((params["target1"], params["target2"]))
        return (clue_type, a, b)
    if clue_type == "COMPARE_REGIONS":
        r1 = (params["region1"]["region_type"], str(params["region1"]["target"]))
        r2 = (params["region2"]["region_type"], str(params["region2"]["target"]))
        return ("COMPARE_REGIONS", params["op"], r1, r2)
    reg = (params["region"]["region_type"], str(params["region"]["target"]))
    if clue_type == "PARITY":
        return ("PARITY", params["parity"], reg)
    return (clue_type, params["k"], reg)


def _generate_candidates(
    known: set[str],
    catalog: list[_NamedRegion],
    meaningful_pairs: list[tuple[str, str, float]],
    compare_pairs: list[tuple[_NamedRegion, _NamedRegion]],
    truth: dict[str, Status],
    roster_map: dict[str, tuple[str, str]],
    num_rows: int,
    num_cols: int,
    extensions: bool,
    used_clue_keys: set[tuple],
    profile: dict,
    rng: random.Random,
) -> tuple[list[_Candidate], list[_Candidate]]:
    """Return (direct_or_chaining_candidates, partial_candidates_for_synergy)."""
    direct_pool: list[_Candidate] = []
    partial_pool: list[_Candidate] = []

    cat_base_score = {
        "PROFESSION": 5.6,
        "ROW": 5.3,
        "COL": 5.3,
        "NEIGHBORS": 5.1,
        "COMMON_NEIGHBORS": 4.7,
        "CORNERS": 5.0,
        "BOUNDARY": 3.2,
    }

    for nr in catalog:
        unk = nr.cells - known
        u = len(unk)
        if u == 0:
            continue
        n = len(nr.cells)
        if nr.category == "BOUNDARY" and u > 4:
            continue
        if u > 5:
            continue

        k = sum(truth[c] == Status.CRIMINAL for c in nr.cells)
        ku = sum(truth[c] == Status.CRIMINAL for c in unk)
        base_nat = cat_base_score.get(nr.category, 3.0)

        def push(ctype: str, params: dict, text: str, nat: float, is_direct: bool):
            key = _canonical_key(ctype, params)
            if key in used_clue_keys:
                return
            cost = _cnf_cost(ctype, params, num_rows, num_cols)
            if cost > MAX_CLUE_CLAUSES:
                return
            cand = _Candidate(ctype, params, text, nr.cells, nr.category, (nr.category, nr.cells), cost, nat)
            if is_direct:
                direct_pool.append(cand)
            else:
                partial_pool.append(cand)

        # EXACTLY
        ex_params = {"k": k, "region": nr.spec}
        ex_text = _format_region_clue(nr, "EXACTLY", k, None, roster_map)
        is_direct_ex = (u == 1) or (ku == 0) or (ku == u)
        ex_nat = base_nat + (0.6 if (ku == 0 or ku == u) and u >= 2 else 0.0)
        push("EXACTLY", ex_params, ex_text, ex_nat, is_direct_ex)

        # Tight AT_LEAST / AT_MOST (skip trivial 0 and n bounds)
        if 0 < k < n:
            if ku == u:
                al_params = {"k": k, "region": nr.spec}
                al_text = _format_region_clue(nr, "AT_LEAST", k, None, roster_map)
                push("AT_LEAST", al_params, al_text, base_nat - 0.15, True)
            elif u <= 4 and ku >= 1:
                al_params = {"k": k, "region": nr.spec}
                al_text = _format_region_clue(nr, "AT_LEAST", k, None, roster_map)
                push("AT_LEAST", al_params, al_text, base_nat - 0.35, False)

            if ku == 0:
                am_params = {"k": k, "region": nr.spec}
                am_text = _format_region_clue(nr, "AT_MOST", k, None, roster_map)
                push("AT_MOST", am_params, am_text, base_nat - 0.15, True)
            elif u <= 4 and ku < u:
                am_params = {"k": k, "region": nr.spec}
                am_text = _format_region_clue(nr, "AT_MOST", k, None, roster_map)
                push("AT_MOST", am_params, am_text, base_nat - 0.35, False)

        # PARITY (enabled with extensions; kept compact for solver speed)
        if (extensions or profile["allow_parity_base"]) and n <= MAX_PARITY_SIZE and u <= MAX_PARITY_UNKNOWN:
            parity = "ODD" if (k & 1) else "EVEN"
            par_params = {"parity": parity, "region": nr.spec}
            par_text = _format_region_clue(nr, "PARITY", None, parity, roster_map)
            push("PARITY", par_params, par_text, base_nat + 0.1, u == 1)

    # Meaningful SAME / DIFFERENT pairs
    sample_pairs = meaningful_pairs
    if len(sample_pairs) > 90:
        sample_pairs = rng.sample(sample_pairs, 90)
    for a, b, bonus in sample_pairs:
        a_in, b_in = a in known, b in known
        if a_in and b_in:
            continue
        same = truth[a] == truth[b]
        ctype = "SAME" if same else "DIFFERENT"
        params = {"target1": a, "target2": b}
        if _canonical_key(ctype, params) in used_clue_keys:
            continue
        text = _format_pair_clue(a, b, same, roster_map)
        cand = _Candidate(ctype, params, text, frozenset((a, b)), "PAIR", ("PAIR", frozenset((a, b))), 2, 2.2 + bonus)
        if a_in != b_in:
            direct_pool.append(cand)
        else:
            partial_pool.append(cand)

    # COMPARE_REGIONS across the whole board when extensions=True
    if extensions and compare_pairs:
        for r1, r2 in compare_pairs:
            diff_unk = (r1.cells ^ r2.cells) - known
            if not (1 <= len(diff_unk) <= 5):
                continue
            c1 = sum(truth[x] == Status.CRIMINAL for x in r1.cells)
            c2 = sum(truth[x] == Status.CRIMINAL for x in r2.cells)
            op = ">" if c1 > c2 else ("<" if c1 < c2 else "==")
            params = {"op": op, "region1": r1.spec, "region2": r2.spec}
            if _canonical_key("COMPARE_REGIONS", params) in used_clue_keys:
                continue
            cost = _cnf_cost("COMPARE_REGIONS", params, num_rows, num_cols)
            if cost > MAX_CLUE_CLAUSES:
                continue

            # Check O(1) direct forcing on symmetric difference
            a_set, b_set = r1.cells - r2.cells, r2.cells - r1.cells
            ca = sum(truth[x] == Status.CRIMINAL for x in a_set if x in known)
            cb = sum(truth[x] == Status.CRIMINAL for x in b_set if x in known)
            ua = [x for x in a_set if x not in known]
            ub = [x for x in b_set if x not in known]
            lo = ca - (cb + len(ub))
            hi = (ca + len(ua)) - cb
            is_direct = (
                (op == ">" and hi == 1)
                or (op == "<" and lo == -1)
                or (op == "==" and (lo == 0 or hi == 0))
            )
            text = _format_compare_clue(r1, r2, op, roster_map)
            nat = 5.8 if (r1.category == "PROFESSION" or r2.category == "PROFESSION") else 5.5
            cand = _Candidate(
                "COMPARE_REGIONS",
                params,
                text,
                r1.cells | r2.cells,
                "COMPARE",
                ("COMPARE", frozenset((r1.cells, r2.cells))),
                cost,
                nat,
            )
            if is_direct:
                direct_pool.append(cand)
            else:
                partial_pool.append(cand)

    return direct_pool, partial_pool


def generate(num_rows, num_cols, seed=None, *, extensions=False, puzzle_id=None,
             title="New Inquiry", difficulty="Normal"):
    rng = random.Random(seed)
    ids = board_ids(num_rows, num_cols)
    profile = DIFFICULTY_PROFILES.get(difficulty, DIFFICULTY_PROFILES["Normal"])

    # Pre-assign roster names & professions so clues can reference them naturally.
    roster_map: dict[str, tuple[str, str]] = {}
    for j, cid in enumerate(ids):
        roster_map[cid] = ROSTER[j] if j < len(ROSTER) else (f"Resident {j + 1}", ROSTER[j % len(ROSTER)][1])

    order = list(ids)
    rng.shuffle(order)

    # Balanced truth assignment (~35%-65% criminals on boards >= 4 cells) for richer puzzles.
    truth = {cid: rng.choice(BINARY) for cid in ids}
    if len(ids) >= 4:
        lo_c = max(1, round(len(ids) * 0.35))
        hi_c = min(len(ids) - 1, round(len(ids) * 0.65))
        crims = [cid for cid in order if truth[cid] == Status.CRIMINAL]
        if len(crims) < lo_c:
            for cid in [x for x in order if truth[x] == Status.INNOCENT][: lo_c - len(crims)]:
                truth[cid] = Status.CRIMINAL
        elif len(crims) > hi_c:
            for cid in crims[: len(crims) - hi_c]:
                truth[cid] = Status.INNOCENT

    catalog = _build_region_catalog(num_rows, num_cols, ids, roster_map, profile["allow_boundary"])
    meaningful_pairs = _build_meaningful_pairs(num_rows, num_cols, ids, roster_map)
    compare_pairs = _build_compare_pairs(catalog, num_rows, num_cols, rng) if extensions else []

    clues: dict[str, Clue] = {}
    compiled_clues: list = []
    used_clue_keys: set[tuple] = set()
    used_region_keys: Counter = Counter()
    used_categories: Counter = Counter()
    used_types: Counter = Counter()
    last_type: str | None = None
    last_cat: str | None = None

    def assign_clue(owner: str, clue_type: str, params: dict, text: str,
                    category: str = "CELLS", region_key=None) -> None:
        nonlocal last_type, last_cat
        clues[owner] = Clue("clue_" + owner, owner, clue_type, params, text)
        compiled_clues.append(_compile_constraint(clue_type, params, num_rows, num_cols))
        used_clue_keys.add(_canonical_key(clue_type, params))
        if region_key is not None:
            used_region_keys[region_key] += 1
        used_categories[category] += 1
        used_types[clue_type] += 1
        last_type = clue_type
        last_cat = category

    def score_candidate(cand: _Candidate, newly_forced: int, chained: bool,
                        free_owner_count: int) -> float:
        s = cand.natural_score
        # Strong diversity penalties against repeating exact regions, categories, or types.
        s -= 4.0 * used_region_keys[cand.region_key]
        s -= 0.75 * used_categories[cand.category]
        s -= 0.85 * used_types[cand.clue_type]
        if cand.clue_type == last_type:
            s -= 1.2
        if cand.category == last_cat:
            s -= 1.0
        # Reward chaining with an already-open dormant clue in the KB.
        if chained:
            s += profile["chain_bonus"]
        # Reward opening 2-3 cells (especially when we only have 1 free owner), avoid opening too many at once.
        if newly_forced == 2:
            s += profile["multi_bonus"] + (1.5 if free_owner_count == 1 else 0.0)
        elif newly_forced == 3:
            s += profile["multi_bonus"] * 0.8 + (1.0 if free_owner_count == 1 else 0.0)
        elif newly_forced >= 4:
            s -= 1.2 * (newly_forced - 3)
        # Prefer compact CNF clauses.
        s -= cand.cnf_cost * 0.012
        # Mild bonus for extensions clues so they show up throughout the case.
        if extensions and cand.clue_type in ("PARITY", "COMPARE_REGIONS"):
            s += 1.1
        # Easy mode favors crisp EXACTLY / SAME / DIFFERENT clues.
        if profile["prefer_simple"] and cand.clue_type in ("EXACTLY", "SAME", "DIFFERENT"):
            s += 1.2
        return s + rng.uniform(0.0, 0.45)

    def try_synergy_pair(
        known: set[str],
        partial_pool: list[_Candidate],
        deductor: _FastDeductor,
        require_strict_zero_solo: bool = True,
    ) -> tuple[_Candidate, _Candidate, set[str]] | None:
        if len(partial_pool) < 2:
            return None

        # Stratify partial candidates by clue_type so PAIR clues never drown out
        # region/compare/parity clues in the shortlist.
        by_type: dict[str, list[_Candidate]] = {}
        for cand in partial_pool:
            by_type.setdefault(cand.clue_type, []).append(cand)
        for bucket in by_type.values():
            rng.shuffle(bucket)
            bucket.sort(
                key=lambda c: (
                    used_region_keys[c.region_key],
                    used_categories[c.category],
                    len(c.scope - known),
                    rng.random(),
                )
            )

        type_caps = {
            "EXACTLY": 10,
            "AT_LEAST": 7,
            "AT_MOST": 7,
            "COMPARE_REGIONS": 10,
            "PARITY": 8,
            "SAME": 4,
            "DIFFERENT": 4,
        }
        ordered_pool: list[_Candidate] = []
        # Round-robin across types up to each cap so every type is represented.
        max_cap = max(type_caps.values())
        type_order = ["EXACTLY", "COMPARE_REGIONS", "PARITY", "AT_LEAST", "AT_MOST", "SAME", "DIFFERENT"]
        for slot in range(max_cap):
            for ctype in type_order:
                bucket = by_type.get(ctype)
                if bucket and slot < min(len(bucket), type_caps[ctype]):
                    ordered_pool.append(bucket[slot])

        shortlist: list[tuple[_Candidate, frozenset[str], set[str]]] = []
        for cand in ordered_pool:
            comp = _compile_constraint(cand.clue_type, cand.params, num_rows, num_cols)
            solo = deductor.forced_cells(known, compiled_clues + [comp])
            if require_strict_zero_solo and solo:
                continue
            if len(solo) >= 2:
                continue
            shortlist.append((cand, cand.scope - known, solo))
            if len(shortlist) >= 34:
                break

        if len(shortlist) < 2:
            return None

        # Index by unknown cell to quickly enumerate overlapping pairs.
        unk_index: dict[str, list[int]] = {}
        for idx, (_, u_cells, _) in enumerate(shortlist):
            for cid in u_cells:
                unk_index.setdefault(cid, []).append(idx)

        seen_pairs: set[tuple[int, int]] = set()
        candidate_pairs: list[tuple[float, _Candidate, _Candidate, set[str], set[str]]] = []
        for indices in unk_index.values():
            for a_pos in range(len(indices)):
                i = indices[a_pos]
                for b_pos in range(a_pos + 1, len(indices)):
                    j = indices[b_pos]
                    pair_id = (i, j) if i < j else (j, i)
                    if pair_id in seen_pairs:
                        continue
                    seen_pairs.add(pair_id)
                    c1, u1, solo1 = shortlist[pair_id[0]]
                    c2, u2, solo2 = shortlist[pair_id[1]]
                    # Two unknown-only SAME/DIFFERENT clues cannot force a variable alone.
                    if c1.category == "PAIR" and c2.category == "PAIR":
                        continue
                    if c1.region_key == c2.region_key:
                        # Only allow same region when pairing PARITY with a cardinality bound.
                        if not (
                            "PARITY" in (c1.clue_type, c2.clue_type)
                            and c1.clue_type != c2.clue_type
                        ):
                            continue
                    overlap = len(u1 & u2)
                    pre = (
                        c1.natural_score + c2.natural_score
                        + 0.7 * overlap
                        + (2.0 if c1.region_key != c2.region_key else -1.5)
                        + (1.8 if c1.clue_type != c2.clue_type else 0.0)
                        + (1.6 if c1.category != c2.category else 0.0)
                        + (1.8 if extensions and "COMPARE_REGIONS" in (c1.clue_type, c2.clue_type) else 0.0)
                        + (1.2 if extensions and "PARITY" in (c1.clue_type, c2.clue_type) else 0.0)
                        - 0.01 * (c1.cnf_cost + c2.cnf_cost)
                        + rng.uniform(0.0, 0.5)
                    )
                    candidate_pairs.append((pre, c1, c2, solo1, solo2))

        candidate_pairs.sort(key=lambda item: -item[0])

        best: tuple[float, _Candidate, _Candidate, set[str]] | None = None
        found = 0
        for _, c1, c2, solo1, solo2 in candidate_pairs[:70]:
            comp1 = _compile_constraint(c1.clue_type, c1.params, num_rows, num_cols)
            comp2 = _compile_constraint(c2.clue_type, c2.params, num_rows, num_cols)
            joint = deductor.forced_cells(known, compiled_clues + [comp1, comp2])
            extra = joint - solo1 - solo2
            if not extra:
                continue
            pair_score = (
                score_candidate(c1, len(joint), True, 2)
                + score_candidate(c2, len(joint), True, 2)
                + (2.5 if not solo1 and not solo2 else 0.0)
                + (2.0 if c1.region_key != c2.region_key else -2.0)
                + (2.0 if c1.clue_type != c2.clue_type else 0.0)
                + (1.5 if c1.category != c2.category else 0.0)
            )
            if best is None or pair_score > best[0]:
                best = (pair_score, c1, c2, joint)
            found += 1
            if found >= 8:
                break
        if best is None:
            return None
        return best[1], best[2], best[3]

    # ── Opening phase ────────────────────────────────────────────────────────
    deductor = _FastDeductor(num_rows, num_cols, truth)
    paired = extensions and len(ids) >= 4
    starters: list[str]
    known: set[str]
    free_owners: deque[str]

    if paired:
        # Try to find a natural 2-clue synergy opening with 2 starter witnesses.
        opening_found = False
        for attempt in range(4):
            s1 = order[(2 * attempt) % len(order)]
            s2 = order[(2 * attempt + 1) % len(order)]
            if s1 == s2:
                continue
            init_known = {s1, s2}
            _, partial_pool = _generate_candidates(
                init_known, catalog, meaningful_pairs, compare_pairs, truth, roster_map,
                num_rows, num_cols, extensions, used_clue_keys, profile, rng,
            )
            syn = try_synergy_pair(init_known, partial_pool, deductor, require_strict_zero_solo=True)
            if syn is not None:
                c1, c2, newly = syn
                starters = [s1, s2]
                assign_clue(s1, c1.clue_type, c1.params, c1.text, c1.category, c1.region_key)
                assign_clue(s2, c2.clue_type, c2.params, c2.text, c2.category, c2.region_key)
                known = init_known | newly
                free_owners = deque(sorted(newly, key=lambda x: order.index(x)))
                opening_found = True
                break

        if not opening_found:
            # Guaranteed fallback for tiny extension boards (e.g. 2x3 with unfavorable random truth).
            a, b, x, y = order[:4]
            truth[a], truth[x], truth[y] = Status.INNOCENT, Status.CRIMINAL, Status.CRIMINAL
            deductor = _FastDeductor(num_rows, num_cols, truth)
            pair_spec, anchor_spec = region("CELLS", [x, y]), region("CELLS", [a])
            assign_clue(
                a, "PARITY", {"parity": "EVEN", "region": pair_spec},
                f"An even number of {x} and {y} are criminals.", "CELLS", ("CELLS", frozenset((x, y))),
            )
            assign_clue(
                b, "COMPARE_REGIONS", {"op": ">", "region1": pair_spec, "region2": anchor_spec},
                f"More criminals in {{{x}, {y}}} than in {a}.", "COMPARE", ("COMPARE", frozenset((x, y, a))),
            )
            starters = [a, b]
            known = {a, b, x, y}
            free_owners = deque([x, y])
    else:
        starters = [order[0]]
        known = {order[0]}
        free_owners = deque([order[0]])

    # ── Main deduction-guided loop ───────────────────────────────────────────
    rank = {cid: idx for idx, cid in enumerate(order)}
    while len(known) < len(ids):
        direct_pool, partial_pool = _generate_candidates(
            known, catalog, meaningful_pairs, compare_pairs, truth, roster_map,
            num_rows, num_cols, extensions, used_clue_keys, profile, rng,
        )

        # 1. Attempt a genuine 2-clue synergy step when >= 2 free owners are ready.
        did_synergy = False
        if len(free_owners) >= 2 and rng.random() < profile["synergy_rate"]:
            syn = try_synergy_pair(known, partial_pool, deductor, require_strict_zero_solo=True)
            if syn is not None:
                c1, c2, newly = syn
                o1 = free_owners.popleft()
                o2 = free_owners.popleft()
                assign_clue(o1, c1.clue_type, c1.params, c1.text, c1.category, c1.region_key)
                assign_clue(o2, c2.clue_type, c2.params, c2.text, c2.category, c2.region_key)
                known.update(newly)
                for cid in sorted(newly, key=rank.get):
                    free_owners.append(cid)
                did_synergy = True

        if did_synergy:
            continue

        # 2. Single-owner step: prefer KB-chaining clues, then rich multi/1-cell natural clues.
        owner = free_owners.popleft()
        best_single: tuple[float, _Candidate, set[str]] | None = None

        # First check partial clues that overlap active open clues in the KB!
        if compiled_clues and partial_pool:
            active_unknowns = {
                cid
                for comp in compiled_clues
                for cid in _constraint_scope(comp)
                if cid not in known
            }
            if active_unknowns:
                chain_sample = [c for c in partial_pool if (c.scope - known) & active_unknowns]
                rng.shuffle(chain_sample)
                chain_sample.sort(
                    key=lambda c: (
                        used_region_keys[c.region_key],
                        used_categories[c.category],
                        c.category == "PAIR",
                        rng.random(),
                    )
                )
                for cand in chain_sample[:28]:
                    comp = _compile_constraint(cand.clue_type, cand.params, num_rows, num_cols)
                    newly = deductor.forced_cells(known, compiled_clues + [comp])
                    if not newly:
                        continue
                    sc = score_candidate(cand, len(newly), chained=True, free_owner_count=len(free_owners) + 1)
                    if best_single is None or sc > best_single[0]:
                        best_single = (sc, cand, newly)

        # Next evaluate direct natural clues.
        if direct_pool:
            direct_sample = list(direct_pool)
            rng.shuffle(direct_sample)
            direct_sample.sort(
                key=lambda c: (
                    used_region_keys[c.region_key],
                    used_categories[c.category],
                    -c.natural_score,
                    rng.random(),
                )
            )
            for cand in direct_sample[:32]:
                comp = _compile_constraint(cand.clue_type, cand.params, num_rows, num_cols)
                solo = deductor.forced_cells(known, [comp])
                newly = deductor.forced_cells(known, compiled_clues + [comp]) if compiled_clues else solo
                if not newly:
                    continue
                chained = len(newly) > len(solo)
                sc = score_candidate(cand, len(newly), chained=chained, free_owner_count=len(free_owners) + 1)
                if best_single is None or sc > best_single[0]:
                    best_single = (sc, cand, newly)

        if best_single is not None:
            _, cand, newly = best_single
            assign_clue(owner, cand.clue_type, cand.params, cand.text, cand.category, cand.region_key)
            known.update(newly)
            for cid in sorted(newly, key=rank.get):
                free_owners.append(cid)
            continue

        # 3. Guaranteed fallback (only hit if no natural region/pair advanced the board).
        target = min(set(ids) - known, key=rank.get)
        peer = min(known, key=lambda c: (c == owner, rank[c]))
        same = truth[target] == truth[peer]
        ctype = "SAME" if same else "DIFFERENT"
        params = {"target1": peer, "target2": target}
        if _canonical_key(ctype, params) not in used_clue_keys:
            text = _format_pair_clue(peer, target, same, roster_map)
            assign_clue(owner, ctype, params, text, "PAIR", ("PAIR", frozenset((peer, target))))
        else:
            text = _format_fact_clue(target, truth[target], roster_map)
            assign_clue(owner, "FACT", {"target": target, "status": truth[target].value}, text, "FACT", ("FACT", target))
        known.add(target)
        free_owners.append(target)

    # ── Final remaining owners: enforce global uniqueness with natural clues ──
    def pick_closing_clue(alt_model: dict[str, Status] | None) -> tuple[str, dict, str, str, object]:
        # Prefer an unused natural region clue (and if alt_model exists, one that refutes alt_model).
        candidates: list[tuple[float, str, dict, str, str, object]] = []
        for nr in catalog:
            n = len(nr.cells)
            if nr.category == "BOUNDARY" and n > 10:
                continue
            k_true = sum(truth[c] == Status.CRIMINAL for c in nr.cells)
            k_alt = sum(alt_model[c] == Status.CRIMINAL for c in nr.cells) if alt_model else None

            # EXACTLY
            if alt_model is None or k_true != k_alt:
                params = {"k": k_true, "region": nr.spec}
                if _canonical_key("EXACTLY", params) not in used_clue_keys:
                    cost = _cnf_cost("EXACTLY", params, num_rows, num_cols)
                    if cost <= MAX_CLUE_CLAUSES:
                        text = _format_region_clue(nr, "EXACTLY", k_true, None, roster_map)
                        sc = (
                            6.0
                            - 3.0 * used_region_keys[(nr.category, nr.cells)]
                            - 0.7 * used_categories[nr.category]
                            - 0.01 * cost
                            + rng.uniform(0.0, 0.4)
                        )
                        candidates.append((sc, "EXACTLY", params, text, nr.category, (nr.category, nr.cells)))

            # PARITY (for extensions)
            if extensions and n <= MAX_PARITY_SIZE and (alt_model is None or (k_true & 1) != (k_alt & 1)):
                parity = "ODD" if (k_true & 1) else "EVEN"
                params = {"parity": parity, "region": nr.spec}
                if _canonical_key("PARITY", params) not in used_clue_keys:
                    cost = _cnf_cost("PARITY", params, num_rows, num_cols)
                    if cost <= MAX_CLUE_CLAUSES:
                        text = _format_region_clue(nr, "PARITY", None, parity, roster_map)
                        sc = (
                            5.5
                            - 3.0 * used_region_keys[(nr.category, nr.cells)]
                            - 0.7 * used_categories[nr.category]
                            + rng.uniform(0.0, 0.4)
                        )
                        candidates.append((sc, "PARITY", params, text, nr.category, (nr.category, nr.cells)))

        if candidates:
            candidates.sort(key=lambda item: -item[0])
            _, ctype, params, text, cat, rkey = candidates[0]
            return ctype, params, text, cat, rkey

        # Fallback: clean FACT on a cell that disagrees with alt_model (or a non-starter if already unique).
        if alt_model is not None:
            diff_cells = [cid for cid in ids if alt_model[cid] != truth[cid]]
            target = next((cid for cid in diff_cells if cid not in starters), diff_cells[0])
        else:
            target = next((cid for cid in order if cid not in starters), starters[0])
        params = {"target": target, "status": truth[target].value}
        return "FACT", params, _format_fact_clue(target, truth[target], roster_map), "FACT", ("FACT", target)

    closing_owners = list(free_owners)
    for idx, owner in enumerate(closing_owners):
        alt = deductor.find_alt_model(compiled_clues, priority_ids=starters)
        remaining_slots = len(closing_owners) - idx
        if alt is not None and remaining_slots == 1:
            # Test natural region candidates to see if one eliminates ALL alternative models at once.
            solved_unique = False
            natural_tries = []
            for nr in catalog:
                n = len(nr.cells)
                if nr.category == "BOUNDARY" and n > 10:
                    continue
                k_true = sum(truth[c] == Status.CRIMINAL for c in nr.cells)
                k_alt = sum(alt[c] == Status.CRIMINAL for c in nr.cells)
                if k_true == k_alt:
                    continue
                params = {"k": k_true, "region": nr.spec}
                if _canonical_key("EXACTLY", params) in used_clue_keys:
                    continue
                cost = _cnf_cost("EXACTLY", params, num_rows, num_cols)
                if cost > MAX_CLUE_CLAUSES:
                    continue
                sc = (
                    6.0
                    - 3.0 * used_region_keys[(nr.category, nr.cells)]
                    - 0.7 * used_categories[nr.category]
                    - 0.01 * cost
                    + rng.uniform(0.0, 0.3)
                )
                natural_tries.append((sc, nr, k_true, params))
            natural_tries.sort(key=lambda item: -item[0])
            for _, nr, k_true, params in natural_tries[:12]:
                comp = _compile_constraint("EXACTLY", params, num_rows, num_cols)
                if deductor.find_alt_model(compiled_clues + [comp], priority_ids=starters) is None:
                    text = _format_region_clue(nr, "EXACTLY", k_true, None, roster_map)
                    assign_clue(owner, "EXACTLY", params, text, nr.category, (nr.category, nr.cells))
                    solved_unique = True
                    break
            if not solved_unique:
                # Guaranteed uniqueness pin on a starter cell that disagrees with alt.
                pin = next((s for s in starters if alt[s] != truth[s]), starters[0])
                assign_clue(
                    owner, "FACT", {"target": pin, "status": truth[pin].value},
                    _format_fact_clue(pin, truth[pin], roster_map), "FACT", ("FACT", pin),
                )
        else:
            ctype, params, text, cat, rkey = pick_closing_clue(alt)
            assign_clue(owner, ctype, params, text, cat, rkey)

    cells = []
    for j, cid in enumerate(ids):
        r, c = divmod(j, num_cols)
        name, job = roster_map[cid]
        cells.append(Cell(cid, r + 1, c + 1, name, job, truth[cid], cid in starters, clues[cid]))

    witness_word = "card" if len(starters) == 1 else "cards"
    puzzle = Puzzle(
        puzzle_id or f"case_{num_rows}x{num_cols}_{rng.getrandbits(32):08x}",
        title,
        difficulty,
        num_rows,
        num_cols,
        f"{num_rows} × {num_cols} deduction case with {len(starters)} initial witness {witness_word}.",
        tuple(cells),
    )
    verify(puzzle)
    return puzzle


def verify(puzzle):
    """Replay publicly visible inference independently of construction order."""
    validate_puzzle(puzzle)
    agent = DeductiveAgent(GameEngine(puzzle))
    if not agent.auto_solve():
        raise ValueError(f"Puzzle stalls: {puzzle.puzzle_id}")
    return agent


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and verify one no-guess puzzle.")
    parser.add_argument("--rows", type=int, default=5)
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--extensions", action="store_true")
    parser.add_argument("--difficulty", default="Normal")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.rows, args.cols, args.seed, extensions=args.extensions, difficulty=args.difficulty)
    save_puzzle(result, args.output)
    print(f"{result.puzzle_id} | verified | {args.output}")
