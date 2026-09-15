import json
import re
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

PRODUCTS_FILE = DATA_DIR / "products_full.json"
KNOWLEDGE_FILE = DATA_DIR / "site_knowledge.json"


# =========================================================
# Normalize text
# =========================================================

def normalize_text(text):

    if text is None:
        return ""

    text = str(text)

    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")
    text = text.replace("\u200c", " ")

    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"

    for p, e in zip(persian_digits, english_digits):
        text = text.replace(p, e)

    arabic_digits = "٠١٢٣٤٥٦٧٨٩"

    for a, e in zip(arabic_digits, english_digits):
        text = text.replace(a, e)

    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()


# =========================================================
# Detect intent
# =========================================================

def detect_intent(message):

    q = normalize_text(message)

    if any(x in q for x in [
        "مته مرغک",
        "مرغک",
        "سوراخ مرکز",
        "سوراخ مرکزی",
        "center drill",
        "center drilling",
    ]):
        return "center_drilling"

    if any(x in q for x in [
        "قلاویز",
        "قلاویزکاری",
        "قلاویز کاری",
        "رزوه داخلی",
        "تپ",
        "tap",
        "tapping",
    ]):
        return "tapping"

    if any(x in q for x in [
        "فرز",
        "فرزکاری",
        "فرز کاری",
        "شیار",
        "milling",
        "mill",
    ]):
        return "milling"

    if any(x in q for x in [
        "تراش",
        "تراشکاری",
        "تراش کاری",
        "الماس تراش",
        "رنده تراش",
        "turning",
        "lathe",
    ]):
        return "turning"

    if any(x in q for x in [
        "سوراخ",
        "سوراخکاری",
        "سوراخ کاری",
        "مته",
        "drill",
        "drilling",
    ]):
        return "drilling"

    return "general"


# =========================================================
# Extract diameter from user question
# =========================================================

def extract_diameter(message):

    q = normalize_text(message)

    patterns = [
        r"(?:سوراخ|قطر)\s*(?:با\s*)?(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
        r"(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            q
        )

        if match:

            try:
                return float(match.group(1))

            except ValueError:
                return None

    return None


# =========================================================
# Product text
# =========================================================

def get_product_text(product):

    parts = [
        product.get("name", ""),
        product.get("brand", ""),
        product.get("sku", ""),
        product.get("category", ""),
        product.get("description", ""),
        product.get("features", ""),
        product.get("advantages", ""),
        product.get("applications", ""),
        product.get("attributes", ""),
        product.get("technical_specs", ""),
        product.get("search_text", ""),
    ]

    return normalize_text(
        " ".join(
            str(x)
            for x in parts
            if x is not None
        )
    )


# =========================================================
# Extract diameter ranges from product
# =========================================================

def extract_product_diameters(product):

    # برای تشخیص سایز، اولویت با نام محصول است.
    name = normalize_text(
        product.get("name", "")
    )

    technical = normalize_text(
        product.get("technical_specs", "")
    )

    attributes = normalize_text(
        product.get("attributes", "")
    )

    text = " ".join([
        name,
        technical,
        attributes,
    ])

    ranges = []
    singles = []

    # -----------------------------------------------------
    # Range:
    #
    # 1 تا 10
    # 1 تا 10 میلی متر
    # 1-10
    # 1 - 10 mm
    # -----------------------------------------------------

    range_patterns = [

        r"(\d+(?:\.\d+)?)\s*تا\s*(\d+(?:\.\d+)?)"
        r"(?:\s*(?:میلی\s*متر|میلیمتر|mm))?",

        r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)"
        r"(?:\s*(?:میلی\s*متر|میلیمتر|mm))?",
    ]

    for pattern in range_patterns:

        matches = re.findall(
            pattern,
            text
        )

        for min_value, max_value in matches:

            min_value = float(min_value)
            max_value = float(max_value)

            # فقط بازه‌های منطقی را قبول کن
            if min_value <= max_value:

                ranges.append(
                    (
                        min_value,
                        max_value
                    )
                )

    # -----------------------------------------------------
    # Single diameter
    #
    # 10 میلی متر
    # 10mm
    # -----------------------------------------------------

    single_patterns = [
        r"(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
    ]

    for pattern in single_patterns:

        matches = re.findall(
            pattern,
            text
        )

        for value in matches:

            singles.append(
                float(value)
            )

    return ranges, singles


