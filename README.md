# Griductive Solver

Đồ án môn **CSC14003 · Introduction to Artificial Intelligence (Project 2)**.

**Griductive Solver** là trò chơi suy luận logic không đoán mò kết hợp tác tử trí tuệ nhân tạo (**Deductive Logic Agent**) dựa trên biểu diễn **Logic mệnh đề (CNF)** và bộ giải **SAT DPLL**. Mỗi nhân vật trên lưới là **Criminal** hoặc **Innocent**, và mọi manh mối khi được lật ra đều đúng sự thật. Một phán quyết chỉ được chấp nhận khi nó là hệ quả logic bắt buộc từ các dữ kiện công khai hiện có.

---

## 1. Yêu cầu môi trường & Cách chạy

- **Python 3.10 trở lên** và một trình duyệt web hiện đại.
- Dự án sử dụng **100% thư viện chuẩn Python** — không cần cài đặt thêm thư viện bên thứ ba (`requirements.txt` không có dependency ngoài).

Mở terminal trong thư mục `Source` và chạy:

```bash
# Khởi chạy ứng dụng Web UI (mặc định mở http://127.0.0.1:8765)
python main.py

# Tùy chọn đổi cổng hoặc không tự mở trình duyệt
python main.py --port 8080 --no-browser
```

### Các lệnh kiểm thử, thực nghiệm & sinh màn

```bash
# Chạy toàn bộ 12 bài kiểm thử (lõi logic + tích hợp Web UI)
python -m unittest discover -s tests -v

# Chạy thực nghiệm DPLL trên cả 8 màn mẫu (3x3, 4x4, 5x4, 5x5)
python benchmark.py

# Xuất bảng thực nghiệm ra file CSV để làm báo cáo
python benchmark.py --csv results.csv

# Sinh và kiểm chứng một màn chơi mới theo seed tái lập được
python puzzle_generator.py --rows 4 --cols 4 --extensions --seed 42 --output new_case.json
```

---

## 2. Hướng dẫn sử dụng giao diện Web UI

1. **Xem manh mối:** Bấm vào một thẻ đã lật để hiển thị nguyên văn manh mối ở khung **Evidence** và tô sáng tất cả các ô được manh mối đó nhắc tới.
2. **Phán quyết thẻ úp:** Bấm vào một thẻ úp rồi chọn **Innocent** hoặc **Criminal**:
   - `ACCEPTED`: Trạng thái được chứng minh logic bắt buộc → lật thẻ, cập nhật trạng thái và bổ sung manh mối mới vào cơ sở tri thức (`KB`).
   - `NOT_PROVABLE`: Cả hai khả năng đều còn thỏa mãn `KB` hiện tại → từ chối lật thẻ (kể cả khi đoán trùng đáp án ẩn).
   - `CONTRADICTED`: Các manh mối hiện tại ép trạng thái đối lập → từ chối và giữ kín thẻ.
3. **Ghi chú nháp:** Bật nút **Mark** (phím `M`) hoặc bấm **chuột phải** lên thẻ úp để gắn nhãn nháp `I?` / `C?`.
4. **Hỗ trợ & Tự giải:**
   - **Hint (`H`):** Chỉ ra một ô úp đã có thể suy luận chắc chắn cùng các thẻ manh mối liên quan (không tiết lộ nhãn đáp án).
   - **Step (`Space`):** Để tác tử DPLL tự suy diễn và mở 1 bước.
   - **Auto Solve:** Tự động giải liên tiếp toàn bộ bàn cờ với tốc độ tùy chỉnh (`1×`, `2×`, `4×`), có thể tạm dừng bất cứ lúc nào.
   - **Restart (`R`):** Đặt lại ván hiện tại về trạng thái ban đầu.
5. **Quản lý màn chơi & Kiểm tra:**
   - Chọn nhanh 8 màn có sẵn từ thanh stepper phía trên hoặc hộp chọn bên trái.
   - **Load** / **Share:** Nạp file màn chơi `.json` từ máy hoặc xuất màn hiện tại ra JSON.
   - **Generate:** Sinh màn mới (3×3, 4×4, 5×4, 5×5), bật/tắt manh mối mở rộng và nhập `seed` tùy chọn; mọi màn sinh ra đều được kiểm chứng tự động qua tác tử DPLL.
   - **Tab Solver & Tab Trace:** Theo dõi thời gian thực các chỉ số DPLL (`Primary Vars`, `Aux Vars`, `CNF Clauses`, `SAT Calls`, `Decisions`, `Propagations`, `Backtracks`, `Runtime`), kiểm tra nghiệm duy nhất (**Check Unique Solution**), và xem nhật ký suy diễn từng bước.
   - **Theme (`T`):** Chuyển đổi giữa giao diện *Dark Noir* và *Warm Paper*.

---

## 3. Cấu trúc mã nguồn & Kiến trúc hệ thống

