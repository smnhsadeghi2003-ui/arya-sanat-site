from __future__ import annotations

import json
import re


from app.config import PRODUCTS_FILE, KNOWLEDGE_FILE

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    import math
    from collections import Counter


def normalize(text: str) -> str:
    text = str(text or "")
    for a, b in [("ي", "ی"), ("ك", "ک"), ("\u200c", " ")]:
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip().lower()


class ProductRAG:
    def __init__(self):
        path = PRODUCTS_FILE
        if not path.exists():
            # fallback
            alt = path.parent / "products_details.json"
            path = alt if alt.exists() else path
        self.products = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        self.knowledge = []
        if KNOWLEDGE_FILE.exists():
            self.knowledge = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))

        self.documents = [self._to_text(p) for p in self.products]
        self.matrix = None
        self.vectorizer = None

        if self.documents and HAS_SKLEARN:
            self.vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                min_df=1,
                sublinear_tf=True,
            )
            self.matrix = self.vectorizer.fit_transform(self.documents)
        elif self.documents:
            self._build_simple_index()

    def _to_text(self, p: dict) -> str:
        attrs = p.get("attributes") or p.get("technical_specs") or {}
        if isinstance(attrs, dict):
            attrs_t = " ".join(f"{k} {v}" for k, v in attrs.items())
        else:
            attrs_t = str(attrs)

        def lt(v):
            if isinstance(v, list):
                return " ".join(str(x) for x in v)
            return str(v or "")

        return normalize(
            " ".join(
                [
                    p.get("name", ""),
                    p.get("brand", ""),
                    p.get("sku", ""),
                    p.get("category", ""),
                    p.get("price", "") or p.get("price_text", ""),
                    p.get("short_description", ""),
                    p.get("description", ""),
                    lt(p.get("features")),
                    lt(p.get("advantages")),
                    lt(p.get("applications")),
                    attrs_t,
                    p.get("search_text", ""),
                ]
            )
        )

    def _build_simple_index(self):
        # pure python fallback
        self._tok_docs = []
        df: dict[str, int] = {}
        for doc in self.documents:
            toks = set(re.findall(r"[\w\u0600-\u06FF]{2,}", doc))
            self._tok_docs.append(Counter(re.findall(r"[\w\u0600-\u06FF]{2,}", doc)))
            for t in toks:
                df[t] = df.get(t, 0) + 1
        n = len(self.documents)
        self._idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.products:
            return []
        qn = normalize(query)
        if self.matrix is not None and self.vectorizer is not None:
            q = self.vectorizer.transform([qn])
            scores = cosine_similarity(q, self.matrix).ravel()
            order = scores.argsort()[::-1][:top_k]
            results = []
            for i in order:
                if scores[i] <= 0:
                    continue
                item = dict(self.products[i])
                item["_score"] = round(float(scores[i]), 4)
                results.append(item)
            return results

        # simple fallback
        q_toks = Counter(re.findall(r"[\w\u0600-\u06FF]{2,}", qn))
        scored = []
        for i, tf in enumerate(self._tok_docs):
            s = 0.0
            for t, c in q_toks.items():
                if t in tf:
                    s += (1 + math.log(tf[t])) * self._idf.get(t, 1) * c
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        results = []
        for s, i in scored[:top_k]:
            item = dict(self.products[i])
            item["_score"] = round(s, 4)
            results.append(item)
        return results

    def build_context(self, hits: list[dict]) -> str:
        blocks = []
        for p in hits:
            attrs = p.get("attributes") or p.get("technical_specs") or {}
            if isinstance(attrs, dict):
                attrs_text = " | ".join(f"{k}: {v}" for k, v in attrs.items())
            else:
                attrs_text = str(attrs or "")
            blocks.append(
                f"نام محصول: {p.get('name', '')}\n"
                f"برند: {p.get('brand', '')}\n"
                f"SKU: {p.get('sku', '')}\n"
                f"قیمت: {p.get('price', '') or p.get('price_text', '')}\n"
                f"دسته: {p.get('category', '')}\n"
                f"توضیحات: {(p.get('description') or p.get('short_description') or '')[:500]}\n"
                f"ویژگی‌ها: {' | '.join(str(x) for x in (p.get('features') or []))}\n"
                f"کاربرد: {' | '.join(str(x) for x in (p.get('applications') or []))}\n"
                f"مشخصات فنی: {attrs_text}\n"
                f"لینک: {p.get('url', '')}"
            )
        return "\n\n---\n\n".join(blocks)