# =========================================================
# Check diameter
# =========================================================

def product_matches_diameter(
    product,
    diameter,
):

    if diameter is None:
        return True

    ranges, singles = extract_product_diameters(
        product
    )

    # -----------------------------------------------------
    # اگر بازه داریم
    # -----------------------------------------------------

    if ranges:

        for min_value, max_value in ranges:

            if min_value <= diameter <= max_value:
                return True

        return False

    # -----------------------------------------------------
    # اگر سایز دقیق داریم
    # -----------------------------------------------------

    if singles:

        for value in singles:

            if abs(value - diameter) < 0.0001:
                return True

        return False

    # -----------------------------------------------------
    # سایز مشخص نشده
    # -----------------------------------------------------

    return False


# =========================================================
# Check operation / intent
# =========================================================

def product_matches_intent(
    product,
    intent,
):

    name = normalize_text(
        product.get("name", "")
    )

    category = normalize_text(
        product.get("category", "")
    )

    text = get_product_text(
        product
    )

    # =====================================================
    # Center drilling
    # =====================================================

    if intent == "center_drilling":

        return any(
            x in text
            for x in [
                "مته مرغک",
                "مرغک",
                "center drill",
                "center drilling",
            ]
        )

    # =====================================================
    # Drilling
    # =====================================================

    if intent == "drilling":

        wrong_products = [
            "دستگاه مته تیز کن",
            "دستگاه مته تیزکنی",
            "دستگاه ابزار تیز کن",
            "دستگاه ابزار تیزکنی",
            "ابزار تیز کن",
            "ابزار تیزکنی",
            "تیز کردن مته",
            "مهره",
            "کولت",
            "هلدر",
            "قلاویز",
            "فرز",
            "الماس تراش",
            "رنده تراش",
        ]

        if any(
            x in name or x in category
            for x in wrong_products
        ):
            return False

        # برای سوراخکاری باید خود نام محصول
        # واقعاً به مته/دریل اشاره کند.
        return any(
            x in name
            for x in [
                "مته",
                "drill",
                "drilling",
            ]
        )

    # =====================================================
    # Tapping
    # =====================================================

    if intent == "tapping":

        return any(
            x in text
            for x in [
                "قلاویز",
                "tap",
                "tapping",
                "رزوه داخلی",
            ]
        )

    # =====================================================
    # Milling
    # =====================================================

    if intent == "milling":

        return any(
            x in text
            for x in [
                "فرز",
                "فرزکاری",
                "milling",
                "mill",
                "end mill",
                "face mill",
            ]
        )

    # =====================================================
    # Turning
    # =====================================================

    if intent == "turning":

        return any(
            x in text
            for x in [
                "تراش",
                "تراشکاری",
                "الماس تراش",
                "رنده تراش",
                "turning",
                "lathe",
                "insert",
            ]
        )

    return True


# =========================================================
# Product RAG
# =========================================================

