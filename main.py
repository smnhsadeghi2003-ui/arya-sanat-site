from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.rag import ProductRAG
from app.consultant import build_advice
from app.llm import generate_llm_answer


# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


# =========================================================
# FastAPI
# =========================================================

apps = FastAPI(
    title="Micron Tools AI Consultant",
    version="1.4.0",
    description="RAG + LLM technical consultant for industrial tools",
)


# =========================================================
# CORS
# =========================================================

apps.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Static
# =========================================================

if STATIC_DIR.exists():

    apps.mount(
        "/static",
        StaticFiles(
            directory=str(STATIC_DIR)
        ),
        name="static",
    )


# =========================================================
# RAG
# =========================================================

rag = ProductRAG()


# =========================================================
# Request model
# =========================================================

class ChatRequest(BaseModel):

    message: str
    top_k: int = 5


# =========================================================
# Root
# =========================================================

@apps.get("/")
def root():

    return {
        "status": "ok",
        "message": "Micron Tools AI Consultant is running.",
        "docs": "/docs",
        "health": "/health",
    }


# =========================================================
# Health
# =========================================================

@apps.get("/health")
def health():

    return {
        "status": "ok",
        "products": len(rag.products),
    }


# =========================================================
# Search
# =========================================================

@apps.post("/search")
def search(req: ChatRequest):

    hits = rag.search(
        req.message,
        top_k=req.top_k,
    )

    return {
        "query": req.message,
        "results": hits,
    }


# =========================================================
# Chat
# =========================================================

@apps.post("/chat")
def chat(req: ChatRequest):

    # -----------------------------------------------------
    # 1. RAG retrieval
    # -----------------------------------------------------

    hits = rag.search(
        req.message,
        top_k=req.top_k,
    )

    # -----------------------------------------------------
    # 2. Build deterministic fallback
    # -----------------------------------------------------

    rag_answer = build_advice(
        req.message,
        hits,
    )

    # -----------------------------------------------------
    # 3. If no products were found
    #
    # Don't call LLM to invent products.
    # -----------------------------------------------------

    if not hits:

        return {
            "answer": rag_answer,
            "products": [],
            "products_found": 0,
            "source": "rag",
        }

    # -----------------------------------------------------
    # 4. Build context
    # -----------------------------------------------------

    context = rag.build_context(
        hits
    )

    # -----------------------------------------------------
    # 5. Ask LLM to explain ONLY the RAG results
    # -----------------------------------------------------

    llm_answer = generate_llm_answer(
        req.message,
        context,
    )

    # -----------------------------------------------------
    # 6. Fallback if LLM unavailable
    # -----------------------------------------------------

    if not llm_answer:

        return {
            "answer": rag_answer,
            "products": hits[:3],
            "products_found": len(hits),
            "source": "rag_fallback",
        }

    # -----------------------------------------------------
    # 7. Final answer
    # -----------------------------------------------------

    return {
        "answer": llm_answer,
        "products": hits[:3],
        "products_found": len(hits),
        "source": "rag+llm",
    }


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":

    uvicorn.run(
        "main:apps",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )