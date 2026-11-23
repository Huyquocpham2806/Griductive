"""Sinh màn bằng quy nạp: mỗi thẻ mới có một chứng minh từ dữ kiện công khai."""
from __future__ import annotations

import argparse
import random
from collections import deque
from pathlib import Path

from engine import GameEngine, resolve_region, save_puzzle, validate_puzzle
from logic_agent import DeductiveAgent
from models import ROSTER, Cell, Clue, Puzzle, Status, board_ids, column_label

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


def generate(num_rows, num_cols, seed=None, *, extensions=False, puzzle_id=None,
             title="New Inquiry", difficulty="Normal"):
    rng = random.Random(seed)
    ids = board_ids(num_rows, num_cols)
    order = list(ids)
    rng.shuffle(order)
    truth = {i: rng.choice((Status.CRIMINAL, Status.INNOCENT)) for i in ids}
    clues = {}

    def count(group):
        return sum(truth[i] == Status.CRIMINAL for i in group)

    def write(owner, kind, text, **params):
        clues[owner] = Clue("clue_" + owner, owner, kind, params, text)

    def fact(owner, i):
        write(owner, "FACT", f"{i} is {truth[i].value.lower()}.", target=i, status=truth[i].value)

    # Hard opening: x XOR y = 0 and x+y > 0 jointly force both x and y.
    paired = extensions and len(ids) >= 4
    if paired:
        a, b, x, y = order[:4]
        truth[a], truth[x], truth[y] = Status.INNOCENT, Status.CRIMINAL, Status.CRIMINAL
        pair, anchor = region("CELLS", [x, y]), region("CELLS", [a])
        write(a, "PARITY", f"An even number in {region_name(pair)} are criminals.",
              parity="EVEN", region=pair)
        write(b, "COMPARE_REGIONS", f"More criminals in {region_name(pair)} than in {{{a}}}.",
              op=">", region1=pair, region2=anchor)
        starters, known, owners = [a, b], set(order[:4]), deque([x, y])
    else:
        starters, known, owners = [order[0]], {order[0]}, deque(order[:1])

    regions = ([region("ROW", r+1) for r in range(num_rows)]
               + [region("COL", column_label(c+1)) for c in range(num_cols)]
               + [region("CORNERS"), region("BOUNDARY")]
               + [region("NEIGHBORS", i) for i in ids])
    for a, b in zip(order[::2], order[1::2]):
        regions.append(region("COMMON_NEIGHBORS", [a, b]))
    pool = [(r, set(resolve_region(r, num_rows, num_cols))) for r in regions]
    used_regions = set()
    rank = {i: n for n, i in enumerate(order)}
    while len(known) < len(ids):
        owner = owners.popleft()
        # Prefer a named region with one unresolved member. Change the geometry
        # over the course of the case instead of repeating a single region.
        choices = [(r, group) for r, group in pool if len(group-known) == 1 and len(group) >= 2]
        if choices and rng.random() < .88:
            rng.shuffle(choices)
            r, group = min(choices, key=lambda item: (item[0]["region_type"] in used_regions,
                                                      -len(item[1])))
            used_regions.add(r["region_type"])
            target, = group-known
        else:
            target = min(set(ids)-known, key=rank.get)
            peers = rng.sample(sorted(known), min(len(known), rng.randint(1, 3)))
            group = {target, *peers}
            r = region("CELLS", sorted(group))
        n = count(group)
        kind = ["EXACTLY", "BOUND", "PAIR", "PARITY" if extensions else "EXACTLY"][len(clues) % 4]
        if difficulty == "Easy" and len(clues) == 0:
            fact(owner, target)
        elif kind == "PAIR":
            peer = rng.choice(sorted(group-{target}))
            same = truth[target] == truth[peer]
            write(owner, "SAME" if same else "DIFFERENT",
                  f"{peer} and {target} have {'the same' if same else 'different'} status.",
                  target1=peer, target2=target)
        elif kind == "PARITY":
            parity = "ODD" if n % 2 else "EVEN"
            write(owner, kind, f"Criminal count in {region_name(r)} is {parity.lower()}.",
                  parity=parity, region=r)
        else:
            label = "Exactly"
            if kind == "BOUND":
                kind, label = (("AT_LEAST", "At least") if truth[target] == Status.CRIMINAL
                               else ("AT_MOST", "At most"))
            write(owner, "EXACTLY" if kind == "EXACTLY" else kind,
                  f"{label} {n} criminals in {region_name(r)}.", k=n, region=r)
        known.add(target)
        owners.append(target)
    for owner, initial in zip(owners, starters):
        fact(owner, initial)
    cells = []
    for j, i in enumerate(ids):
        r, c = divmod(j, num_cols)
        name, job = ROSTER[j] if j < len(ROSTER) else (f"Resident {j+1}", ROSTER[j % len(ROSTER)][1])
        cells.append(Cell(i, r+1, c+1, name, job, truth[i], i in starters, clues[i]))
    puzzle = Puzzle(puzzle_id or f"case_{num_rows}x{num_cols}_{rng.getrandbits(32):08x}",
                    title, difficulty, num_rows, num_cols,
                    f"{num_rows} × {num_cols} deduction case with {len(starters)} initial witness cards.",
                    tuple(cells))
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.rows, args.cols, args.seed, extensions=args.extensions)
    save_puzzle(result, args.output)
    print(f"{result.puzzle_id} | verified | {args.output}")
