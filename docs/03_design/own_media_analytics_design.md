# Thiết Kế Chức Năng: Own Media Analytics & Self-Feedback Loop

**Phiên bản:** 1.0 (Đề xuất bởi CTO dựa trên yêu cầu của CMO)
**Người viết:** CTO
**Cập nhật:** 31/05/2026

## 1. Mục tiêu (Objectives)
Đóng vòng lặp tối ưu hóa (Optimization Loop) bằng cách đo lường hiệu suất thực tế và phân tích bình luận của **chính các bài viết hệ thống đã tự đăng (Own Media)**. Từ đó tự động rút ra "Winning Angle" và "Anti-pattern" để rèn giũa Agent Sáng tạo cho các chiến dịch tiếp theo.

## 2. Phân Tích Khả Năng API (Upload-Post API)
Dựa trên tài liệu `llm-upload-post.md`, chúng ta sẽ khai thác 2 API Endpoint cốt lõi:
1. **`GET /api/uploadposts/post-analytics`**: Lấy số liệu tương tác trực tiếp (Views, Likes, Comments) dựa trên `platform_post_id` gốc của mạng xã hội (tích hợp xuyên nền tảng).
2. **`GET /api/uploadposts/comments`**: (Chỉ dành cho Instagram/Facebook) Lấy nội dung text của từng comment dựa trên `platform_post_id`.

## 3. Kiến Trúc Lưu Trữ (Database Schema)
Hệ thống hiện tại đã có sẵn các bảng hoàn hảo để đáp ứng chức năng này mà KHÔNG cần tạo thêm bảng mới:
* **`PlatformVariant`**: Đã có sẵn cột `platform_post_id`, `metric_views`, `metric_likes`, `metric_shares`, `metric_comments`.
* **`SocialInteraction`**: Dùng để lưu trữ bình luận thô cào về (cột `content`, `sentiment`, `platform_user_id`).
* **`rag_chunks` (pgvector)**: Dùng để lưu trữ các bài học đã được LLM đúc kết lại dưới dạng Vector với nhãn `access_tags = ["self_feedback"]`.

## 4. Luồng Vận Hành (Celery Cron Workflow)
Hệ thống sử dụng mô hình Background Job (Celery Beat) chạy định kỳ mỗi đêm:

**Bước 1: Cập nhật Metrics (Tracking Job)**
* Quét bảng `PlatformVariant` lấy các bản ghi có `publish_status = 'published'` và `published_at` trong vòng 7 ngày qua.
* Gọi API `/api/uploadposts/post-analytics` lấy số liệu mới nhất.
* Cập nhật các cột `metric_views`, `metric_likes`... vào database phục vụ Dashboard của CMO.

**Bước 2: Thu thập Bình luận (Listening Job - Instagram First)**
* Lọc các bài đăng thuộc nền tảng `instagram`.
* Gọi API `/api/uploadposts/comments` để lấy list bình luận.
* Insert trực tiếp các bình luận mới vào bảng `SocialInteraction`.

**Bước 3: Tự động học (Self-Feedback LLM Job)**
* Khởi chạy **Feedback Agent** (một node LLM ngầm không cần UI). Agent này sẽ tổng hợp các comment mới nhất của 1 kịch bản.
* *Nhiệm vụ của Agent:* 
  - Phân tích Sentiment (Tích cực/Tiêu cực).
  - Trích xuất Pain-point (Tại sao user chê?).
  - Định dạng kết quả thành Markdown ảo: *"Bài học kịch bản: Video về tính năng X bị người dùng chê vì [lý do Y]. Cần tránh..."*
* Sử dụng `document_service.process_and_store_document()`: Biến đoạn Text ảo thành file .md đẩy lên MinIO và tự động băm vào RAG Database với tag `self_feedback`.

## 5. Ứng dụng vào LangGraph (Creative Node)
Tại Node viết bài (`creative.py`), khi sinh Prompt cho LLM Copywriter, hệ thống sẽ thực hiện truy vấn RAG (Similarity Search) với điều kiện `access_tags = ["self_feedback"]`.
- *Luật bắt buộc:* "Mày (Copywriter) phải đọc lịch sử vấp ngã ở dưới đây, tuyệt đối không lặp lại lỗi (Anti-pattern) mà người dùng đã chửi trước đó."

## 6. Lộ Trình Triển Khai (Action Plan cho Dev)
1. **Sprint 1 (Tracking):** Viết Celery Task cập nhật `metric_*` cho `PlatformVariant` bằng API `post-analytics`.
2. **Sprint 2 (Listening):** Kéo comment Instagram lưu vào `SocialInteraction`.
3. **Sprint 3 (Self-Learning):** Build **Feedback Agent** tổng hợp comment -> băm vào RAG. Tích hợp RAG context này vào prompt của Copywriter.
