from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PRODUCTS_FILE = DATA_DIR / "products_full.json"
KNOWLEDGE_FILE = DATA_DIR / "site_knowledge.json"
ENV_FILE = BASE_DIR / ".env"

# ۱) dotenv
try:
    from dotenv import load_dotenv
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    # ۲) خواندن دستی .env اگر python-dotenv نصب نبود
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def _get(name: str) -> str:
    return (os.getenv(name) or "").strip().strip('"').strip("'")


USE_OLLAMA = _get("USE_OLLAMA") in ("1", "true", "True", "yes")
OLLAMA_MODEL = _get("OLLAMA_MODEL") or "qwen2.5:7b"
OLLAMA_URL = _get("OLLAMA_URL") or "http://localhost:11434/api/generate"

OPENAI_API_KEY = _get("OPENAI_API_KEY")
GROQ_API_KEY = _get("GROQ_API_KEY")
XAI_API_KEY = _get("XAI_API_KEY")
LLM_MODEL = _get("LLM_MODEL")
OPENAI_BASE_URL = _get("OPENAI_BASE_URL")

# تشخیص وضعیت برای /health (بدون لو دادن کلید)
def llm_status() -> dict:
    key = OPENAI_API_KEY or GROQ_API_KEY or XAI_API_KEY
    provider = None
    if OPENAI_API_KEY:
        provider = "openai"
    elif GROQ_API_KEY:
        provider = "groq"
    elif XAI_API_KEY:
        provider = "xai"
    return {
        "cloud_llm": bool(key),
        "provider": provider,
        "key_prefix": (key[:7] + "...") if key and len(key) > 10 else (key[:3] + "..." if key else None),
        "env_file_exists": ENV_FILE.exists(),
        "model": LLM_MODEL or None,
        "ollama": USE_OLLAMA,
    }
