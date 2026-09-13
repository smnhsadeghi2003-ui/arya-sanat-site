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


from app.config import (GROQ_API_KEY, LLM_MODEL,
                 OLLAMA_MODEL,
                 OLLAMA_URL,
                 OPENAI_API_KEY,
                 USE_OLLAMA,
                 XAI_API_KEY, )

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"

apps = FastAPI(title="Arya Sanat AI Consultant", version="1.1.0")
apps.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = ProductRAG()

if STATIC.exists():
    apps.mount("static", StaticFiles(directory=str(STATIC)), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)


def call_ollama(message: str, context: str) -> str | None:
    if not USE_OLLAMA:
        return None
    prompt = f"""تو مشاور فروش آریا صنعت هستی.
قوانین:
1) فارسی ساده و کوتاه بنویس (حداکثر ۸ خط).
2) فقط از Context استفاده کن؛ چیزی اختراع نکن.
3) اگر سلام کرد، گرم جواب بده و بپرس چطور کمک کنی.
4) اگر تماس/آدرس خواست، دقیق بده: تلفن 021-66722504 واتساپ 09194654017 آدرس تهران خیابان امام خمینی پلاک ۲۹.
5) برای محصول: نام، برند، یک جمله توضیح، لینک، بعد بگو برای قیمت تماس بگیرند.
6) لیست بلند و گیج‌کننده ننویس.

سؤال کاربر:
{message}

Context:
{context}
"""
    """


سؤال کاربر:
{message}

Context:
{context}
"""
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return (r.json().get("response") or "").strip()
    except Exception:
        return None


def call_cloud_llm(message: str, context: str) -> str | None:
    api_key = OPENAI_API_KEY or GROQ_API_KEY or XAI_API_KEY
    if not api_key:
        return None
    base_url = "https://api.openai.com/v1"
    model = LLM_MODEL or "gpt-4o-mini"
    if GROQ_API_KEY and not OPENAI_API_KEY:
        base_url = "https://api.groq.com/openai/v1"
        model = LLM_MODEL or "llama-3.3-70b-versatile"
    if XAI_API_KEY and not OPENAI_API_KEY and not GROQ_API_KEY:
        base_url = "https://api.x.ai/v1"
        model = LLM_MODEL or "grok-2-latest"
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        {
                                 "تو مشاور فروش آریا صنعت هستی. فارسی خیلی ساده و کوتاه. "
                                "اگر سلام بود گرم جواب بده. اگر تماس بود: 021-66722504 و واتساپ 09194654017 "
                                "و آدرس تهران امام خمینی پلاک ۲۹. "
                                "برای محصول حداکثر ۳ گزینه با نام و لینک. گیج‌کننده ننویس. فقط از Context."

                        },
                    ),
                },
                {
                    "role": "user",
                    "content": f"سؤال: {message}\n\nContext:\n{context}",
                },
            ],
            temperature=0.3,
            max_tokens=900,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return None


@apps.get("/")
def home():
    index = STATIC / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "API آماده است", "docs": "/docs"}


@apps.get("/health")
def health():
    from app.config import llm_status
    st = llm_status()
    return {
        "status": "ok",
        "products": len(rag.products),
        "sklearn": rag.matrix is not None,
        "version": "1.1.1",
        **st,
    }


@apps.get("/search")
def search(q: str, top_k: int = 5):
    hits = rag.search(q, top_k=top_k)
    return {"query": q, "results": hits}


@apps.post("/chat")
def chat(req: ChatRequest):
    hits = rag.search(req.message, top_k=req.top_k)
    context = rag.build_context(hits)

    answer = call_ollama(req.message, context) or call_cloud_llm(req.message, context)
    source = "llm" if answer else "rag"
    if not answer:
        answer = build_advice(req.message, hits)

    products = [
        {
            "name": h.get("name"),
            "brand": h.get("brand"),
            "price": h.get("price") or h.get("price_text"),
            "url": h.get("url"),
            "image": h.get("image"),
            "score": h.get("_score"),
        }
        for h in hits
    ]
    return {
        "answer": answer,
        "products": products,
        "products_found": len(products),
        "source": source,
    }
