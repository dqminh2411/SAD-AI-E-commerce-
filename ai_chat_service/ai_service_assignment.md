# AI Service Assignment
## 1. Yêu cầu:
YÊU CẦU NỘP FILE aiservice02_lớp.nhóm_tênho.PDF 
1. Trang bìa 
2. Mô tả AISERVICE  
3. Copy 20 dòng data 
4. Lời giải thích + Copy code Câu 2a và các ảnh. 
5. KB_Graph copy anh 20 dòng và ảnh graph (ảnh càng phức tạp-đẹp càng có giá trị) 
6. Câu 2c, 2d viết tài liệu + ảnh  
## 2. Nội dung bài làm
1. [2đ] Sinh ra tập dữ liệu data_user500.csv với 500 user + 8 behaviors bao gồm:
- user_id: ID người dùng
- product_id: ID sản phẩm
- action: 
- timestamp

2. Sử dụng data ở câu 1 để
a. [2đ] Xây dựng 3 mô hình RNN, LSTM, biLSTM để dựa đoán và phân loại. Đánh giá 3 mô hình và chọn ra mô hình tốt nhất model_best. Sử dụng các độ đo thích hợp và show plots để visualization kết quả. Đánh giá bằng lời khi chọn 
b. [2đ] Xây dựng knowledge Base graph (KB_Graph) với neo4j dựa trên tập dữ liệu này 
c. [2đ] Xây dựng RAG và chat dựa trên dựa trên KB_Graph  
d. [2đ] Triển khai tích hợp trong Hệ e-commerce. Hiển thị qua: 
    - Danh sách hàng khi khách hàng click search hay chọn vào giỏ hàng 
    - Giao diện Chat với user (Không phải giao diện thường của chatGPT)

## 3. Các bước làm bài chi tiết
1. Sinh dữ liệu:
- Sử dụng script `generate_fake_interactions.py` trong thư mục `neo4j/neo4j_import` để tạo ra file `fake_interactions.csv` với 500 user và 10 events mỗi user. Các events bao gồm:
    - view
    - add_to_cart
  - add_to_wishlist
    - purchase
    - search
    - filter
    - sort
    - remove_from_cart
    - checkout_start
    - chat
    Dữ liệu sản phẩm trong file `product_service/product_service/products_data.csv` được sử dụng để lấy `product_id` và `category` cho các events liên quan đến sản phẩm.
    Tổng số dòng sẽ xấp xỉ `users * events_per_user` (có thể lệch nhẹ tuỳ vào logic session/goal).
2. 
### 2a — RNN/LSTM/biLSTM dự đoán & phân loại (chọn model_best)

**Mục tiêu (bài toán)**
- Dùng chuỗi hành vi theo thời gian của từng user trong file `fake_interactions.csv` để học mô hình dự đoán **hành vi kế tiếp**.
- Vì hành vi kế tiếp thuộc một tập nhãn rời rạc (multi-class), nên đây là **bài toán phân loại đa lớp**, đồng thời cũng là **dự đoán (prediction)** vì nhãn chính là hành vi tiếp theo.

**Nhãn hành vi sử dụng (giữ nguyên như trong dữ liệu, không cần chuẩn hoá thêm)**
- `view`, `add_to_cart`, `add_to_wishlist`, `purchase`, `search`, `remove_from_cart`, `checkout_start`, `filter`

**Định nghĩa Input/Output**
- Với mỗi user, sắp xếp events theo `created_at` tăng dần để có chuỗi hành vi: `a1, a2, …, aT`.
- Chọn độ dài cửa sổ `seq_len = k` (ví dụ 5).
- Input tại thời điểm t: chuỗi hành vi k bước trước đó  
  `X_t = [a_{t-k}, …, a_{t-1}]`
- Output/label: hành vi kế tiếp  
  `y_t = a_t`

**Tiền xử lý dữ liệu**
1. Đọc [neo4j/neo4j_import/fake_interactions.csv](neo4j/neo4j_import/fake_interactions.csv)
2. Parse `created_at` → datetime, sort theo `(user_id, created_at)`
3. Tạo vocabulary nhãn hành vi trực tiếp từ `event_type` (vd: dùng LabelEncoder)
4. Với mỗi user: tạo mẫu theo sliding window để sinh (X, y)
5. Chia train/val/test theo **user_id** (tránh leakage giữa các mẫu của cùng 1 user)

