# Griductive Solver

Đồ án CSC14003 · Project 2. Người chơi phân loại từng nhân vật bằng các manh mối đang mở. Mở đúng một thẻ sẽ bổ sung một sự kiện và một manh mối mới vào cơ sở tri thức. Ba phần thuật toán dành cho sinh viên nằm trong `cnf_encoder.py`, `dpll_solver.py` và `logic_agent.py`.

## Chạy trên Windows hoặc Anaconda

Giải nén cả thư mục `Source`. Mở Anaconda Prompt hoặc terminal trong thư mục chứa `Source` và chạy:

```console
cd Source
python main.py
```

Dùng Python 3.10 trở lên với Tk 8.6. Chạy `python -m tkinter` để kiểm tra cửa sổ Tk trong môi trường Python đang chọn. Trên Ubuntu/Debian dùng gói `python3-tk` tương ứng với Python hệ thống. Các mô-đun Python của dự án đều thuộc thư viện chuẩn.

## Chơi một ván

Màn mặc định có **5 hàng và 4 cột**, từ A1 đến D5. Mỗi người, kể cả tội phạm, đều cung cấp một manh mối đúng.

1. Bấm vào thẻ đã mở hoặc biểu tượng kính lúp. Khung **Evidence** hiện nguyên văn manh mối. Viền vàng đánh dấu thẻ được chọn và những ô được nhắc đến.
2. Bấm thẻ úp, chọn **Innocent** hoặc **Criminal**. `ACCEPTED` mở thẻ. `NOT_PROVABLE` nghĩa là cả hai kết luận còn khả dĩ. `CONTRADICTED` nghĩa là các manh mối buộc phải chọn trạng thái đối lập. Hai trường hợp bị từ chối đều giữ kín thông tin trên thẻ.
3. **Hint** đánh dấu một thẻ có thể kết luận và các thẻ có manh mối nhắc trực tiếp đến nó. Các manh mối liên quan có thể cần kết hợp với những dữ kiện khác. **Step** thực hiện một phán quyết, **Auto Solve** lặp từng bước và có thể tạm dừng. **Restart** quay lại cùng bộ manh mối.
4. Chọn một màn rồi bấm **Generate New** để tạo ván cùng kích thước và cấu hình mở rộng. Ván mới được kiểm chứng trước khi mở. Có thể lưu ván tái lập bằng trình sinh dòng lệnh bên dưới.

**Thử suy luận ở màn 02.** Thẻ A1 đã mở và là Innocent. Manh mối của A1 cho biết số tội phạm trong {A2, A4} là chẵn. Manh mối của A5 cho biết số đó lớn hơn số tội phạm trong {A1}. Điều kiện đầu cho hai khả năng 0 và 2. Điều kiện sau loại 0. Vì vậy A2 và A4 đều là Criminal, và người chơi có thể mở một trong hai trước.

## Dòng dữ liệu

| Tệp | Vai trò |
|---|---|
| `main.py`, `gui.py` | Khởi chạy Tk, vẽ thẻ Canvas, điều khiển lượt đi và hoạt ảnh |
| `models.py` | Kiểu dữ liệu, trạng thái, thống kê và cờ fallback |
| `engine.py` | Đọc/ghi JSON, kiểm tra manh mối, xác định vùng, tạo `PublicState`, kiểm soát mở thẻ |
| `logic_agent.py` | Phân loại, Hint/Step/Auto Solve, truy vấn tính duy nhất, ghi trace |
| `cnf_encoder.py`, `dpll_solver.py` | Giao diện CNF và SAT, instrumentation và các bài tập tự cài đặt |
| `puzzle_generator.py`, `puzzles/` | Sinh màn có chuỗi suy diễn và tám màn mẫu |
| `benchmark.py`, `tests/` | Thực nghiệm và kiểm thử độc lập |

`PublicState` chứa tọa độ, tên, nghề của mọi người, trạng thái đã mở và các manh mối đã mở. Tác tử chỉ truy vấn bản chiếu này. Engine giữ lời giải riêng để xác minh dữ liệu và phát nội dung thẻ sau khi chấp nhận phán quyết. Bộ nhớ đệm kết luận được xóa khi tập dữ kiện công khai thay đổi.