class ProductRAG:

    def __init__(self):

        self.products = []
        self.knowledge = []

        # -------------------------------------------------
        # Load products
        # -------------------------------------------------

        if PRODUCTS_FILE.exists():

            with open(
                PRODUCTS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                self.products = json.load(f)

        # -------------------------------------------------
        # Load knowledge
        # -------------------------------------------------

        if KNOWLEDGE_FILE.exists():

            try:

                with open(
                    KNOWLEDGE_FILE,
                    "r",
                    encoding="utf-8"
                ) as f:

                    self.knowledge = json.load(f)

            except Exception:

                self.knowledge = []

        # -------------------------------------------------
        # Prepare TF-IDF
        # -------------------------------------------------

        self.documents = [
            get_product_text(product)
            for product in self.products
        ]

        if self.documents:

            self.vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                min_df=1,
            )

            self.matrix = self.vectorizer.fit_transform(
                self.documents
            )

        else:

            self.vectorizer = None
            self.matrix = None

    # =====================================================
    # Search
    # =====================================================

    def search(
        self,
        query,
        top_k=5,
    ):

        query = normalize_text(
            query
        )

        intent = detect_intent(
            query
        )

        diameter = extract_diameter(
            query
        )

        # -------------------------------------------------
        # Empty database
        # -------------------------------------------------

        if not self.products:

            return []

        # -------------------------------------------------
        # TF-IDF
        # -------------------------------------------------

        if self.vectorizer is not None:

            query_vector = self.vectorizer.transform(
                [query]
            )

            similarities = cosine_similarity(
                query_vector,
                self.matrix
            )[0]

        else:

            similarities = np.zeros(
                len(self.products)
            )

        candidates = []

        # -------------------------------------------------
        # Filtering
        # -------------------------------------------------

        for index, product in enumerate(
            self.products
        ):

            # Operation filter
            if not product_matches_intent(
                product,
                intent
            ):
                continue

            # Diameter filter
            if diameter is not None:

                if not product_matches_diameter(
                    product,
                    diameter
                ):
                    continue

            score = float(
                similarities[index]
            )

            # -------------------------------------------------
            # Intent bonus
            # -------------------------------------------------

            score += 0.15

            # -------------------------------------------------
            # Diameter bonus
            # -------------------------------------------------

            if diameter is not None:

                score += 0.30

            product_copy = dict(
                product
            )

            product_copy["_score"] = score
            product_copy["_intent"] = intent
            product_copy["_diameter"] = diameter

            candidates.append(
                product_copy
            )

        # -------------------------------------------------
        # Sort
        # -------------------------------------------------

        candidates.sort(
            key=lambda x: x.get(
                "_score",
                0
            ),
            reverse=True
        )

        return candidates[:top_k]

    # =====================================================
    # Build context
    # =====================================================

    def build_context(
        self,
        hits,
    ):

        if not hits:
            return ""

        context_parts = []

        for product in hits:

            context_parts.append(
                "\n".join([
                    f"نام محصول: {product.get('name', '')}",
                    f"برند: {product.get('brand', '')}",
                    f"دسته‌بندی: {product.get('category', '')}",
                    f"توضیحات: {product.get('description', '')}",
                    f"ویژگی‌ها: {product.get('features', '')}",
                    f"کاربردها: {product.get('applications', '')}",
                    f"مشخصات فنی: {product.get('technical_specs', '')}",
                    f"لینک: {product.get('url', '')}",
                ])
            )

        return "\n\n--------------------\n\n".join(
            context_parts
        )


# =========================================================
# Direct test
# =========================================================

if __name__ == "__main__":

    rag = ProductRAG()

    tests = [
        "برای سوراخ 10 میلی متر روی آلومینیوم چه ابزاری مناسب است؟",
        "برای سوراخ 30 میلی متر روی فولاد چه ابزاری؟",
        "برای سوراخ کاری چه ابزاری خوبه؟",
    ]

    for question in tests:

        print("\n")
        print("=" * 80)

        print(
            "QUESTION:",
            question
        )

        print(
            "INTENT:",
            detect_intent(question)
        )

        print(
            "DIAMETER:",
            extract_diameter(question)
        )

        results = rag.search(
            question,
            top_k=5
        )

        print(
            "RESULTS:",
            len(results)
        )

        for product in results:

            print(
                "-",
                product.get("name"),
                "| score:",
                product.get("_score")
            )

        print("=" * 80)