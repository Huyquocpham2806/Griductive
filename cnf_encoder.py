"""Một biến C_i cho mỗi người. Literal dương biểu diễn CRIMINAL."""
from typing import List

from engine import clue_groups
from models import BINARY, Status, board_ids


class CNFEncoder:
    def __init__(self, num_rows, num_cols):
        self.num_rows, self.num_cols = num_rows, num_cols
        self.var_to_cell = dict(enumerate(board_ids(num_rows, num_cols), start=1))
        self.cell_to_var = {cell: var for var, cell in self.var_to_cell.items()}
        self.primary_vars = len(self.var_to_cell)
        self.num_vars = self.primary_vars
        self.num_clauses = 0

    @property
    def aux_vars(self):
        return self.num_vars - self.primary_vars

    def fresh_var(self):
        self.num_vars += 1
        return self.num_vars

    def encode_clue(self, clue):
        groups = [[self.cell_to_var[i] for i in ids]
                  for ids in clue_groups(clue, self.num_rows, self.num_cols)]
        v, p, kind = groups[0], clue.params, clue.clue_type
        if kind == "FACT":
            return [[v[0] if p["status"] == Status.CRIMINAL else -v[0]]]
        if kind in ("SAME", "DIFFERENT"):
            fn = self.encode_same if kind == "SAME" else self.encode_different
            return fn(*v)
        if kind == "COMPARE_REGIONS":
            return self.encode_compare_regions(p["op"], v, groups[1])
        if kind == "PARITY":
            return self.encode_parity(p["parity"], v)
        method = {"EXACTLY": self.encode_exactly, "AT_LEAST": self.encode_at_least,
                  "AT_MOST": self.encode_at_most}[kind]
        return method(p["k"], v)

    def build_kb(self, public_state):
        if (public_state.num_rows, public_state.num_cols) != (self.num_rows, self.num_cols):
            raise ValueError("Encoder and board dimensions differ")
        self.num_vars, self.num_clauses = self.primary_vars, 0
        clauses = []
        for cell, status in public_state.known.items():
            if status not in BINARY:
                raise ValueError("Known cells need binary status")
            v = self.cell_to_var[cell]
            clauses.append([v if status == Status.CRIMINAL else -v])
        for clue in public_state.clues:
            clauses.extend(self.encode_clue(clue))
        self.num_clauses = len(clauses)
        return clauses

    def encode_same(self, var_a: int, var_b: int) -> List[List[int]]:
        """a ↔ b. Tách thành a→b và b→a. Đổi từng kéo theo thành một clause."""
        # === TODO (CODE TAY) ===
        raise NotImplementedError("encode_same")

    def encode_different(self, var_a: int, var_b: int) -> List[List[int]]:
        """a XOR b. Loại hai hàng 00 và 11 khỏi bảng chân trị bằng hai clause."""
        # === TODO (CODE TAY) ===
        raise NotImplementedError("encode_different")

    def encode_at_most(self, k: int, region_vars: List[int]) -> List[List[int]]:
        """Σx ≤ k. Với mỗi tập k+1 biến, cấm tất cả cùng đúng bằng literal âm.
        k≥n trả [] (hằng đúng), k<0 trả [[]] (hằng sai). Kiểm tra cả n=0.
        """
        # === TODO (CODE TAY) ===
        raise NotImplementedError("encode_at_most")

    def encode_at_least(self, k: int, region_vars: List[int]) -> List[List[int]]:
        """Σx ≥ k. Mỗi tập n−k+1 biến cần ít nhất một literal dương đúng.
        k≤0 trả [], k>n trả [[]]. Thử n=3, k=2 trên đủ 8 phép gán.
        """
        # === TODO (CODE TAY) ===
        raise NotImplementedError("encode_at_least")

    def encode_exactly(self, k: int, region_vars: List[int]) -> List[List[int]]:
        """Σx = k iff (Σx ≥ k) ∧ (Σx ≤ k). Ghép hai danh sách clause."""
        # === TODO (CODE TAY) ===
        raise NotImplementedError("encode_exactly")

    def encode_parity(self, parity_type: str, region_vars: List[int]) -> List[List[int]]:
        """XOR toàn vùng bằng 1 cho ODD, bằng 0 cho EVEN. Bắt đầu với 0.
        Nối từng bit bằng z ↔ (x XOR y), cấp z qua fresh_var(), chặn bốn hàng sai
        của bảng ba biến. Ép bit cuối bằng unit clause. Chú ý vùng rỗng/đơn.
        """
        # === TODO (CODE TAY) ===
        raise NotImplementedError("encode_parity")

    def encode_compare_regions(self, op: str, vars_r1: List[int], vars_r2: List[int]) -> List[List[int]]:
        """Khử biến chung vì chúng đóng góp bằng nhau cho hai vế.
        Gọi A,B là hai tập còn lại. ΣA−ΣB = Σ(A ∪ {¬b | b∈B})−|B|.
        Với ==, >, < lần lượt ép tổng literal bằng |B|, ≥|B|+1, ≤|B|−1.
        Các hàm cardinality cần nhận literal có dấu; đổi dấu để lấy phủ định.
        """
        # === TODO (CODE TAY) ===
        raise NotImplementedError("encode_compare_regions")