| Tệp / Thư mục | Vai trò |
|---|---|
| `main.py` | Điểm vào chương trình, phân tích tham số dòng lệnh và khởi chạy máy chủ Web UI |
| `web_server.py`, `web/` | Máy chủ HTTP thuần stdlib (`ThreadingHTTPServer`), REST API JSON và giao diện Web (`index.html`, `styles.css`, `app.js`, `avatars.js`) |
| `models.py` | Định nghĩa kiểu dữ liệu (`Status`, `Verdict`, `Clue`, `Person`, `Cell`, `Puzzle`, `PublicState`, `SolverStats`, `Hint`, `TraceStep`, `DeductionTrace`) |
| `engine.py` | Đọc/ghi & xác thực đề JSON, giải nghĩa vùng (`resolve_region`), bộ đánh giá ngữ nghĩa trực tiếp (`evaluate_clue_directly`), và `GameEngine` |
| `cnf_encoder.py` | Ánh xạ biến mệnh đề và mã hóa tự động toàn bộ manh mối sang công thức CNF |
| `dpll_solver.py` | Bộ giải SAT DPLL với rút gọn, lan truyền đơn vị, rẽ nhánh xác định và quay lui |
| `logic_agent.py` | `classify_cell`, `check_uniqueness`, và `DeductiveAgent` (Hint, Step, Auto Solve, cache theo revision, ghi trace) |
| `puzzle_generator.py`, `puzzles/` | Bộ sinh màn suy diễn không cần đoán kèm 8 màn mẫu (`01` đến `08`) |
| `benchmark.py` | Chạy thực nghiệm tự động trên 8 màn mẫu và xuất số liệu CSV |
| `tests/` | Kiểm thử đơn vị lõi logic (`test_game.py`) và kiểm thử tích hợp HTTP Web UI (`test_web.py`) |

### Ranh giới cô lập thông tin (`GameEngine` vs `DeductiveAgent`)
- **`GameEngine`** sở hữu toàn bộ `Puzzle` gốc gồm `true_status` và `clue` của cả các thẻ đang úp.
- **`PublicState`** chỉ trích xuất danh sách `Person` (đã tước bỏ `true_status` và `clue`), tập trạng thái `known` và các `clues` của những thẻ **đã mở**.
- **`DeductiveAgent`** và **Web Frontend** chỉ được phép đọc `PublicState`. Mọi nước đi gửi lên `GameEngine.submit()` đều được kiểm chứng lại bằng phép suy diễn trên `PublicState` trước khi cho phép lật thẻ.

---

## 4. Thuật toán cốt lõi

### 4.1. Mã hóa CNF (`cnf_encoder.py`)
Mỗi nhân vật tại `(row, col)` tương ứng một biến mệnh đề chính `var_id = (row - 1) * num_cols + col` (`+v` biểu diễn **Criminal**, `-v` biểu diễn **Innocent**). Danh sách literal biểu diễn phép tuyển ($\lor$), danh sách clause biểu diễn phép hội ($\land$); `[]` là hằng đúng và `[[]]` là hằng sai.

- **6 mẫu manh mối cơ bản:** `FACT`, `SAME` ($a \leftrightarrow b$), `DIFFERENT` ($a \oplus b$), `AT_MOST` ($\sum x \le k$), `AT_LEAST` ($\sum x \ge k$), `EXACTLY` ($\sum x = k$).
- **2 mẫu manh mối mở rộng:**
  - `PARITY` (`EVEN` / `ODD`): Mã hóa chuỗi XOR tuyến tính theo kỹ thuật Tseitin bằng biến phụ từ `fresh_var()`, giữ số clause ở mức $4(n-1)+1$ thay vì bùng nổ hàm mũ.
  - `COMPARE_REGIONS` (`==`, `>`, `<`): Khử phần giao hai vùng để còn $A = R_1 \setminus R_2$, $B = R_2 \setminus R_1$, biến đổi $\sum A - \sum B = \sum (A \cup \{\neg b \mid b \in B\}) - |B|$ và tái sử dụng các hàm đếm với literal có dấu.
- **Các vùng hỗ trợ:** `ROW`, `COL`, `NEIGHBORS`, `CELLS` cùng các vùng mở rộng `COMMON_NEIGHBORS`, `CORNERS`, `BOUNDARY`.
- **Bộ đánh giá ngữ nghĩa trực tiếp:** `evaluate_clue_directly()` trong `engine.py` đánh giá trực tiếp tính đúng/sai của mọi loại manh mối trên phép gán đầy đủ mà không gọi `CNFEncoder`.

