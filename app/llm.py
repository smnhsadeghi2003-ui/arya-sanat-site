import os

from dotenv import load_dotenv
from openai import OpenAI


# خواندن فایل .env
load_dotenv()


# گرفتن API Key از .env
api_key = os.getenv("OPENAI_API_KEY")

# گرفتن نام مدل از .env
model = os.getenv(
    "LLM_MODEL",
    "gpt-4o-mini"
)


# ساخت Client
client = None

if api_key:
    client = OpenAI(
        api_key=api_key
    )


def generate_llm_answer(
    user_message,
    context,
):

    # اگر API Key پیدا نشد
    if client is None:

        print("OPENAI_API_KEY پیدا نشد.")

        return None

    system_prompt = """
تو مشاور تخصصی ابزارهای صنعتی شرکت میکرون ابزار هستی.

قوانین بسیار مهم:

1. فقط بر اساس اطلاعات CONTEXT پاسخ بده.
2. هیچ محصول یا مشخصات فنی از خودت اختراع نکن.
3. اگر محصول مناسبی وجود ندارد، صادقانه بگو پیدا نشد.
4. اگر RAG محصولی را انتخاب نکرده، خودت محصول جدید پیشنهاد نده.
5. پاسخ فارسی، طبیعی و حرفه‌ای باشد.
6. پاسخ خیلی طولانی نباشد.
"""

    prompt = f"""
سؤال مشتری:

{user_message}


اطلاعات محصولات:

{context}


بر اساس اطلاعات بالا به مشتری پاسخ بده.
"""

    try:

        response = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=prompt,
        )

        return response.output_text.strip()

    except Exception as e:

        print(
            "LLM ERROR:",
            repr(e)
        )

        return None