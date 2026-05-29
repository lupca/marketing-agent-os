# TMCP Database Design v2.1
## Marketing Hub & Dashboard — Complete Schema Redesign

> **Cập nhật**: 2026-02-15
> **Mục tiêu**: Thiết kế lại toàn bộ database phù hợp với hệ thống marketing automation có AI agent hỗ trợ.
> **Giai đoạn tập trung**: Thương hiệu, Khách hàng, Content, Campaigns.
> **Backend**: PocketBase (Go + SQLite)

Dưới đây là **Tài liệu Đặc tả Dữ liệu (Data Dictionary)** chi tiết cho toàn bộ cấu trúc cơ sở dữ liệu. Tài liệu này giải thích rõ ý nghĩa, mục đích và cách hệ thống (đặc biệt là các AI Agent và API) tương tác với từng trường dữ liệu.

---

### [TẦNG 1]: NỀN TẢNG CHIẾN LƯỢC (Master Data)

**1. Collection: `Workspace**`
Vách ngăn cấp cao nhất để quản lý Multi-tenant, đảm bảo dữ liệu của các tổ chức/team không bị lẫn lộn.

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính tự sinh (thường là chuỗi 15 ký tự nếu dùng backend như PocketBase). |
| **`name`** | `string` | Tên của không gian làm việc (VD: "Team Marketing Alpha", "Agency X"). |
| **`ownerId`** | `relation` | Link tới bảng `User`. Định danh người có quyền Admin cao nhất của Workspace này. |
| **`members`** | `relation[]` | Mảng các `User` được phép truy cập. Dùng để cấu hình API Rules chặn truy cập trái phép. |
| **`settings`** | `json` | Lưu các thiết lập chung (VD: múi giờ mặc định, hạn mức ngân sách, API key kết nối các nền tảng social). |

**2. Collection: `BrandIdentity**`
Kho lưu trữ "linh hồn" của thương hiệu. Nguồn tham chiếu bắt buộc để AI Agent giữ đúng văn phong.

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính. |
| **`workspaceId`** | `relation` | Ràng buộc bắt buộc. Brand này thuộc về Workspace nào. |
| **`brandName`** | `string` | Tên thương hiệu. |
| **`coreMessaging`** | `json` | Chứa Slogan, Tầm nhìn, Sứ mệnh, và Keywords. Nhóm lại thành JSON để API gọi 1 lần là lấy đủ text. |
| **`visualAssets`** | `json` | Chứa link Logo, mã màu Hex (Color Palette). Dùng cho Frontend render hoặc AI tạo ảnh tham chiếu. |
| **`voiceAndTone`** | `editor` | Giọng văn (VD: "Chuyên nghiệp, hài hước, không dùng tiếng lóng"). Dùng làm System Prompt cho AI Agent viết content. |
| **`dosAndDonts`** | `json` | Danh sách những từ/hành động "Nên làm" và "Tuyệt đối cấm kỵ". |
| **`contentPillars`** | `json` | Các trụ cột nội dung chính (VD: Đào tạo, Giải trí, Bán hàng). |
| **`createdAt`** | `timestamp` | Thời gian tạo mốc nhận diện này. |

**3. Collection: `CustomerPersona**`
Hồ sơ khách hàng mục tiêu để nhắm đích (Targeting).

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính. |
| **`workspaceId`** | `relation` | Liên kết vùng làm việc. |
| **`personaName`** | `string` | Tên gợi nhớ (VD: "CEO bận rộn", "Sinh viên IT"). |
| **`summary`** | `string` | Tóm tắt ngắn gọn 1-2 câu về tệp này. |
| **`demographics`** | `json` | Nhân khẩu học (Tuổi, Giới tính, Thu nhập, Vị trí địa lý). |
| **`psychographics`** | `json` | Tâm lý học. Quan trọng nhất là lưu `painPoints` (Nỗi đau) và `goals` (Mục tiêu) để AI phân tích concept. |

