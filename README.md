# Worker Profile Form MVP v0.2

Luồng chính:

**link công khai nhập hồ sơ → lưu dữ liệu → ánh xạ Việt → Hoa → link quản lý bí mật → xem/xóa hồ sơ → xuất DOCX theo mẫu gốc**.

## Thay đổi ở v0.2

- Bỏ **Tôn giáo** và **Ngoại ngữ** khỏi form. Hai phần này được giữ nguyên theo `base_template.docx`.
- Nghề nghiệp gia đình chỉ chọn 3 loại: **Nông nghiệp / Công nghiệp / Khác**.
  - Nông nghiệp xuất theo mẫu: `农夫 Nông Dân`.
  - Công nghiệp: `工人 Công Nhân`.
  - Khác: người dùng nhập tiếng Việt; hệ thống lấy bản Hoa từ từ điển nếu đã có.
- Có nút **Xóa hồ sơ** ở danh sách và trang chi tiết, kèm xác nhận trước khi xóa.
- Word exporter tách run Hoa/Việt, luôn có khoảng trắng giữa hai phần và ép phần Việt/Latin sang **Times New Roman**.
- Ảnh mới được lưu trong database dưới dạng data URI, phù hợp với cloud server không có ổ đĩa bền vững.
- Hỗ trợ PostgreSQL qua `DATABASE_URL`.
- Có `render.yaml` để deploy web + PostgreSQL lên Render.
- Đã dùng cú pháp `TemplateResponse` mới để tương thích FastAPI/Starlette hiện tại.

## Chạy local trên Windows

Mở PowerShell tại thư mục dự án:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run_local.ps1
```

Mặc định:

- Form: `http://127.0.0.1:8000/`
- Quản lý: `http://127.0.0.1:8000/manage/local-manager-demo-change-this`

## Từ điển dịch

Trang quản lý từ điển:

`/manage/<MANAGER_KEY>/dictionary`

Nhóm dữ liệu:

- `province`: tỉnh/quê quán
- `job`: nghề nghiệp
- `country`: quốc gia
- `work_description`: nội dung công việc
- `education`: học lực
- `religion`: tôn giáo cố định của mẫu
- `marital_status`: tình trạng hôn nhân
- `name_token`: từng từ trong tên người

Giá trị chưa có trong từ điển sẽ **không được hệ thống tự đoán**. Phần Hoa để trống/`//` cho tới khi người quản lý bổ sung bản dịch.

## Dữ liệu

### Local

- SQLite: `data/profiles.db`
- Word mẫu: `app/word/base_template.docx`
- Word xuất được tạo tạm trong `exports/` rồi xóa khỏi server sau khi gửi cho trình duyệt.

### Production

`render.yaml` cấu hình:

- Web service FastAPI chạy liên tục trên compute trả phí tối thiểu.
- PostgreSQL quản lý dữ liệu lâu dài.
- `MANAGER_KEY` được sinh tự động và phải được giữ bí mật.
- Ảnh nằm trong PostgreSQL nên không bị mất khi web service redeploy.

## Deploy lên Internet bằng Render

1. Đưa thư mục này lên một Git repository.
2. Trong Render, tạo **Blueprint** từ repository đó.
3. Render đọc `render.yaml` và tạo web service + PostgreSQL.
4. Sau khi deploy, lấy `MANAGER_KEY` trong Environment của web service.
5. Link nhập là URL gốc của service.
6. Link quản lý là `https://<ten-service>/manage/<MANAGER_KEY>`.

> Không chia sẻ link quản lý cho người nhập form. Ai giữ link này có thể xem, xuất Word, sửa từ điển và xóa hồ sơ.

## Lưu ý Word

- Phần tôn giáo và ngoại ngữ được copy nguyên trạng từ mẫu.
- Tiếng Việt/Latin động dùng Times New Roman.
- Tiếng Hoa giữ font East Asian của template để tránh lỗi glyph.
- Các ô song ngữ dùng run riêng nên có khoảng cách đúng, ví dụ `农夫 Nông Dân`.
