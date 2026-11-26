"""Giao ước solve trả về (sat, model, stats). Model SAT cần gán đủ mọi biến."""
from time import perf_counter
from typing import Dict, List, Optional, Tuple

from models import SolverStats


class DPLLSolver:
    def solve(self, clauses, num_vars, assumptions=None):
        """Assumptions chỉ có hiệu lực trong một lần gọi; đầu vào không bị sửa."""
        start = perf_counter()
        stats = SolverStats(sat_calls=1)
        if type(num_vars) is not int or num_vars < 0:
            raise ValueError("Invalid variable count")
        formula = [list(c) for c in clauses]
        formula.extend([lit] for lit in (assumptions or ()))
        if any(type(x) is not int or not 1 <= abs(x) <= num_vars for c in formula for x in c):
            raise ValueError("Literal outside 1..num_vars")
        sat, model = self._dpll_recursive(formula, {}, num_vars, stats)
        if sat:
            model = {i: model.get(i, False) for i in range(1, num_vars + 1)}
        stats.runtime_sec = perf_counter() - start
        return sat, model, stats

    def _simplify(self, clauses: List[List[int]], literal: int) -> Optional[List[List[int]]]:
        """Gán literal đúng. Bỏ clause chứa literal, bỏ −literal khỏi phần còn lại.
        Nếu một clause rỗng (kể cả rỗng từ đầu), trả None. [] toàn công thức là SAT.
        Tạo danh sách mới để hai nhánh luôn độc lập.
        """

        negative_lit = -literal
        simplified: List[List[int]] = []

        for clause in clauses:
            if not clause:
                return None

            if literal in clause:
                continue

            new_clause = [lit for lit in clause if lit != negative_lit]
            if not new_clause:
                return None

            simplified.append(new_clause)

        return simplified
        
        raise NotImplementedError("_simplify")

    def _unit_propagate(self, clauses: List[List[int]], assignment: Dict[int, bool],
                        stats: SolverStats) -> Tuple[Optional[List[List[int]]], Dict[int, bool]]:
        """Lặp khi tồn tại clause [l]. Gán |l| theo dấu, cộng propagations cho mỗi
        phép gán mới rồi gọi _simplify. Dừng ở điểm cố định; nếu xung đột trả
        (None, assignment). Kiểm tra clause rỗng trước khi coi là điểm cố định.
        """

        current_clauses = clauses
        current_assignment = assignment.copy()

        while True:
            unit: Optional[int] = None

            for clause in current_clauses:
                if not clause:
                    return None, current_assignment
                if len(clause) == 1 and unit is None:
                    unit = clause[0]

            if unit is None:
                return current_clauses, current_assignment

            var = abs(unit)
            val = unit > 0

            if var in current_assignment:
                if current_assignment[var] != val:
                    return None, current_assignment
            else:
                current_assignment[var] = val
                stats.propagations += 1

            current_clauses = self._simplify(current_clauses, unit)
            if current_clauses is None:
                return None, current_assignment

        raise NotImplementedError("_unit_propagate")

    def _dpll_recursive(self, clauses: List[List[int]], assignment: Dict[int, bool],
                        num_vars: int, stats: SolverStats) -> Tuple[bool, Optional[Dict[int, bool]]]:
        """Lan truyền trước. Conflict → (False,None); hết clause → (True,assignment).
        Chọn biến chưa gán có ID nhỏ nhất, cộng decisions một lần tại nút.
        Thử +v rồi −v trên bản sao assignment, rút gọn và đệ quy. Cộng backtracks
        mỗi nhánh thất bại bị bỏ. Trả model đầu tiên hoặc UNSAT khi cả hai thất bại.
        """
        # === TODO (CODE TAY) ===

        simplified_clauses, current_assignment = self._unit_propagate(clauses, assignment, stats)
        if simplified_clauses is None:
            return False, None
        if not simplified_clauses:
            return True, current_assignment

        var = min(
            (
                abs(lit)
                for clause in simplified_clauses
                for lit in clause
                if abs(lit) not in current_assignment
            ),
            default=None
        )

        if var is None:
            satisfied = all(
                any((lit > 0) == current_assignment[abs(lit)] for lit in clause)
                for clause in simplified_clauses
            )
            return (True, current_assignment) if satisfied else (False, None)

        stats.decisions += 1
        for value, literal in ((True, var), (False, -var)):
            branch_assignment = current_assignment.copy()
            branch_assignment[var] = value
            branch_clauses = self._simplify(simplified_clauses, literal)

            if branch_clauses is not None:
                sat, model = self._dpll_recursive(branch_clauses, branch_assignment, num_vars, stats)
                if sat:
                    return True, model
            stats.backtracks += 1
        
        return False, None
        raise NotImplementedError("_dpll_recursive")
