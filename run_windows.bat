@echo off
chcp 65001 >nul
cd /d %~dp0

if not exist .venv (
  echo [1/4] ساخت محیط مجازی...
  python -m venv .venv
  if errorlevel 1 (
    echo Python پیدا نشد. از python.org نصب کن و Add to PATH را بزن.
    pause
    exit /b 1
  )
  call .venv\Scripts\activate
  echo [2/4] نصب پکیج‌ها...
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
  pip install -q -r requirements.txt
)

if not exist .env (
  copy .env.example .env >nul
  echo.
  echo ========================================
  echo فایل .env ساخته شد.
  echo کلید OpenAI را جایگزین YOUR_KEY_HERE کن
  echo بعد ذخیره کن و این پنجره را ببند و دوباره اجرا کن.
  echo ========================================
  notepad .env
  pause
  exit /b 0
)

echo [3/4] چک کلید...
python check_env.py
echo.
echo [4/4] اجرای سرور...
echo سایت: http://127.0.0.1:8000
echo.
uvicorn main:apps --reload --host 0.0.0.0 --port 8000
pause
