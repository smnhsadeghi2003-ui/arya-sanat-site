from __future__ import annotations

import json
import re
from collections import Counter

from app.config import PRODUCTS_FILE, KNOWLEDGE_FILE

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    import math


# ---------------------------------------------------------
# Normalize
# ---------------------------------------------------------

def normalize(text: str) -> str:
    text = str(text or "")

    replacements = [
        ("ي", "ی"),
        ("ك", "ک"),
        ("\u200c", " "),
        ("ۀ", "ه"),
        ("ة", "ه"),
    ]

    for a, b in replacements:
        text = text.replace(a, b)

    text = text.lower()

    # تبدیل اعداد فارسی و عربی به انگلیسی
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"

    for p, e in zip(persian_digits, english_digits):
        text = text.replace(p, e)

    for p, e in zip(arabic_digits, english_digits):
        text = text.replace(p, e)

    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------
# Technical intent detection
# ---------------------------------------------------------

INTENT_KEYWORDS = {
    "drilling": [
        "سوراخ",
        "سوراخکاری",
        "سوراخ کاری",
        "مته",
        "دریل",
        "حفاری",
        "ایجاد سوراخ",
        "hole",
        "drilling",
        "drill",
    ],

    "tapping": [
        "قلاویز",
        "قلاویزکاری",
        "رزوه داخلی",
        "رزوه زنی",
        "رزوه‌زنی",
        "tapping",
        "tap",
    ],

    "turning": [
        "تراشکاری",
        "تراش",
        "turning",
        "lathe",
    ],

    "milling": [
        "فرزکاری",
        "فرز",
        "milling",
        "mill",
    ],

    "threading": [
        "رزوه",
        "رزوه زنی",
        "رزوه‌زنی",
        "threading",
        "thread",
    ],

    "center_drilling": [
        "مته مرغک",
        "مرغک",
        "center drill",
        "center drilling",
    ],
}


# ---------------------------------------------------------
# Product intent mapping
# ---------------------------------------------------------

INTENT_PRODUCT_KEYWORDS = {

    "drilling": [
        "مته",
        "مته گرد",
        "مته کبالت",
        "مته hss",
        "drill",
        "drilling",
        "سوراخکاری",
    ],

    "tapping": [
        "قلاویز",
        "tap",
        "tapping",
    ],

    "turning": [
        "الماس تراش",
        "الماس",
        "تراش",
        "رنده",
        "turning",
    ],

    "milling": [
        "فرز",
        "فرز انگشتی",
        "milling",
        "end mill",
    ],

    "threading": [
        "قلاویز",
        "حدیده",
        "رزوه",
        "thread",
    ],

    "center_drilling": [
        "مته مرغک",
        "مرغک",
        "center drill",
    ],
}


def detect_intent(query: str) -> str | None:
    """
    تشخیص عملیات اصلی از سؤال کاربر.
    """

    q = normalize(query)

    scores = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            keyword_n = normalize(keyword)

            if keyword_n in q:
                score += 1

        if score > 0:
            scores[intent] = score

    if not scores:
        return None

    return max(scores, key=scores.get)


def product_matches_intent(product: dict, intent: str) -> bool:
    """
    بررسی می‌کند محصول با عملیات موردنظر سازگار است یا نه.
    """

    if not intent:
        return True

    product_text = normalize(
        " ".join(
            [
                str(product.get("name", "")),
                str(product.get("category", "")),
                str(product.get("description", "")),
                str(product.get("short_description", "")),
                str(product.get("features", "")),
                str(product.get("applications", "")),
                str(product.get("search_text", "")),
            ]
        )
    )

    keywords = INTENT_PRODUCT_KEYWORDS.get(intent, [])

    for keyword in keywords:
        if normalize(keyword) in product_text:
            return True

    return False


# ---------------------------------------------------------
# Product RAG
# ---------------------------------------------------------

