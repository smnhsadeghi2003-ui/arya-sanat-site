"""چک کردن اینکه کلید API درست خوانده می‌شود یا نه"""
from pathlib import Path
print("پوشه فعلی:", Path(".").resolve())
env = Path(".env")
print(".env وجود دارد؟", env.exists())
if env.exists():
    print("--- محتوای .env (کلید سانسور شده) ---")
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        if "KEY" in line.upper() and "=" in line:
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            print(f"{k.strip()} = {v[:8]}...{v[-4:] if len(v)>12 else ''}  (طول={len(v)})")
        else:
            print(line)
print("---")
from app.config import OPENAI_API_KEY, GROQ_API_KEY, llm_status
print("وضعیت:", llm_status())
if not (OPENAI_API_KEY or GROQ_API_KEY):
    print("\nمشکل: کلید خالی است.")
    print("در فایل .env باید دقیقاً این شکل باشد (بدون فاصله اضافه):")
    print("OPENAI_API_KEY=sk-proj-xxxxx")
else:
    print("\nکلید خوانده شد. سرور را ری‌استارت کن.")
