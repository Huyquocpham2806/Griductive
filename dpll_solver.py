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
        # === TODO (CODE TAY) ===
        raise NotImplementedError("_simplify")

    def _unit_propagate(self, clauses: List[List[int]], assignment: Dict[int, bool],
                        stats: SolverStats) -> Tuple[Optional[List[List[int]]], Dict[int, bool]]:
        """Lặp khi tồn tại clause [l]. Gán |l| theo dấu, cộng propagations cho mỗi
        phép gán mới rồi gọi _simplify. Dừng ở điểm cố định; nếu xung đột trả
        (None, assignment). Kiểm tra clause rỗng trước khi coi là điểm cố định.
        """
        # === TODO (CODE TAY) ===
        raise NotImplementedError("_unit_propagate")

    def _dpll_recursive(self, clauses: List[List[int]], assignment: Dict[int, bool],
                        num_vars: int, stats: SolverStats) -> Tuple[bool, Optional[Dict[int, bool]]]:
        """Lan truyền trước. Conflict → (False,None); hết clause → (True,assignment).
        Chọn biến chưa gán có ID nhỏ nhất, cộng decisions một lần tại nút.
        Thử +v rồi −v trên bản sao assignment, rút gọn và đệ quy. Cộng backtracks
        mỗi nhánh thất bại bị bỏ. Trả model đầu tiên hoặc UNSAT khi cả hai thất bại.
        """
        # === TODO (CODE TAY) ===
        raise NotImplementedError("_dpll_recursive")
