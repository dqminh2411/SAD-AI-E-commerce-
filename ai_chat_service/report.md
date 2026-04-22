# Viết bài báo cáo Latex cho phần AI Chat Service
## 1. Bố cục báo cáo
- **Trang bìa**: có bố cục giống `assets/report_cover_template.png` (bạn có thể dùng LaTeX template để tạo trang bìa này).
- **Mục lục**: liệt kê các phần chính của báo cáo.
- **Chương 1**: Giới thiệu chung về AI Chat Service (mục tiêu, phạm vi, công nghệ sử dụng, vai trò trong hệ thống E-commerce). sử dụng `../README.md` của project làm nguồn chính.
- **Chương 2**: Mô tả tập dữ liệu `data_user500.csv` (cấu trúc, các trường dữ liệu, thống kê cơ bản). kẻ bảng liệt kê các trường dữ liệu và giải thích ý nghĩa của chúng.
    - quá trình tạo dữ liệu giả (fake data generation) cũng nên được mô tả ngắn gọn (sử dụng `generate_fake_interactions.py`, ghi là `generate_data.py`), giải thích cách tạo ra dữ liệu tương tác cho 500 người dùng.
    - trình bày phân bố dữ liệu, với mỗi behavior có bao nhiêu dòng, có 500 user, v.v. sử dụng các biểu đồ (bar chart, pie chart) để minh họa phân bố này. (sử dụng ảnh `assets/input_distribution_event_type.png`). phân bố như sau (dạng csv):
        event_type, count
        search,6154
        view,6127
        add_to_wishlist,4972
        filter,994
        add_to_cart,930
        checkout_start,240
        purchase,207
        remove_from_cart,192
    - trích xuất 20 dòng dữ liệu từ `data_user500.csv` để minh họa (chụp ảnh bảng, lấy ảnh `assets/20_lines_data.png`).
- **Chương 3**: Xây dựng và đánh giá mô hình RNN/LSTM/biLSTM để dự đoán hành vi kế tiếp của user dựa trên chuỗi hành vi trước đó. Mô tả cách bạn định nghĩa bài toán (input/output), cách tiền xử lý dữ liệu, kiến trúc mô hình, quá trình huấn luyện và đánh giá. So sánh kết quả giữa 3 mô hình và chọn ra model_best. Show plots để visualization kết quả (loss curve, confusion matrix, v.v.).
    - Lý thuyết nền tảng có liên hệ với hệ thống E-commerce
    - copy code từ notebook `behavior_sequence_models.ipynb` (câu 2a) vào báo cáo, giải thích chi tiết từng bước từ các quá trình tiền xử lý, xây dựng mô hình, huấn luyện đến đánh giá, có sử dụng các ảnh confusion trong `assets/` và giải thích.
    - khi so sánh các mô hình, sử dụng ảnh `plot_accuracy_3models.png`, `plot_loss_3models.png`, `plot_macro_f1_3models.png`, sử dụng `metrics_summary.json`
- **Chương 4**: Mô tả chi tiết về RAG + KB_Graph (Neo4j) implementation:
    - kiến trúc GraphRAG: VectorDB (FAISS) + KB_Graph (Neo4j) + LLM (Gemini-2.5-flash). sử dụng file `../README.md` để mô tả kiến trúc tổng thể, có thể viết thành bảng có giải thích, mô tả
    - quy trình xử lý câu hỏi từ user cho chatbot
  - Cách bạn thiết kế Cypher query để lấy context từ Neo4j dựa trên user_id + product_type.
  - giới thiệu và giải thích knowledge base (folder `knowledge_base/`) lưu trữ faq, guides, policies và vector store FAISS trong `vector_store/` (có thể trình bày dưới dạng bảng hoặc sơ đồ).
  - Cách bạn tích hợp context này vào prompt cho LLM.
  - Ví dụ cụ thể về một câu hỏi của user và cách chatbot trả lời dựa trên context từ Neo4j.

    - Bằng chứng trong báo cáo: sử dụng json response từ query của người dùng "Mình cần laptop văn phòng tầm 20 triệu, nên chọn gì?" ở file `assets/chat_response.json`
    - code xử lý request chatbot từ người dùng
    + ảnh graph, (ảnh graph: `assets/neo4j_graph.png`)
- **Chương 5**: Tích hợp AI Service vào hệ thống E-commerce:
    - gợi ý sản phẩm dựa trên lịch sử tương tác của người dùng với hệ thống (ảnh `assets/products_recommendation.png`)
    - tính năng chatbot AI: giới thiệu các thành phần giao diện tối ưu cho trải nghiệm người dùng e-commerce (ảnh `assets/chat_interface.png`), mô tả cách chatbot hỗ trợ người dùng trong quá trình mua sắm (ví dụ: trả lời câu hỏi về sản phẩm, hỗ trợ đặt hàng, v.v.)

## 2. Yêu cầu về  hình thức
- cỡ chữ chuẩn report Latex, template report, số trang tối thiểu 30 trang.
- không cần header, footer nhưng cần có số trang ở giữa dưới cùng, số trang bắt đầu từ chương 1 (không tính trang bìa và mục lục).
- sử dụng hình ảnh minh họa có trong thư mục `assets/` (đã được liệt kê ở trên) để làm rõ các phần trình bày, có chú thích cho từng hình ảnh.
- sử dụng bảng để trình bày các thông tin có cấu trúc (ví dụ: bảng liệt kê các trường dữ liệu, bảng so sánh kết quả giữa các mô hình, v.v.)
- ở trang bìa: tên báo cáo là "BÁO CÁO BÀI TẬP AI SERVICE 02", còn lại các thông tin khác y hệt ảnh `assets/report_cover_template.png` (bạn có thể dùng LaTeX template để tạo trang bìa này).
- tên file pdf: `aiservice02_08.04_minhdq.pdf`
## 3. Các file để agents tham khảo khi viết báo cáo
- `../README.md`: để lấy thông tin về tổng quan hệ thống, kiến trúc, công nghệ sử dụng, v.v.
- `../neo4j_import/data_user500.csv`: để phân tích và mô tả tập dữ liệu.
- `../docker-compose.yml`: để tham khảo về các services và ports.
- `../neo4j/cypher/import_interactions_500u.cypher`: để tham khảo về cách import dữ liệu vào Neo4j.
- `../neo4j_import/generate_fake_interactions.py`: để tham khảo về cách generate dữ liệu giả cho 500 user.
- folder `../interaction_service/`: interaction_service có thể cung cấp thêm thông tin về cách dữ liệu tương tác được ghi lại và cấu trúc của chúng.
- `chat/services.py`: để tham khảo về cách xử lý câu hỏi từ user cho chatbot, cách tích hợp context từ Neo4j vào prompt cho LLM, v.v.
- `ai_service_assignment.md`: để tham khảo về yêu cầu chi tiết của bài tập, cách xây dựng và đánh giá mô hình RNN/LSTM/biLSTM, cách xây dựng KB_Graph với Neo4j, cách xây dựng RAG và chat dựa trên KB_Graph, v.v.
- `notebooks/behavior_sequence_models.ipynb`: để tham khảo về code xây dựng và đánh giá các mô hình RNN/LSTM/biLSTM cho bài toán dự đoán hành vi kế tiếp của user.