**Cơ chế dự phòng.** Mỗi truy vấn thử thuật toán sinh viên trước. Khi gặp `NotImplementedError` và cờ `USE_FALLBACK_WHEN_TODO_NOT_IMPLEMENTED` đang bật, bộ tìm kiếm ngữ nghĩa thử hai giả thiết về ô cần xét. Nó duyệt các biến trong phạm vi manh mối công khai, cắt nhánh bất khả thi bằng cận số lượng, rồi gọi `evaluate_clue_directly` trên từng phạm vi đã gán đủ. Một trạng thái được chứng minh khi chính nó có mô hình và trạng thái đối lập hết mô hình. Bộ tìm kiếm có độ phức tạp xấu nhất theo hàm mũ của số biến được nhắc đến. Tìm kiếm trong quá trình chứng minh không tạo nước đi trên bàn.

## Hoàn thiện 3 phần thuật toán

Tìm dấu `# === TODO (CODE TAY) ===` trong tệp Python. Có **12 hàm thuộc 3 mô-đun**. Mỗi hàm có docstring nêu công thức, giao ước trả về và trường hợp biên. Giữ nguyên chữ ký để dùng được GUI và benchmark.

### 1. Mã hóa CNF · 7 hàm

Quy ước `C_i = True` là Criminal. Ánh xạ theo hàng, `var_id = (row - 1) * num_cols + col`. Danh sách literal là một phép tuyển, danh sách clause là một phép hội. Công thức `[]` luôn đúng, còn `[[]]` luôn sai.

- **SAME và DIFFERENT.** Viết bảng chân trị hai biến, mỗi hàng sai sinh một clause chặn đúng phép gán đó. Dùng cả trường hợp hai đối số cùng chỉ một ô.
- **AT_MOST và AT_LEAST.** Với n biến, lần lượt xét mọi nhóm k+1 biến cùng đúng hoặc n−k+1 biến cùng sai. Viết hàm cho cả literal âm để tái sử dụng trong so sánh vùng. Thử n=0, k=0, k=n và ngưỡng ngoài miền. **EXACTLY** ghép hai ràng buộc cùng ngưỡng.
- **PARITY.** Nối các XOR bằng biến phụ từ `fresh_var()`. Với từng hàng sai của `z ↔ (a XOR b)`, thêm một clause chặn. Ép giá trị bit cuối. XOR của tập rỗng bằng 0.
- **COMPARE_REGIONS.** Loại giao hai vùng. Với hai phần còn lại A, B, thay tổng ở vế trái bằng tổng các literal dương trong A cùng các literal âm trong B. Ngưỡng so sánh mới là |B|. Chuyển bất đẳng thức nghiêm thành ngưỡng nguyên liền kề.

Để kiểm tra encoder riêng, cố định mỗi phép gán trên **biến ô**, cho các biến phụ tự do. Công thức CNF phải có ít nhất một cách gán biến phụ khi và chỉ khi bộ đánh giá trực tiếp trả về đúng. Có thể bắt đầu với vùng 2–3 ô.

### 2. DPLL · 3 hàm

1. `_simplify` gán một literal, loại clause đã đúng và bỏ literal đối lập trong các clause còn lại. Dùng `None` cho conflict. Kiểm tra riêng công thức hết clause và công thức chứa clause rỗng.
2. `_unit_propagate` áp dụng unit clause đến điểm cố định. Ví dụ `[[1], [-1, 2], [-2]]` phải dẫn đến conflict. Mỗi phép gán bắt buộc mới tăng `propagations`.
3. `_dpll_recursive` lan truyền, chọn biến chưa gán có ID nhỏ nhất, thử nhánh dương trước. Mỗi nhánh có assignment riêng. Đếm `decisions` ở nút rẽ nhánh và `backtracks` khi bỏ một nhánh thất bại. `solve` hoàn thiện các biến tự do trong model và đo thời gian cho mỗi lần gọi.

### 3. Tác tử · 2 hàm

Với một ô i, gọi SAT hai lần trên cùng KB, lần lượt với giả thiết +i và −i.

