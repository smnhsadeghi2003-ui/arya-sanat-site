from __future__ import annotations

from pathlib import Path

import requests

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.consultant import build_advice
from app.rag import ProductRAG

from app.config import (
    GROQ_API_KEY,
    LLM_MODEL,
    OLLAMA_MODEL,
    OLLAMA_URL,
    OPENAI_API_KEY,
    USE_OLLAMA,
    XAI_API_KEY,
)


# =========================================================
# PATHS
# =========================================================

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"


# =========================================================
# FASTAPI
# =========================================================

apps = FastAPI(
    title="Arya Sanat AI Consultant",
    version="1.2.0",
)


apps.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# RAG
# =========================================================

rag = ProductRAG()


# =========================================================
# STATIC FILES
# =========================================================

if STATIC.exists():

    apps.mount(
        "/static",
        StaticFiles(
            directory=str(STATIC)
        ),
        name="static",
    )


# =========================================================
# REQUEST MODEL
# =========================================================

class ChatRequest(BaseModel):

    message: str = Field(
        min_length=1
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )


# =========================================================
# OLLAMA
# =========================================================

def call_ollama(
    message: str,
    context: str,
) -> str | None:

    if not USE_OLLAMA:
        return None

    prompt = f"""
تو مشاور فروش و فنی آریا صنعت هستی.

قوانین بسیار مهم:

1. فقط از اطلاعات Context استفاده کن.
2. هیچ محصولی که در Context نیست اختراع نکن.
3. اگر سؤال درباره یک عملیات مشخص مثل سوراخکاری است،
   فقط محصولات مناسب همان عملیات را پیشنهاد بده.
4. قلاویز برای سوراخکاری پیشنهاد نده.
5. مته مرغک را برای سوراخکاری اصلی پیشنهاد نده،
   مگر اینکه کاربر مشخصاً مته مرغک بخواهد.
6. اگر محصول مناسب در Context وجود ندارد،
   صادقانه بگو محصول مناسب پیدا نشد.
7. حداکثر 3 محصول معرفی کن.
8. پاسخ فارسی، ساده و کوتاه باشد.
9. برای هر محصول نام، برند، توضیح کوتاه و لینک را بده.
10. اگر اطلاعات فنی کافی نیست، سؤال تکمیلی بپرس.

سؤال کاربر:

{message}

Context:

{context}
"""

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()

        return (
            response
            .json()
            .get("response")
            or ""
        ).strip()

    except Exception:

        return None


# =========================================================
# CLOUD LLM
# =========================================================

def call_cloud_llm(
    message: str,
    context: str,
) -> str | None:

    api_key = (
        OPENAI_API_KEY
        or GROQ_API_KEY
        or XAI_API_KEY
    )

    if not api_key:
        return None

    base_url = (
        "https://api.openai.com/v1"
    )

    model = (
        LLM_MODEL
        or "gpt-4o-mini"
    )

    # GROQ
    if (
        GROQ_API_KEY
        and not OPENAI_API_KEY
    ):

        base_url = (
            "https://api.groq.com/openai/v1"
        )

        model = (
            LLM_MODEL
            or "llama-3.3-70b-versatile"
        )

    # XAI
    if (
        XAI_API_KEY
        and not OPENAI_API_KEY
        and not GROQ_API_KEY
    ):

        base_url = (
            "https://api.x.ai/v1"
        )

        model = (
            LLM_MODEL
            or "grok-2-latest"
        )

    try:

        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        system_prompt = """
تو مشاور فروش و فنی آریا صنعت هستی.

قوانین:

- فقط از Context استفاده کن.
- محصولی خارج از Context پیشنهاد نده.
- نوع عملیات کاربر را جدی بگیر.
- برای سوراخکاری، قلاویز پیشنهاد نده.
- برای قلاویزکاری، مته معمولی پیشنهاد نده.
- مته مرغک را فقط برای عملیات مربوط به مرغک پیشنهاد بده.
- اگر محصول مناسب وجود ندارد، بگو پیدا نشد.
- حداکثر 3 محصول پیشنهاد بده.
- فارسی ساده و حرفه‌ای بنویس.
"""

        response = client.chat.completions.create(

            model=model,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": (
                        f"سؤال کاربر:\n"
                        f"{message}\n\n"
                        f"اطلاعات محصولات:\n"
                        f"{context}"
                    ),
                },
            ],

            temperature=0.2,

            max_tokens=900,
        )

        return (
            response
            .choices[0]
            .message
            .content
            or ""
        ).strip()

    except Exception:

        return None


# =========================================================
# HOME
# =========================================================

@apps.get("/")
def home():

    index = STATIC / "index.html"

    if index.exists():

        return FileResponse(index)

    return {
        "message": "API آماده است",
        "docs": "/docs",
    }


# =========================================================
# HEALTH
# =========================================================

@apps.get("/health")
def health():

    from app.config import llm_status

    status = llm_status()

    return {
        "status": "ok",
        "products": len(
            rag.products
        ),
        "sklearn": (
            rag.matrix is not None
        ),
        "version": "1.2.0",
        **status,
    }


# =========================================================
# SEARCH
# =========================================================

@apps.get("/search")
def search(
    q: str,
    top_k: int = 5,
):

    hits = rag.search(
        q,
        top_k=top_k,
    )

    return {
        "query": q,
        "results": hits,
    }


# =========================================================
# CHAT
# =========================================================

@apps.post("/chat")
def chat(
    req: ChatRequest,
):

    # -----------------------------------------------------
    # STEP 1
    # پیدا کردن محصولات مرتبط
    # -----------------------------------------------------

    hits = rag.search(
        req.message,
        top_k=req.top_k,
    )


    # -----------------------------------------------------
    # STEP 2
    # پاسخ اصلی
    #
    # فعلاً مستقیم از build_advice استفاده می‌کنیم.
    # این کار برای تست RAG است.
    # -----------------------------------------------------

    answer = build_advice(
        req.message,
        hits,
    )

    source = "rag"


    # -----------------------------------------------------
    # STEP 3
    # محصولات خروجی
    # -----------------------------------------------------

    products = []

    for h in hits:

        products.append(
            {
                "name": h.get(
                    "name"
                ),

                "brand": h.get(
                    "brand"
                ),

                "price": (
                    h.get("price")
                    or h.get("price_text")
                ),

                "url": h.get(
                    "url"
                ),

                "image": h.get(
                    "image"
                ),

                "score": h.get(
                    "_score"
                ),

                "intent": h.get(
                    "_intent"
                ),
            }
        )


    # -----------------------------------------------------
    # STEP 4
    # RESPONSE
    # -----------------------------------------------------

    return {

        "answer": answer,

        "products": products,

        "products_found": len(
            products
        ),

        "source": source,
    }