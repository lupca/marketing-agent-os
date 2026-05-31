# Thi?t K? Ch?c Nang: Market Intelligence & Tích H?p SerpApi

**Phiên b?n:** 1.0 (Draft)
**Ngu?i vi?t:** CTO
**C?p nh?t:** 31/05/2026

## 1. M?c tiêu (Objectives)
Nâng c?p Marketing Agent OS t? m?c d? "Tra c?u n?i b?" lên "Tình báo th? tru?ng". Ch?c nang m?i cho phép h? th?ng t? d?ng theo dõi, thu th?p và phân tích d? li?u t? Google/YouTube thông qua SerpApi, qua dó h? tr? d?i ngu Creative lên k?ch b?n dánh trúng "Search Intent" và "Pain-point" c?a khách hàng.

## 2. Các Gi?i H?n K? Thu?t & Gi?i Pháp (Technical Feasibility)
D?a trên yêu c?u c?a CMO và gi?i h?n c?a n?n t?ng API (SerpApi):

*   **Cào Transcript (K?ch b?n):** Kh? thi thông qua YouTube Transcript API ho?c các thu vi?n open-source h? tr? l?y ph? d?.
*   **Cào Bình lu?n (Sentiment Analysis):** Kh? thi. SerpApi cung c?p YouTube Comments API. Tuy nhiên, d? t?i uu chi phí (credits) và tránh "nhi?u" (spam), h? th?ng s? ch? l?y **Top 50 comments** có lu?ng tuong tác (likes/replies) cao nh?t t? các video top d?u.
*   **Ch?ng "Cá nhân hóa" (Clean Search):** S? d?ng tham s? location, hl, gl c?ng trong payload g?i SerpApi d? d?m b?o k?t qu? tr? v? là khách quan nh?t.

## 3. Ki?n Trúc Lu?ng D? Li?u (Data Flow Pipeline)

Ð? gi?i quy?t bài toán "Nhi?m d?c d? li?u rác" và "Bóc tách Creative Hook" c?a CMO, lu?ng cào d? li?u s? di qua m?t **B? l?c LLM (LLM Processing Pipeline)** tru?c khi dua vào RAG:

1.  **Data Extraction (Thu th?p):**
    *   G?i SerpApi l?y Top 10 Video.
    *   Cào Transcript + Top 50 Comments c?a t?ng video.
2.  **LLM Pre-processing (B? L?c Ch?t Lu?ng - Qwen2.5/Gemini):**
    *   **Garbage Filter:** LLM dánh giá Transcript. N?u là video rác, clickbait không có giá tr? chuy?n d?i -> B? qua.
    *   **Hook Extractor:** Phân tích 3-5 giây d?u c?a video d?t chu?n -> G?n tag [Hook_Type].
    *   **Sentiment Analyzer:** Phân tích Comments -> G?n tag [Pain_Point], [Customer_Objection].
3.  **Vectorization & Storage (Luu tr?):**
    *   D? li?u dã du?c "làm s?ch" và "dán nhãn" s? du?c bam (chunking) và nhúng (embedding) vào pgvector.
    *   Raw JSON du?c luu vào Data Lake (S3/MinIO) d? backup.

## 4. Tuong tác v?i D? N?i B? (Cross-Reference)
*(Ch? CMO xác nh?n lu?ng nghi?p v? c? th?. Có 2 hu?ng thi?t k?:)*
*   **Hu?ng 1 (Biz-First):** H? th?ng phân tích CPA/T?n kho n?i b? TRU?C. Ch? khi s?n ph?m d? di?u ki?n ch?y ads, Agent m?i ra ngoài cào trend d? tìm cách vi?t bài.
*   **Hu?ng 2 (Market-First):** T? d?ng cào Trend liên t?c. Khi phát hi?n m?t kho?ng tr?ng th? tru?ng (Gap), Agent s? quay v? h?i Database n?i b? xem "Chúng ta có s?n ph?m nào dáp ?ng trend này không, biên l?i nhu?n t?t không?".

## 5. K? Nang Tìm Ki?m (Search Playbook cho Agent)
C?u hình system prompt cho Intelligence Agent v?i các k? nang:
*   **Footprinting:** S? d?ng các toán t? site:, intitle:.
*   **Chain-of-Search:** Tìm ki?m r?ng -> L?c d?i th? l?n -> Ði sâu vào video viral.
*   **Cross-border Learning:** Ð?i location sang th? tru?ng qu?c t? (US, Trung Qu?c) d? d? doán trend s? v? Vi?t Nam.
