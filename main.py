from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.rag import ProductRAG
from app.consultant import build_advice


# =========================================================
# FastAPI
# =========================================================

apps = FastAPI(
    title="Micron Tools AI Consultant",
    version="1.3.0",
    description="AI Technical Consultant for Micron Tools",
)


# =========================================================
# CORS
# =========================================================

apps.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"


# =========================================================
# Static Files
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
# Request Model
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
        "name": "Micron Tools AI Consultant",
        "version": "1.3.0",
        "status": "running",
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

@apps.get("/search")
def search(
    q: str,
    top_k: int = 5,
):

    hits = rag.search(
        q,
        top_k=top_k,
    )

    products = []

    for hit in hits:

        products.append({
            "name": hit.get(
                "name",
                ""
            ),

            "brand": hit.get(
                "brand",
                ""
            ),

            "sku": hit.get(
                "sku",
                ""
            ),

            "category": hit.get(
                "category",
                ""
            ),

            "price": hit.get(
                "price",
                ""
            ),

            "description": hit.get(
                "description",
                ""
            ),

            "url": hit.get(
                "url",
                ""
            ),

            "image": hit.get(
                "image",
                ""
            ),

            "score": hit.get(
                "_score",
                0
            ),

            "intent": hit.get(
                "_intent",
                "general"
            ),

            "diameter": hit.get(
                "_diameter",
                None
            ),
        })

    return {
        "query": q,
        "results": products,
        "count": len(products),
    }


# =========================================================
# Chat
# =========================================================

@apps.post("/chat")
def chat(
    req: ChatRequest,
):

    # -----------------------------------------------------
    # Search products
    # -----------------------------------------------------

    hits = rag.search(
        req.message,
        top_k=req.top_k,
    )

    # -----------------------------------------------------
    # Build consultant answer
    # -----------------------------------------------------

    answer = build_advice(
        req.message,
        hits,
    )

    # -----------------------------------------------------
    # Prepare products
    # -----------------------------------------------------

    products = []

    for hit in hits:

        products.append({
            "name": hit.get(
                "name",
                ""
            ),

            "brand": hit.get(
                "brand",
                ""
            ),

            "sku": hit.get(
                "sku",
                ""
            ),

            "category": hit.get(
                "category",
                ""
            ),

            "price": hit.get(
                "price",
                ""
            ),

            "description": hit.get(
                "description",
                ""
            ),

            "url": hit.get(
                "url",
                ""
            ),

            "image": hit.get(
                "image",
                ""
            ),

            "score": hit.get(
                "_score",
                0
            ),

            "intent": hit.get(
                "_intent",
                "general"
            ),

            "diameter": hit.get(
                "_diameter",
                None
            ),
        })

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "answer": answer,

        "products": products,

        "products_found": len(products),

        "source": "rag",
    }


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:apps",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )