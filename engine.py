"""Hình học, ngữ nghĩa manh mối và cổng lật thẻ."""
from __future__ import annotations

import json
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from models import BINARY, Cell, Clue, Person, PublicState, Puzzle, RegionSpec, Status, Verdict, board_ids, column_label


@lru_cache(maxsize=32)
def geometry(rows, cols):
    return {key: divmod(i, cols) for i, key in enumerate(board_ids(rows, cols))}


def resolve_region(region, rows, cols):
    """Trả về các ô phân biệt theo thứ tự hàng, kể cả ở lưới một chiều."""
    if isinstance(region, dict):
        region = RegionSpec(**region)
    coords = geometry(rows, cols)
    kind, t = region.region_type, region.target

    def neighbors(key):
        if not isinstance(key, str) or key not in coords:
            raise ValueError(f"Unknown neighbor origin: {key}")
        r, c = coords[key]
        return {i for i, (a, b) in coords.items() if max(abs(r-a), abs(c-b)) == 1}

    if kind == "ROW" and type(t) is int and 1 <= t <= rows:
        result = {i for i, (r, _) in coords.items() if r == t-1}
    elif kind == "COL" and t in [column_label(c+1) for c in range(cols)]:
        result = {i for i, (_, c) in coords.items() if column_label(c+1) == t}
    elif kind == "NEIGHBORS":
        result = neighbors(t)
    elif kind == "CELLS" and isinstance(t, list) and all(isinstance(i, str) and i in coords for i in t):
        result = set(t)
    elif kind == "COMMON_NEIGHBORS" and isinstance(t, list) and len(t) == 2:
        result = neighbors(t[0]) & neighbors(t[1])
    elif kind in ("BOUNDARY", "CORNERS") and t is None:
        result = set()
        for i, (r, c) in coords.items():
            edges = (r in (0, rows-1), c in (0, cols-1))
            if (all(edges) if kind == "CORNERS" else any(edges)):
                result.add(i)
    else:
        raise ValueError(f"Invalid region: {region}")
    return tuple(i for i in coords if i in result)


def clue_groups(clue, rows, cols):
    """Validate parameters and return ordered operands (two groups for comparison)."""
    kind, p = clue.clue_type, clue.params
    if kind in ("FACT", "SAME", "DIFFERENT"):
        if kind == "FACT":
            if Status(p["status"]) not in BINARY:
                raise ValueError("FACT requires a binary status")
            ids = [p["target"]]
        else:
            ids = [p["target1"], p["target2"]]
        if any(i not in geometry(rows, cols) for i in ids):
            raise ValueError(f"Invalid reference in {clue.clue_id}")
        return (tuple(ids),)
    if kind == "COMPARE_REGIONS":
        if p["op"] not in ("==", "<", ">"):
            raise ValueError("Invalid comparison")
        return tuple(resolve_region(p[k], rows, cols) for k in ("region1", "region2"))
    ids = resolve_region(p["region"], rows, cols)
    if kind == "PARITY" and p["parity"] in ("EVEN", "ODD"):
        return (ids,)
    if kind in ("EXACTLY", "AT_LEAST", "AT_MOST") and type(p["k"]) is int and 0 <= p["k"] <= len(ids):
        return (ids,)
    raise ValueError(f"Invalid clue parameters for {kind}")


def evaluate_clue_directly(clue, assignment, rows, cols, *, groups=None):
    """Evaluate a complete assignment on the clue scope. Values are binary Status."""
    groups = clue_groups(clue, rows, cols) if groups is None else groups
    kind, p = clue.clue_type, clue.params
    values = []
    for ids in groups:
        states = [Status(assignment[i]) for i in ids]
        if any(s not in BINARY for s in states):
            raise ValueError("Direct evaluation needs binary statuses")
        values.append([s == Status.CRIMINAL for s in states])
    bits = values[0]
    if kind == "FACT":
        return bits[0] == (p["status"] == Status.CRIMINAL)
    if kind == "SAME":
        return bits[0] == bits[1]
    if kind == "DIFFERENT":
        return bits[0] != bits[1]
    n = sum(bits)
    if kind == "PARITY":
        return n % 2 == int(p["parity"] == "ODD")
    if kind == "COMPARE_REGIONS":
        other = sum(values[1])
        return {"==": n == other, ">": n > other, "<": n < other}[p["op"]]
    k = p["k"]
    return {"EXACTLY": n == k, "AT_LEAST": n >= k, "AT_MOST": n <= k}[kind]


def validate_puzzle(puzzle):
    ids = board_ids(puzzle.num_rows, puzzle.num_cols)
    cells = puzzle.cells
    if tuple(c.cell_id for c in cells) != ids:
        raise ValueError("Expected one cell per coordinate in row-major order")
    if not 1 <= sum(c.initially_revealed for c in cells) <= 3:
        raise ValueError("Expected 1 to 3 initial cards")
    truth = {c.cell_id: c.true_status for c in cells}
    if len({c.clue.clue_id for c in cells}) != len(cells):
        raise ValueError("Duplicate clue IDs")
    for c in cells:
        r, col = geometry(puzzle.num_rows, puzzle.num_cols)[c.cell_id]
        if ((c.row, c.col) != (r+1, col+1) or c.clue.owner_cell != c.cell_id
                or type(c.initially_revealed) is not bool or c.true_status not in BINARY):
            raise ValueError(f"Invalid card {c.cell_id}")
        if not evaluate_clue_directly(c.clue, truth, puzzle.num_rows, puzzle.num_cols):
            raise ValueError(f"False clue: {c.clue.clue_id}")


def load_puzzle(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cells = []
    for raw in data.pop("cells"):
        raw["true_status"] = Status(raw["true_status"])
        raw["clue"] = Clue(**raw["clue"])
        cells.append(Cell(**raw))
    puzzle = Puzzle(**data, cells=tuple(cells))
    validate_puzzle(puzzle)
    return puzzle


def save_puzzle(puzzle, path):
    validate_puzzle(puzzle)
    Path(path).write_text(json.dumps(asdict(puzzle), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class GameEngine:
    def __init__(self, puzzle):
        validate_puzzle(puzzle)
        self._puzzle = puzzle
        self._cards = {c.cell_id: c for c in puzzle.cells}
        self._people = tuple(Person(c.cell_id, c.row, c.col, c.name, c.profession) for c in puzzle.cells)
        self.restart()

    def restart(self):
        self._opened = dict.fromkeys(c.cell_id for c in self._cards.values() if c.initially_revealed)

    def public_state(self):
        return PublicState(self._puzzle.num_rows, self._puzzle.num_cols, self._people,
                           {i: self._cards[i].true_status for i in self._opened},
                           tuple(self._cards[i].clue for i in self._opened))

    def submit(self, cell_id, status, classify):
        """Use a public-state classifier. Hidden data becomes accessible only after acceptance."""
        if cell_id not in self._cards or status not in BINARY:
            raise ValueError("Invalid move")
        if cell_id in self._opened:
            return Verdict.ALREADY_REVEALED
        forced = classify(self.public_state(), cell_id)
        if forced == Status.INCONSISTENT:
            return Verdict.INCONSISTENT
        if forced == Status.UNKNOWN:
            return Verdict.NOT_PROVABLE
        if forced != status:
            return Verdict.CONTRADICTED
        if self._cards[cell_id].true_status != forced:
            raise RuntimeError("Classifier disagrees with the validated puzzle")
        self._opened[cell_id] = None
        return Verdict.ACCEPTED