class ProductRAG:

    def __init__(self):

        path = PRODUCTS_FILE

        if not path.exists():

            alt = path.parent / "products_details.json"

            path = alt if alt.exists() else path

        self.products = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.exists()
            else []
        )

        self.knowledge = []

        if KNOWLEDGE_FILE.exists():

            self.knowledge = json.loads(
                KNOWLEDGE_FILE.read_text(
                    encoding="utf-8"
                )
            )

        self.documents = [
            self._to_text(p)
            for p in self.products
        ]

        self.matrix = None
        self.vectorizer = None

        if self.documents and HAS_SKLEARN:

            self.vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                min_df=1,
                sublinear_tf=True,
            )

            self.matrix = self.vectorizer.fit_transform(
                self.documents
            )

        elif self.documents:

            self._build_simple_index()


    # -----------------------------------------------------
    # Convert product to searchable text
    # -----------------------------------------------------

    def _to_text(self, p: dict) -> str:

        attrs = (
            p.get("attributes")
            or p.get("technical_specs")
            or {}
        )

        if isinstance(attrs, dict):

            attrs_t = " ".join(
                f"{k} {v}"
                for k, v in attrs.items()
            )

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
                    p.get("price", "")
                    or p.get("price_text", ""),
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


    # -----------------------------------------------------
    # Simple fallback index
    # -----------------------------------------------------

    def _build_simple_index(self):

        self._tok_docs = []

        df = {}

        for doc in self.documents:

            tokens = set(
                re.findall(
                    r"[\w\u0600-\u06FF]{2,}",
                    doc
                )
            )

            self._tok_docs.append(
                Counter(
                    re.findall(
                        r"[\w\u0600-\u06FF]{2,}",
                        doc
                    )
                )
            )

            for token in tokens:

                df[token] = (
                    df.get(token, 0) + 1
                )

        n = len(self.documents)

        self._idf = {
            token:
            math.log(
                (1 + n) / (1 + count)
            ) + 1

            for token, count in df.items()
        }


    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> list[dict]:

        if not self.products:
            return []

        qn = normalize(query)

        # ---------------------------------------------
        # Detect technical intent
        # ---------------------------------------------

        intent = detect_intent(qn)

        # ---------------------------------------------
        # Candidate products
        # ---------------------------------------------

        candidates = []

        for index, product in enumerate(self.products):

            if product_matches_intent(
                product,
                intent
            ):
                candidates.append(index)

        # اگر intent تشخیص داده شد ولی هیچ محصولی
        # پیدا نشد، جستجوی معمولی را انجام بده
        if intent and not candidates:

            candidates = list(
                range(len(self.products))
            )

        # ---------------------------------------------
        # TF-IDF search
        # ---------------------------------------------

        if (
            self.matrix is not None
            and self.vectorizer is not None
        ):

            q = self.vectorizer.transform([qn])

            scores = cosine_similarity(
                q,
                self.matrix
            ).ravel()

            scored = []

            for index in candidates:

                score = float(
                    scores[index]
                )

                if score <= 0:
                    continue

                product = dict(
                    self.products[index]
                )

                # ---------------------------------
                # Technical intent bonus
                # ---------------------------------

                if intent and product_matches_intent(
                    product,
                    intent
                ):
                    score += 0.20

                product["_score"] = round(
                    score,
                    4
                )

                product["_intent"] = intent

                scored.append(product)

            scored.sort(
                key=lambda x: x["_score"],
                reverse=True
            )

            return scored[:top_k]

        # ---------------------------------------------
        # Pure Python fallback
        # ---------------------------------------------

        q_toks = Counter(
            re.findall(
                r"[\w\u0600-\u06FF]{2,}",
                qn
            )
        )

        scored = []

        for index in candidates:

            tf = self._tok_docs[index]

            score = 0.0

            for token, count in q_toks.items():

                if token in tf:

                    score += (
                        (1 + math.log(tf[token]))
                        * self._idf.get(token, 1)
                        * count
                    )

            if intent:

                product = self.products[index]

                if product_matches_intent(
                    product,
                    intent
                ):
                    score += 2.0

            if score > 0:

                product = dict(
                    self.products[index]
                )

                product["_score"] = round(
                    score,
                    4
                )

                product["_intent"] = intent

                scored.append(product)

        scored.sort(
            key=lambda x: x["_score"],
            reverse=True
        )

        return scored[:top_k]


    # -----------------------------------------------------
    # Build LLM context
    # -----------------------------------------------------

    def build_context(
        self,
        hits: list[dict]
    ) -> str:

        blocks = []

        for p in hits:

            attrs = (
                p.get("attributes")
                or p.get("technical_specs")
                or {}
            )

            if isinstance(attrs, dict):

                attrs_text = " | ".join(
                    f"{k}: {v}"
                    for k, v in attrs.items()
                )

            else:

                attrs_text = str(
                    attrs or ""
                )

            blocks.append(

                f"نام محصول: {p.get('name', '')}\n"

                f"برند: {p.get('brand', '')}\n"

                f"SKU: {p.get('sku', '')}\n"

                f"قیمت: "
                f"{p.get('price', '') or p.get('price_text', '')}\n"

                f"دسته: "
                f"{p.get('category', '')}\n"

                f"امتیاز جستجو: "
                f"{p.get('_score', '')}\n"

                f"عملیات تشخیص داده‌شده: "
                f"{p.get('_intent', '')}\n"

                f"توضیحات: "
                f"{(p.get('description') or p.get('short_description') or '')[:500]}\n"

                f"ویژگی‌ها: "
                f"{' | '.join(str(x) for x in (p.get('features') or []))}\n"

                f"کاربرد: "
                f"{' | '.join(str(x) for x in (p.get('applications') or []))}\n"

                f"مشخصات فنی: "
                f"{attrs_text}\n"

                f"لینک: "
                f"{p.get('url', '')}"
            )

        return "\n\n---\n\n".join(blocks)