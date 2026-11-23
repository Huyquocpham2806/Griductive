"""Dữ liệu của ván chơi. PublicState chỉ chứa thông tin người chơi đã thấy."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

USE_FALLBACK_WHEN_TODO_NOT_IMPLEMENTED = True


class Status(str, Enum):
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"
    UNKNOWN = "UNKNOWN"
    INCONSISTENT = "INCONSISTENT"


class Verdict(str, Enum):
    ACCEPTED = "ACCEPTED"
    NOT_PROVABLE = "NOT_PROVABLE"
    CONTRADICTED = "CONTRADICTED"
    INCONSISTENT = "INCONSISTENT"
    ALREADY_REVEALED = "ALREADY_REVEALED"


BINARY = (Status.INNOCENT, Status.CRIMINAL)
ROSTER = list(zip(
    "Abel Bea Clara Derek Eliza Franz Grant Hannah Ivy Jonas Karl Leo Mara Noah Owen Priya Quilla Roy Sophia Tom Uma Victor Wendy Xavier Yara".split(),
    "Astronaut Cook Guard Cook Detective Detective Clerk Guard Clerk Farmer Painter Farmer Astronaut Clerk Clerk Farmer Detective Guard Painter Pilot Doctor Guard Cook Pilot Detective".split(),
))


def column_label(col: int) -> str:
    if type(col) is not int or col < 1:
        raise ValueError("Column must be a positive integer")
    label = ""
    while col:
        col, rem = divmod(col - 1, 26)
        label = chr(65 + rem) + label
    return label


def board_ids(rows: int, cols: int) -> tuple[str, ...]:
    if any(type(n) is not int or n < 1 for n in (rows, cols)):
        raise ValueError("Board dimensions must be positive integers")
    return tuple(f"{column_label(c)}{r}" for r in range(1, rows + 1) for c in range(1, cols + 1))


@dataclass(frozen=True)
class RegionSpec:
    region_type: str
    target: Any


@dataclass(frozen=True)
class Clue:
    clue_id: str
    owner_cell: str
    clue_type: str
    params: dict
    text: str


@dataclass(frozen=True)
class Person:
    cell_id: str
    row: int
    col: int
    name: str
    profession: str


@dataclass(frozen=True)
class Cell(Person):
    true_status: Status
    initially_revealed: bool
    clue: Clue


@dataclass(frozen=True)
class Puzzle:
    puzzle_id: str
    title: str
    difficulty: str
    num_rows: int
    num_cols: int
    description: str
    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class PublicState:
    num_rows: int
    num_cols: int
    people: tuple[Person, ...]
    known: dict[str, Status]
    clues: tuple[Clue, ...]


@dataclass
class SolverStats:
    mode: str = "DPLL"
    primary_vars: int = 0
    aux_vars: int = 0
    cnf_clauses: int = 0
    sat_calls: int = 0
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime_sec: float = 0.0

    def add(self, other: SolverStats) -> None:
        """Geometry describes the latest KB. Work counters accumulate across calls."""
        self.mode = other.mode
        self.primary_vars = other.primary_vars
        self.aux_vars = other.aux_vars
        self.cnf_clauses = other.cnf_clauses
        for key in ("sat_calls", "decisions", "propagations", "backtracks", "runtime_sec"):
            setattr(self, key, getattr(self, key) + getattr(other, key))


@dataclass(frozen=True)
class Hint:
    cell_id: str
    status: Status
    related: tuple[str, ...]


@dataclass
class DeductionTrace:
    entries: list[str] = field(default_factory=list)

    def record(self, hint: Hint) -> None:
        opposite = Status.INNOCENT if hint.status == Status.CRIMINAL else Status.CRIMINAL
        message = f"{hint.cell_id} → {hint.status.value}. Giả sử {opposite.value} dẫn đến mâu thuẫn."
        if hint.related:
            message += " Thẻ nhắc đến ô này: " + ", ".join(hint.related) + "."
        self.entries.append(message)