**4. Collection: `MediaAsset**`
Kho quản lý tài sản kỹ thuật số tập trung (DAM - Digital Asset Management).

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính. |
| **`workspaceId`** | `relation` | Liên kết vùng làm việc. |
| **`file`** | `file` | Link vật lý lưu trữ ảnh/video/tài liệu. |
| **`fileType`** | `string` | Phân loại `image`, `video`, `document` để Frontend render UI player tương ứng. |
| **`aspectRatio`** | `string` | Tỷ lệ (VD: 16:9, 9:16, 1:1). Giúp filter nhanh ảnh hợp với TikTok hay Facebook. |
| **`tags`** | `json` | Các từ khóa đánh dấu để tìm kiếm nhanh (VD: ["logo", "transparent", "tet2026"]). |

**5. Collection: `InspirationEvent**`
Dữ liệu kích hoạt ý tưởng (Lễ hội, Sự kiện).

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính. |
| **`workspaceId`** | `relation` | **Đặc biệt:** Có thể NULL. Nếu NULL, đây là sự kiện Global (Quốc tế Phụ nữ, Tết). Nếu có ID, đây là sự kiện nội bộ (Sinh nhật công ty). |
| **`eventName`** | `string` | Tên sự kiện (VD: "Black Friday 2026"). |
| **`eventDate`** | `date` | Ngày diễn ra. Backend sẽ chạy cronjob quét ngày này để báo nhắc nhở. |
| **`eventType`** | `select` | Phân loại: `holiday`, `trend`, `company_anniversary`. |
| **`description`** | `text` | Mô tả về sự kiện. |
| **`suggestedAngles`** | `json` | Gợi ý sẵn các góc nhìn content cho sự kiện này (VD: Góc tri ân, Góc khuyến mãi). |

---

### [TẦNG 2]: KHÔNG GIAN HOẠCH ĐỊNH (Planning)

**6. Collection: `Worksheet**`
Nơi giao thoa của các Master Data để bắt đầu lên ý tưởng chiến lược.

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính. |
| **`workspaceId`** | `relation` | Liên kết vùng làm việc. |
| **`title`** | `string` | Tên bảng làm việc. |
| **`brandRefs`** | `relation[]` | (Multiple) Kéo dữ liệu từ `BrandIdentity`. |
| **`customerRefs`** | `relation[]` | (Multiple) Kéo dữ liệu từ `CustomerPersona`. |
| **`eventRef`** | `relation` | Kéo dữ liệu từ `InspirationEvent` (nếu chiến dịch làm riêng cho một sự kiện). |
| **`status`** | `select` | `draft` (đang nháp), `analyzing` (AI đang xử lý), `approved_brief` (đã chốt thành Brief). |
| **`agentContext`** | `json` | Không gian nhớ (Memory) của AI. Lưu lại toàn bộ luồng suy luận, kết quả research thị trường, phân tích SWOT mà AI Agent trả về. |

---

### [TẦNG 3]: QUẢN LÝ THỰC THI (Execution)

**7. Collection: `MarketingCampaign**`
Chiến dịch chính thức được sinh ra sau khi chốt Worksheet.

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính. |
| **`workspaceId`** | `relation` | Liên kết vùng làm việc. |
| **`worksheetId`** | `relation` | Tham chiếu ngược về Worksheet gốc để kế thừa context. |
| **`name`** | `string` | Tên chiến dịch. |
| **`campaignType`** | `string` | Phân loại (VD: Awareness, Lead Generation). |
| **`status`** | `select` | Quản lý vòng đời thực thi: `draft`, `planning`, `active`, `completed`. |
| **`budget`** | `number` | Ngân sách tổng. |
| **`kpiTargets`** | `json` | Mục tiêu KPI (VD: {"leads": 500, "reach": 100000}). |
| **`startDate` / `endDate**` | `datetime` | Khung thời gian chạy chiến dịch. |

**8. Collection: `MasterContent**`
Thông điệp gốc, chưa bị giới hạn bởi các nền tảng mạng xã hội.

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính. |
| **`workspaceId`** | `relation` | Liên kết vùng làm việc. |
| **`campaignId`** | `relation` | Content này thuộc Campaign nào. |
| **`coreMessage`** | `editor` | Nội dung thông điệp cốt lõi dạng Rich Text (HTML/Markdown). |
| **`primaryMediaIds`** | `relation[]` | Link tới ảnh/video chủ đạo trong kho `MediaAsset`. |
| **`approvalStatus`** | `select` | Workflow duyệt bài: `draft`, `reviewing`, `approved`. Trạng thái `approved` là Trigger để AI tự động đẻ ra các Platform Variant. |

