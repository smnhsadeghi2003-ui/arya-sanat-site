# سایت مشاور هوشمند آریا صنعت

## نصب سریع (ویندوز)

1. پوشه را باز کن
2. روی `run_windows.bat` دوبار کلیک کن
3. اگر `.env` باز شد، کلید OpenAI را جایگزین `sk-proj-xxxxxxxx` کن و ذخیره کن
4. دوباره `run_windows.bat` را اجرا کن
5. برو به: **http://127.0.0.1:8000/**

## تنظیم کلید API

فایل `.env` را ویرایش کن:

```env
OPENAI_API_KEY=sk-proj-کلید-جدید-تو
LLM_MODEL=gpt-4o-mini
```

> کلید را در چت یا گیت‌هاب نگذار. اگر قبلاً لو رفته، از پنل OpenAI آن را Revoke کن و کلید جدید بساز.

## اجرا دستی

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# فایل .env را بساز و کلید را بگذار
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## آدرس‌ها

| آدرس | کاربرد |
|------|--------|
| http://127.0.0.1:8000/ | سایت چت |
| http://127.0.0.1:8000/docs | API |
| http://127.0.0.1:8000/health | وضعیت (باید cloud_llm: true باشد) |


## اتصال به وردپرس

فایل‌ها در پوشه :
-  — ویجت شناور چت
-  — راهنمای نصب

خلاصه: API را آنلاین کن، بعد در فوتر وردپرس:

```html
<script>window.ARYA_CHAT_API = "https://YOUR-API-DOMAIN";</script>
<script src="https://YOUR-API-DOMAIN/static/arya-chat-widget.js"></script>
```
