"""Suy diễn logic chỉ đọc PublicState, sử dụng CNFEncoder và DPLLSolver."""
from typing import List, Tuple

from cnf_encoder import CNFEncoder
from dpll_solver import DPLLSolver
from engine import clue_groups
from models import BINARY, Clue, DeductionTrace, Hint, PublicState, SolverStats, Status, Verdict


def classify_cell(public_state: PublicState, cell_id: str) -> Tuple[Status, SolverStats]:
    """Tạo CNFEncoder cùng kích thước, gọi build_kb, lấy v = cell_to_var[cell_id].
    Gọi DPLLSolver.solve trên KB với assumptions=[v] và [-v]. Với kết quả
    (SAT+,SAT−): 10→CRIMINAL, 01→INNOCENT, 11→UNKNOWN, 00→INCONSISTENT.
    Cộng các bộ đếm và runtime của hai truy vấn, đặt primary_vars, aux_vars,
    cnf_clauses từ encoder rồi trả (status, stats). Không truy cập đáp án.
    """
    encoder = CNFEncoder(public_state.num_rows, public_state.num_cols)
    if cell_id not in encoder.cell_to_var:
        raise ValueError(f"Unknown cell: {cell_id}")

    kb = encoder.build_kb(public_state)
    var = encoder.cell_to_var[cell_id]

    solver = DPLLSolver()
    sat_pos, _, stats_pos = solver.solve(kb, encoder.num_vars, assumptions=[var])
    sat_neg, _, stats_neg = solver.solve(kb, encoder.num_vars, assumptions=[-var])

    if sat_pos and not sat_neg:
        status = Status.CRIMINAL
    elif not sat_pos and sat_neg:
        status = Status.INNOCENT
    elif sat_pos and sat_neg:
        status = Status.UNKNOWN
    else:
        status = Status.INCONSISTENT

    stats = SolverStats(
        mode="DPLL",
        primary_vars=encoder.primary_vars,
        aux_vars=encoder.aux_vars,
        cnf_clauses=encoder.num_clauses,
        sat_calls=stats_pos.sat_calls + stats_neg.sat_calls,
        decisions=stats_pos.decisions + stats_neg.decisions,
        propagations=stats_pos.propagations + stats_neg.propagations,
        backtracks=stats_pos.backtracks + stats_neg.backtracks,
        runtime_sec=stats_pos.runtime_sec + stats_neg.runtime_sec,
    )

    return status, stats


def check_uniqueness(all_clues: List[Clue], num_rows: int, num_cols: int) -> bool:
    """Mã hóa tất cả clue trên KB không có givens ngầm. Tìm model M; UNSAT→False.
    Thêm đúng một blocking clause ∨_i (¬v_i nếu M_i=True, ngược lại v_i)
    cho các biến Ô (bỏ qua biến phụ). Trả True iff lần solve thứ hai UNSAT.
    Muốn tính cả trạng thái mở đầu, truyền thêm FACT tương ứng.
    """
    encoder = CNFEncoder(num_rows, num_cols)
    clauses: List[List[int]] = []

    for clue in all_clues:
        clauses.extend(encoder.encode_clue(clue))

    solver = DPLLSolver()
    sat_first, model, _ = solver.solve(clauses, encoder.num_vars)

    if not sat_first or model is None:
        return False

    blocking_clause = [
        -var if model[var] else var
        for var in range(1, encoder.primary_vars + 1)
    ]

    sat_second, _, _ = solver.solve(clauses + [blocking_clause], encoder.num_vars)
    return not sat_second


def uniqueness(all_clues, num_rows, num_cols):
    """Public wrapper. Returns uniqueness over cell statuses across all supplied clues."""
    return check_uniqueness(all_clues, num_rows, num_cols)


class DeductiveAgent:
    def __init__(self, engine):
        self.engine = engine
        self.trace = DeductionTrace()
        self.stats = SolverStats(mode="DPLL")
        self._revision = None
        self._cache = {}

    def classify(self, state, cell_id):
        if cell_id not in {p.cell_id for p in state.people}:
            raise ValueError("Unknown cell")
        revision = (state.known, state.clues)
        if revision != self._revision:
            self._revision = (state.known.copy(), state.clues)
            self._cache.clear()
        if cell_id in self._cache:
            return self._cache[cell_id]
        status, stats = classify_cell(state, cell_id)
        self.stats.add(stats)
        self._cache[cell_id] = status
        return status

    def related(self, state, cell_id):
        return tuple(c.owner_cell for c in state.clues
                     if any(cell_id in group for group in clue_groups(c, state.num_rows, state.num_cols)))

    def get_hint(self):
        state = self.engine.public_state()
        for person in state.people:
            i = person.cell_id
            if i not in state.known:
                status = self.classify(state, i)
                if status == Status.INCONSISTENT:
                    raise ValueError("INCONSISTENT: public clues conflict")
                if status in BINARY:
                    return Hint(i, status, self.related(state, i))
        return None

    def submit(self, cell_id, status):
        before = self.engine.public_state()
        result = self.engine.submit(cell_id, status, self.classify)
        if result == Verdict.ACCEPTED:
            after = self.engine.public_state()
            revealed_clue = next((c for c in after.clues if c.owner_cell == cell_id), None)
            active_clues = tuple(c.clue_id for c in before.clues)
            self.trace.record(
                Hint(cell_id, status, self.related(before, cell_id)),
                active_clues=active_clues,
                revealed_clue=revealed_clue,
            )
        return result

    def step(self):
        hint = self.get_hint()
        if hint and self.submit(hint.cell_id, hint.status) != Verdict.ACCEPTED:
            raise RuntimeError("Failed to apply an entailed move")
        return hint

    def auto_solve(self):
        while self.step():
            pass
        state = self.engine.public_state()
        return len(state.known) == len(state.people)