**9. Collection: `AgentLog**`
Bảng giám sát sức khỏe và hoạt động của hệ thống AI (Observability).

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính. |
| **`workspaceId`** | `relation` | Liên kết vùng làm việc. |
| **`agentName`** | `string` | Tên Agent thực thi (VD: `PlannerAgent`, `CopywriterAgent`). |
| **`action`** | `string` | Hành động vừa làm (VD: "Generate TikTok Script"). |
| **`status`** | `select` | `success`, `failed`, `running`. Dễ dàng check xem AI có bị treo không. |
| **`tokensUsed`** | `number` | Số lượng Token đã tiêu thụ (dùng để tính cost/billing sau này). |
| **`targetCollection`** | `string` | Tên bảng bị tác động (VD: "PlatformVariant"). |
| **`targetRecordId`** | `string` | ID cụ thể của dòng dữ liệu vừa được AI tạo/sửa. Giúp trace ngược dễ dàng. |
| **`errorMessage`** | `text` | Lưu lại lỗi (VD: "Ollama timeout" hoặc "Rate limit LLM"). |

---

### [TẦNG 4]: ĐIỂM CHẠM VẬT LÝ (Deliverables)

**10. Collection: `PlatformVariant**`
Bản đăng cuối cùng bắn ra ngoài mạng xã hội.

| Tên Field | Kiểu dữ liệu | Giải thích & Mục đích sử dụng |
| --- | --- | --- |
| **`id`** | `string (PK)` | Khóa chính. |
| **`workspaceId`** | `relation` | Liên kết vùng làm việc. |
| **`masterContentId`** | `relation` | Kế thừa từ Master Content nào. |
| **`platform`** | `select` | Chọn kênh: `facebook`, `tiktok`, `linkedin`, `instagram`. |
| **`adaptedCopy`** | `text` | Nội dung chữ đã được AI "xào nấu" lại (thêm icon, cắt ngắn, đổi format) cho chuẩn kênh. |
| **`platformMediaIds`** | `relation[]` | Ảnh/video CỤ THỂ dùng cho kênh này (VD: Bản TikTok chỉ lấy video 9:16). |
| **`publishStatus`** | `select` | Trạng thái đăng bài: `draft`, `scheduled`, `publishing`, `published`, `failed`. |
| **`scheduledAt`** | `datetime` | Thời gian lên lịch hẹn giờ đăng. |
| **`publishedAt`** | `datetime` | Thời gian thực tế API báo đăng thành công. |
| **`platformPostId`** | `string` | ID của bài đăng do Meta/TikTok trả về. Rất quan trọng để kéo webhook update tương tác. |
| **`platformPostUrl`** | `url` | Link trực tiếp xem bài viết trên mạng xã hội. |
| **`metadata`** | `json` | "Thùng rác ngăn nắp" chứa các râu ria: `hashtags`, `seoKeywords`, `aiPrompt` đã dùng, `errorLogs` (nếu đăng xịt). |
| **`metricViews`** | `number` | Số lượt xem (Lưu dạng vật lý để query/sort siêu tốc). |
| **`metricLikes`** | `number` | Số lượt thích. |
| **`metricShares`** | `number` | Số lượt chia sẻ. |
| **`metricComments`** | `number` | Số lượt bình luận. |

---

Bản mô tả này đã bao quát đầy đủ logic vận hành từ lúc lên ý tưởng tới khi phân phối và đo lường.

Để bước tiếp theo vào thực tế, bạn có muốn mình chuyển đổi schema này thành các class **Pydantic Model (cho FastAPI)** hoặc xuất dưới dạng **JSON Export để import thẳng vào PocketBase** không? Hệ thống sẽ tạo sẵn toàn bộ các collection và quan hệ này chỉ bằng 1 thao tác.