### 4.2. Bộ giải SAT DPLL (`dpll_solver.py`)
1. `_simplify(clauses, literal)`: Loại các clause đã thỏa mãn, xóa `-literal` khỏi các clause còn lại; phát hiện ngay clause rỗng (conflict → `None`).
2. `_unit_propagate(clauses, assignment, stats)`: Lặp lan truyền unit clause `[l]` đến điểm cố định, ghi nhận `propagations`.
3. `_dpll_recursive(...)`: Chạy lan truyền đơn vị trước, chọn biến chưa gán có ID nhỏ nhất (tính xác định), thử nhánh `+v` rồi `-v` trên bản sao phép gán, ghi nhận `decisions`, `backtracks`, và thời gian thực thi `runtime_sec`.

### 4.3. Suy diễn hệ quả logic & Kiểm tra duy nhất (`logic_agent.py`)
- **`classify_cell(public_state, cell_id)`:** Chứng minh bằng phản chứng qua 2 truy vấn SAT trên cùng `KB` với giả thiết `[+v]` và `[-v]`:

| `SAT(KB ∧ Cᵢ)` | `SAT(KB ∧ ¬Cᵢ)` | Kết luận |
|---|---|---|
| Có | Không | `CRIMINAL` |
| Không | Có | `INNOCENT` |
| Có | Có | `UNKNOWN` |
| Không | Không | `INCONSISTENT` |

- **`check_uniqueness(all_clues, num_rows, num_cols)`:** Tìm mô hình đầu tiên $M$, thêm đúng 1 **blocking clause** phủ định phép gán trên các **biến ô chính** `1..primary_vars` (bỏ qua biến phụ `aux_vars`), rồi giải lại; trả `True` khi và chỉ khi lần giải thứ hai là `UNSAT`.
- **`DeductionTrace`:** Lưu đầy đủ từng bước (`TraceStep` và chuỗi `entries`) gồm: số bước, phán quyết, kết quả 2 truy vấn SAT, danh sách `clue_id` đang kích hoạt, và manh mối mới vừa mở.

---

## 5. Kết quả thực nghiệm (DPLL)

Kết quả chạy `python benchmark.py` trên 8 màn mẫu có sẵn (tất cả đều giải hoàn toàn bằng DPLL, 0 lần đoán mò):

| Màn chơi | Lưới | Mở sẵn | Bước suy diễn | Primary Vars | Aux Vars | CNF Clauses | SAT Calls | Decisions | Propagations | Backtracks | Inference (ms) | Wall (ms) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `03_grid_3x3_easy` | 3×3 | 1 | 8 | 9 | 0 | 42 | 44 | 23 | 253 | 0 | 0.84 | 2.03 |
| `04_grid_3x3_extensions` | 3×3 | 2 | 7 | 9 | 3 | 46 | 24 | 16 | 223 | 0 | 0.93 | 2.03 |
| `05_grid_4x4_medium` | 4×4 | 1 | 15 | 16 | 0 | 82 | 92 | 35 | 692 | 1 | 2.94 | 6.76 |
| `06_grid_4x4_hard` | 4×4 | 2 | 14 | 16 | 6 | 95 | 100 | 65 | 1238 | 10 | 6.69 | 12.57 |
| `01_classic_5x4_normal` | 5×4 | 1 | 19 | 20 | 0 | 180 | 144 | 156 | 1574 | 0 | 9.63 | 18.24 |
| `02_classic_5x4_hard` | 5×4 | 2 | 18 | 20 | 8 | 133 | 148 | 218 | 2619 | 19 | 19.29 | 28.84 |
| `07_grid_5x5_stress_1` | 5×5 | 1 | 24 | 25 | 0 | 230 | 174 | 253 | 2212 | 18 | 17.50 | 29.61 |
| `08_grid_5x5_stress_2` | 5×5 | 2 | 23 | 25 | 7 | 243 | 246 | 544 | 4339 | 145 | 39.89 | 58.51 |

**Giải thích cột số liệu:** `primary_vars`, `aux_vars` và `cnf_clauses` mô tả kích thước `KB` tại truy vấn gần nhất; các bộ đếm `sat_calls`, `decisions`, `propagations`, `backtracks` và `inference_ms` được cộng dồn trong suốt ván chơi. `wall_ms` là tổng thời gian toàn vòng giải tự động bao gồm xử lý trạng thái và ghi trace.

---

## 6. Kiểm thử

- `tests/test_game.py`: Kiểm tra hình học vùng, đối chiếu chéo `CNFEncoder + DPLLSolver` với `evaluate_clue_directly` trên toàn bộ phép gán bộ phận, kiểm tra tham số biên, `PublicState`, các loại verdict, `DeductionTrace`, kiểm tra nghiệm duy nhất và giải đủ 8 màn mẫu.
- `tests/test_web.py`: Khởi chạy máy chủ HTTP nội bộ để kiểm thử tích hợp các endpoint `/`, `/api/cases`, `/api/state`, `/api/case`, `/api/hint`, `/api/submit`, `/api/step`, `/api/restart`, `/api/generate`, `/api/check_uniqueness`, `/api/export` và `/api/load_json`.