| SAT(KB ∧ Cᵢ) | SAT(KB ∧ ¬Cᵢ) | Kết luận |
|---|---|---|
| Có | Có | UNKNOWN |
| Có | Không | CRIMINAL |
| Không | Có | INNOCENT |
| Không | Không | INCONSISTENT |

`classify_cell` trả trạng thái cùng tổng thống kê của hai truy vấn. `check_uniqueness` tìm một nghiệm, chặn **toàn bộ phép gán trên biến ô** bằng một clause rồi giải lại. Nếu lần đầu UNSAT hoặc lần hai SAT thì không có đúng một nghiệm. Hai hàm này kiểm tra hai thuộc tính khác nhau: nghiệm duy nhất của tất cả manh mối chỉ phản ánh toàn bộ đáp án, còn khả năng chơi từng bước cần một phép suy diễn từ các thẻ đã mở tại từng lượt.

Sau khi điền đủ các hàm, chương trình dùng CNF và DPLL tự động. Lệnh `python benchmark.py --require-dpll` tắt fallback cho lần chạy đó để phát hiện ngay một hàm còn thiếu.

## Sinh màn và tái lập thực nghiệm

Từ thư mục `Source`:

```console
python puzzle_generator.py --rows 5 --cols 4 --extensions --seed 42 --output new_case.json
python -m unittest discover -s tests -v
python benchmark.py
python benchmark.py --csv results.csv
```

Màn cùng seed, kích thước và cấu hình được tái tạo trên cùng phiên bản Python. Thuật toán chọn trước trạng thái ẩn, xây dựng chuỗi manh mối từ một tập thẻ đã biết, rồi kiểm chứng bằng tác tử chơi lại theo thứ tự quét bàn. Một ràng buộc đếm có đúng một thành viên chưa biết sẽ xác định thành viên đó nếu ngưỡng được chọn chặt. Các màn mở rộng từ bốn ô trở lên bắt đầu bằng cặp ràng buộc số chẵn và so sánh số lượng. Có thể chọn các thẻ đã được chứng minh theo thứ tự khác vì bổ sung dữ kiện đúng luôn bảo toàn hệ quả đã có.

| Màn | Kích thước (hàng × cột) | Mở sẵn | Bước suy diễn | Kết quả fallback |
|---|---:|---:|---:|---:|
| 01 · The Column B Inquiry | 5 × 4 | 1 | 19 | 20/20 |
| 02 · Two Witnesses | 5 × 4 | 2 | 18 | 20/20 |
| 03 · The First Witness | 3 × 3 | 1 | 8 | 9/9 |
| 04 · Odd Company | 3 × 3 | 2 | 7 | 9/9 |
| 05 · The Corner Office | 4 × 4 | 1 | 15 | 16/16 |
| 06 · A Shared Alibi | 4 × 4 | 2 | 14 | 16/16 |
| 07 · The Night Shift | 5 × 5 | 1 | 24 | 25/25 |
| 08 · The Last Comparison | 5 × 5 | 2 | 23 | 25/25 |

**Đọc số liệu.** `inference_ms` cộng thời gian suy diễn của backend, `wall_ms` đo toàn bộ vòng chơi tự động, gồm cả xử lý state và trace. `primary_vars` là số biến ô. `aux_vars` và `cnf_clauses` mô tả KB của truy vấn gần nhất. Các bộ đếm SAT tích lũy theo ván. Trong chế độ Fallback, không có lần gọi DPLL nên SAT Calls, Decisions, Propagations, Backtracks và kích thước CNF bằng 0. Khi viết báo cáo về DPLL, thu lại số liệu bằng `--require-dpll` sau khi hoàn thành bài tập.

Kiểm thử đối chiếu các kiểu manh mối với bảng chân trị, thử các phép gán bộ phận, vùng chồng lấp, KB mâu thuẫn, phán quyết sai và phán quyết đoán đúng nhưng chưa đủ bằng chứng. Tám màn được kiểm tra cả tính duy nhất lẫn khả năng mở hết từ đầu. Test GUI gửi sự kiện chuột tới Tk và chạy timer Auto Solve thật. Test này tự bỏ qua trong môi trường không có màn hình.