**Train 3 mô hình (giữ các phần còn lại giống nhau để so sánh công bằng)**
- Input: chuỗi action-id dài `seq_len`
- Embedding: `Embedding(num_actions, emb_dim)`
- Encoder + classifier:
  1) RNN: `Embedding → SimpleRNN(hidden) → Dense(softmax)`
  2) LSTM: `Embedding → LSTM(hidden) → Dense(softmax)`
  3) biLSTM: `Embedding → Bidirectional(LSTM(hidden)) → Dense(softmax)`
- Loss: `sparse_categorical_crossentropy`
- Metrics báo cáo: `accuracy`, và đánh giá thêm `macro-F1` trên validation/test

**Validate, so sánh và chọn model_best**
- Vẽ plots: train/val loss, train/val accuracy cho từng model
- Tính trên test:
  - `accuracy`
  - `macro-F1`
  - `classification_report`, `confusion_matrix`
- Chọn `model_best` là model có `macro-F1` tốt nhất (hoặc tiêu chí bạn nêu rõ) và giải thích bằng lời vì sao chọn.

**Vai trò trong flow hệ thống e-commerce**
- Khi user thao tác (search/view/add_to_cart/…), hệ thống ghi event và cập nhật KB_Graph (Neo4j).
- `model_best` nhận chuỗi hành vi gần nhất của user và dự đoán hành vi tiếp theo (vd: dự đoán user sắp `purchase` hay sắp `search`).
- Kết quả dự đoán dùng như “tín hiệu” để điều hướng chiến lược lấy context từ Neo4j:
  - Nếu dự đoán sắp `purchase`/`checkout_start`: ưu tiên lấy top products theo `CARTED/VIEWED` (ý định mua cao)
  - Nếu dự đoán sắp `search/filter/sort/add_to_wishlist`: ưu tiên query/brand affinity để gợi ý danh sách phù hợp
  - Nếu dự đoán sắp `chat`: ưu tiên context FAQ/KB + sản phẩm user đang quan tâm

(Toàn bộ quy trình preprocessing + train + plots + lưu model_best được thực hiện trong notebook tạo ở bước tiếp theo.)

### 2b — Xây dựng KB_Graph với Neo4j
- Thiết kế schema graph: 
    - node types (User, Product)
  - relationship types (VIEWED, CARTED, WISHLISTED, PURCHASED, SEARCHED, SORTED, REMOVED_FROM_CART, STARTED_CHECKOUT).
- import data vào neo4j sử dụng script `import_interactions_500u.cypher` (đã có sẵn trong `neo4j/cypher`).
- Viết Cypher query để lấy “context” cho user_id + product_type:
    - Top products theo VIEWED/CARTED/PURCHASED (weight w, cnt, last_ts)
    - Brand affinity (đếm theo brand của products user tương tác)
### 2c — RAG + chat dựa trên KB_Graph (Neo4j)
Repo bạn đã có nền khá sẵn:

- Chat API nằm ở views.py và routing ở urls.py.
- Logic RAG + graph context nằm ở services.py (đã có FAISS + Neo4j driver).
- Cách hoàn thiện đúng “RAG dựa KB_Graph” để viết báo cáo:
- Retriever từ Neo4j (KB_Graph): viết Cypher lấy “context” theo user_id + product_type:
    - Top products theo VIEWED/CARTED/PURCHASED (weight w, cnt, last_ts)
    - Brand affinity (đếm theo brand của products user tương tác)
- Generator: nhét context Neo4j + (optional) FAISS chunks vào prompt (hiện bạn đang làm kiểu này là hợp lý).
- Bằng chứng trong báo cáo: chụp ảnh Neo4j Browser query trả về 20 dòng + ảnh graph; chụp ảnh response chat có “giải thích dựa trên hành vi user”.

### 2d — Tích hợp vào hệ e-commerce + hiển thị (search / add_to_cart) + UI chat:
