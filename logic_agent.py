"""Suy diễn chỉ đọc PublicState. Fallback tìm mô hình trực tiếp trong miền nhị phân."""
from collections import Counter
from time import perf_counter
from typing import List, Tuple

import models
from cnf_encoder import CNFEncoder
from dpll_solver import DPLLSolver
from engine import clue_groups, evaluate_clue_directly
from models import BINARY, Clue, DeductionTrace, Hint, PublicState, SolverStats, Status, Verdict, board_ids


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
    sat_pos, _, stats_pos = solver.solve(kb, encoder.num_vars, assumptions = [var])
    sat_neg, _, stats_neg = solver.solve(kb, encoder.num_vars, assumptions = [-var])

    if sat_pos and not sat_neg:
        status = Status.CRIMINAL
    elif not sat_pos and sat_neg:
        status = Status.INNOCENT
    elif sat_pos and sat_neg:
        status = Status.UNKNOWN
    else:
        status = Status.INCONSISTENT

    stats = SolverStats(
        mode = "DPLL",
        primary_vars = encoder.primary_vars,
        aux_vars = encoder.aux_vars,
        cnf_clauses = encoder.num_clauses,
        sat_calls = stats_pos.sat_calls + stats_neg.sat_calls,
        decisions = stats_pos.decisions + stats_neg.decisions,
        propagations = stats_pos.propagations + stats_neg.propagations,
        backtracks = stats_pos.backtracks + stats_neg.backtracks,
        runtime_sec = stats_pos.runtime_sec + stats_neg.runtime_sec
    )

    return status, stats

    raise NotImplementedError("classify_cell")


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
    
    raise NotImplementedError("check_uniqueness")


class SemanticSearch:
    """Exact finite-domain search. Only cells mentioned by visible clues need branching."""
    def __init__(self, rows, cols, clues):
        self.rows, self.cols = rows, cols
        self.constraints = []
        freq = Counter()
        for clue in clues:
            groups = clue_groups(clue, rows, cols)
            scope = tuple(dict.fromkeys(i for group in groups for i in group))
            self.constraints.append((clue, groups, scope))
            freq.update(scope)
        self.order = tuple(sorted(freq, key=lambda i: (-freq[i], i)))

    def possible(self, clue, groups, scope, assignment):
        if all(i in assignment for i in scope):
            return evaluate_clue_directly(clue, assignment, self.rows, self.cols, groups=groups)
        kind, p = clue.clue_type, clue.params
        if kind in ("EXACTLY", "AT_MOST", "AT_LEAST"):
            lo = sum(assignment.get(i) == Status.CRIMINAL for i in scope)
            hi = lo + sum(i not in assignment for i in scope)
            if kind == "EXACTLY":
                return lo <= p["k"] <= hi
            return lo <= p["k"] if kind == "AT_MOST" else hi >= p["k"]
        if kind == "COMPARE_REGIONS":
            left, right = map(set, groups)
            a, b = left-right, right-left
            delta = (sum(assignment.get(i) == Status.CRIMINAL for i in a)
                     - sum(assignment.get(i) == Status.CRIMINAL for i in b))
            lo, hi = delta - len(b-assignment.keys()), delta + len(a-assignment.keys())
            return {"==": lo <= 0 <= hi, "<": lo < 0, ">": hi > 0}[p["op"]]
        return True

    def witness(self, facts):
        assignment = dict(facts)

        def visit():
            if any(not self.possible(c, g, s, assignment) for c, g, s in self.constraints):
                return None
            var = next((i for i in self.order if i not in assignment), None)
            if var is None:
                return assignment.copy()
            for status in BINARY:
                assignment[var] = status
                model = visit()
                if model is not None:
                    return model
            del assignment[var]
            return None

        return visit()


def uniqueness(all_clues, num_rows, num_cols):
    """Public wrapper. Returns uniqueness over cell statuses across all supplied clues."""
    try:
        return check_uniqueness(all_clues, num_rows, num_cols)
    except NotImplementedError:
        if not models.USE_FALLBACK_WHEN_TODO_NOT_IMPLEMENTED:
            raise
    search = SemanticSearch(num_rows, num_cols, all_clues)
    model = search.witness({})
    if model is None:
        return False
    for i in board_ids(num_rows, num_cols):
        if i not in model:
            return False
        opposite = Status.CRIMINAL if model[i] == Status.INNOCENT else Status.INNOCENT
        if search.witness({i: opposite}) is not None:
            return False
    return True


class DeductiveAgent:
    def __init__(self, engine):
        self.engine = engine
        self.trace = DeductionTrace()
        self.stats = SolverStats(mode="—")
        self._revision = None
        self._cache = {}

    def classify(self, state, cell_id):
        if cell_id not in {p.cell_id for p in state.people}:
            raise ValueError("Unknown cell")
        revision = (state.known, state.clues)
        if revision != self._revision:
            self._revision = (state.known.copy(), state.clues)
            self._cache.clear()
            self._search = None
        if cell_id in self._cache:
            return self._cache[cell_id]
        try:
            status, stats = classify_cell(state, cell_id)
        except NotImplementedError:
            if not models.USE_FALLBACK_WHEN_TODO_NOT_IMPLEMENTED:
                raise
            start = perf_counter()
            if self._search is None:
                self._search = SemanticSearch(state.num_rows, state.num_cols, state.clues)
            allowed = []
            for s in BINARY:
                if cell_id in state.known and state.known[cell_id] != s:
                    continue
                if self._search.witness({**state.known, cell_id: s}) is not None:
                    allowed.append(s)
            status = (allowed[0] if len(allowed) == 1 else
                      Status.UNKNOWN if allowed else Status.INCONSISTENT)
            stats = SolverStats(mode="Fallback", primary_vars=len(state.people),
                                runtime_sec=perf_counter()-start)
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
        state = self.engine.public_state()
        result = self.engine.submit(cell_id, status, self.classify)
        if result == Verdict.ACCEPTED:
            self.trace.record(Hint(cell_id, status, self.related(state, cell_id)))
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
