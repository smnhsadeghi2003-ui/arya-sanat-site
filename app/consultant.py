import json
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import PRODUCTS_FILE, KNOWLEDGE_FILE


# =========================================================
# Normalize Persian Text
# =========================================================

def normalize_text(text):
    if text is None:
        return ""

    text = str(text)

    # Arabic → Persian
    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    # حذف نیم‌فاصله
    text = text.replace("\u200c", " ")

    # Persian digits → English
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"

    for p, e in zip(persian_digits, english_digits):
        text = text.replace(p, e)

    # Arabic digits → English
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"

    for a, e in zip(arabic_digits, english_digits):
        text = text.replace(a, e)

    # فاصله‌های اضافی
    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()


# =========================================================
# Intent Detection
# =========================================================

def detect_intent(query):
    """
    تشخیص نوع عملیات از سؤال کاربر
    """

    q = normalize_text(query)

    drilling_words = [
        "سوراخ",
        "سوراخکاری",
        "سوراخ کاری",
        "مته",
        "drill",
        "drilling",
    ]

    tapping_words = [
        "قلاویز",
        "قلاویزکاری",
        "قلاویز کاری",
        "رزوه داخلی",
        "تپ",
        "tap",
        "tapping",
    ]

    milling_words = [
        "فرز",
        "فرزکاری",
        "فرز کاری",
        "شیار",
        "milling",
        "mill",
    ]

    turning_words = [
        "تراش",
        "تراشکاری",
        "تراش کاری",
        "الماس تراش",
        "رنده تراش",
        "turning",
        "lathe",
    ]

    center_drilling_words = [
        "مته مرغک",
        "مرغک",
        "سوراخ مرکز",
        "سوراخ مرکزی",
        "center drill",
        "center drilling",
    ]

    # ترتیب مهم است
    if any(word in q for word in center_drilling_words):
        return "center_drilling"

    if any(word in q for word in tapping_words):
        return "tapping"

    if any(word in q for word in milling_words):
        return "milling"

    if any(word in q for word in turning_words):
        return "turning"

    if any(word in q for word in drilling_words):
        return "drilling"

    return "general"


# =========================================================
# Diameter Extraction
# =========================================================

def extract_diameter(query):
    """
    استخراج قطر از سؤال کاربر.

    مثال:
    سوراخ 30 میلی متر → 30
    سوراخ ۳۰ میلی‌متر → 30
    قطر 8mm → 8
    """

    q = normalize_text(query)

    patterns = [
        r"(?:سوراخ|قطر)\s*(?:با\s*)?(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
        r"(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
    ]

    for pattern in patterns:

        match = re.search(pattern, q)

        if match:

            try:
                return float(match.group(1))

            except ValueError:
                return None

    return None


# =========================================================
# Product Text
# =========================================================

def get_product_text(product):
    """
    ترکیب اطلاعات محصول برای جستجوی متنی
    """

    fields = [
        "name",
        "brand",
        "sku",
        "category",
        "price",
        "short_description",
        "description",
        "features",
        "advantages",
        "applications",
        "attributes",
        "technical_specs",
        "search_text",
    ]

    values = []

    for field in fields:

        value = product.get(field, "")

        if isinstance(value, list):

            value = " ".join(
                str(x)
                for x in value
            )

        elif isinstance(value, dict):

            value = " ".join(
                f"{k} {v}"
                for k, v in value.items()
            )

        values.append(
            str(value)
        )

    return normalize_text(
        " ".join(values)
    )


# =========================================================
# Extract Product Diameter Information
# =========================================================

def extract_product_diameters(product):

    text = get_product_text(product)

    ranges = []
    singles = []

    # ---------------------------------------------
    # Range
    # مثال:
    # 1 تا 13 میلی متر
    # 2-10 میلی متر
    # ---------------------------------------------

    range_patterns = [
        r"(\d+(?:\.\d+)?)\s*تا\s*(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
        r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
    ]

    for pattern in range_patterns:

        matches = re.findall(
            pattern,
            text
        )

        for min_value, max_value in matches:

            ranges.append(
                (
                    float(min_value),
                    float(max_value)
                )
            )

    # ---------------------------------------------
    # Single diameter
    # ---------------------------------------------

    single_pattern = (
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:میلی\s*متر|میلیمتر|mm)"
    )

    matches = re.findall(
        single_pattern,
        text
    )

    for value in matches:

        value = float(value)

        singles.append(value)

    return ranges, singles


# =========================================================
# Diameter Matching
# =========================================================

def product_matches_diameter(product, diameter):
    """
    بررسی تطبیق قطر محصول با قطر درخواست‌شده.
    """

    if diameter is None:
        return True

    ranges, singles = extract_product_diameters(
        product
    )

    # ---------------------------------------------
    # اگر بازه مشخص دارد
    # ---------------------------------------------

    if ranges:

        for min_value, max_value in ranges:

            if min_value <= diameter <= max_value:
                return True

        # اگر قطر خارج از همه بازه‌هاست
        return False

    # ---------------------------------------------
    # اگر سایز تکی دارد
    # ---------------------------------------------

    if singles:

        for value in singles:

            if abs(value - diameter) < 0.001:
                return True

        return False

    # ---------------------------------------------
    # اگر هیچ اطلاعات قطری ندارد
    # ---------------------------------------------

    return False


# =========================================================
# Operation Matching
# =========================================================

def product_matches_intent(product, intent):
    """
    بررسی ارتباط محصول با عملیات موردنظر.
    """

    text = get_product_text(product)

    name = normalize_text(
        product.get("name", "")
    )

    category = normalize_text(
        product.get("category", "")
    )

    # =====================================================
    # Center Drilling
    # =====================================================

    if intent == "center_drilling":

        keywords = [
            "مته مرغک",
            "مرغک",
            "center drill",
            "center drilling",
        ]

        return any(
            word in text
            for word in keywords
        )

    # =====================================================
    # Drilling
    # =====================================================

    if intent == "drilling":

        # محصولات نامرتبط
        wrong_product_keywords = [
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
            word in name or word in category
            for word in wrong_product_keywords
        ):
            return False

        # برای سوراخ‌کاری باید خود محصول مته باشد
        drilling_product_keywords = [
            "مته",
            "drill",
            "drilling",
        ]

        if not any(
            word in name
            for word in drilling_product_keywords
        ):
            return False

        return True

    # =====================================================
    # Tapping
    # =====================================================

    if intent == "tapping":

        keywords = [
            "قلاویز",
            "tap",
            "tapping",
            "رزوه داخلی",
        ]

        return any(
            word in text
            for word in keywords
        )

    # =====================================================
    # Milling
    # =====================================================

    if intent == "milling":

        keywords = [
            "فرز",
            "فرزکاری",
            "milling",
            "mill",
            "end mill",
            "face mill",
        ]

        return any(
            word in text
            for word in keywords
        )

    # =====================================================
    # Turning
    # =====================================================

    if intent == "turning":

        keywords = [
            "تراش",
            "تراشکاری",
            "الماس تراش",
            "رنده تراش",
            "turning",
            "lathe",
            "insert",
        ]

        return any(
            word in text
            for word in keywords
        )

    # =====================================================
    # General
    # =====================================================

    return True


# =========================================================
# Product RAG
# =========================================================

class ProductRAG:

    def __init__(
        self,
        products_file=PRODUCTS_FILE,
        knowledge_file=KNOWLEDGE_FILE,
    ):

        self.products_file = Path(
            products_file
        )

        self.knowledge_file = Path(
            knowledge_file
        )

        # ---------------------------------------------
        # Load data
        # ---------------------------------------------

        self.products = self.load_json(
            self.products_file
        )

        self.knowledge = self.load_json(
            self.knowledge_file
        )

        # ---------------------------------------------
        # Documents
        # ---------------------------------------------

        self.documents = [
            get_product_text(product)
            for product in self.products
        ]

        # ---------------------------------------------
        # TF-IDF
        # ---------------------------------------------

        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
        )

        if self.documents:

            self.matrix = (
                self.vectorizer.fit_transform(
                    self.documents
                )
            )

        else:

            self.matrix = None

    # =====================================================
    # Load JSON
    # =====================================================

    @staticmethod
    def load_json(path):

        if not path.exists():

            print(
                f"JSON file not found: {path}"
            )

            return []

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

            if isinstance(data, list):
                return data

            return []

        except Exception as e:

            print(
                f"Error loading JSON {path}: {e}"
            )

            return []

    # =====================================================
    # Search
    # =====================================================

    def search(
        self,
        query,
        top_k=5,
    ):

        if not self.products:
            return []

        if self.matrix is None:
            return []

        query_normalized = normalize_text(
            query
        )

        # ---------------------------------------------
        # Detect intent
        # ---------------------------------------------

        intent = detect_intent(
            query_normalized
        )

        # ---------------------------------------------
        # Extract diameter
        # ---------------------------------------------

        diameter = extract_diameter(
            query_normalized
        )

        # ---------------------------------------------
        # Query vector
        # ---------------------------------------------

        query_vector = (
            self.vectorizer.transform(
                [query_normalized]
            )
        )

        similarities = cosine_similarity(
            query_vector,
            self.matrix,
        )[0]

        results = []

        # =================================================
        # Process products
        # =================================================

        for index, product in enumerate(
            self.products
        ):

            score = float(
                similarities[index]
            )

            # ---------------------------------------------
            # Operation filter
            # ---------------------------------------------

            if not product_matches_intent(
                product,
                intent,
            ):
                continue

            # ---------------------------------------------
            # Diameter filter
            # ---------------------------------------------

            if diameter is not None:

                if not product_matches_diameter(
                    product,
                    diameter,
                ):
                    continue

            # ---------------------------------------------
            # Operation bonus
            # ---------------------------------------------

            if intent != "general":

                score += 0.15

            # ---------------------------------------------
            # Diameter bonus
            # ---------------------------------------------

            if diameter is not None:

                ranges, singles = (
                    extract_product_diameters(
                        product
                    )
                )

                diameter_match = False

                for min_value, max_value in ranges:

                    if min_value <= diameter <= max_value:
                        diameter_match = True

                for value in singles:

                    if abs(
                        value - diameter
                    ) < 0.001:
                        diameter_match = True

                if diameter_match:
                    score += 0.30

            # ---------------------------------------------
            # Save result
            # ---------------------------------------------

            product_copy = dict(
                product
            )

            product_copy["_score"] = score

            product_copy["_intent"] = intent

            if diameter is not None:

                product_copy["_diameter"] = diameter

            results.append(
                product_copy
            )

        # =================================================
        # Sort
        # =================================================

        results.sort(
            key=lambda x: x.get(
                "_score",
                0
            ),
            reverse=True,
        )

        return results[:top_k]

    # =====================================================
    # Build Context
    # =====================================================

    def build_context(
        self,
        hits,
        max_items=5,
    ):

        if not hits:

            return (
                "محصول مرتبطی پیدا نشد."
            )

        parts = []

        for product in hits[:max_items]:

            parts.append(
                f"""
نام محصول: {product.get("name", "")}
برند: {product.get("brand", "")}
دسته‌بندی: {product.get("category", "")}
کد محصول: {product.get("sku", "")}
توضیحات: {product.get("description", "")}
ویژگی‌ها: {product.get("features", "")}
کاربردها: {product.get("applications", "")}
مشخصات فنی: {product.get("technical_specs", "")}
امتیاز: {product.get("_score", 0):.3f}
عملیات: {product.get("_intent", "")}
قطر درخواست‌شده: {product.get("_diameter", "")}
""".strip()
            )

        return (
            "\n\n"
            "--------------------"
            "\n\n"
        ).join(parts)


# =========================================================
# Direct Test
# =========================================================

if __name__ == "__main__":

    rag = ProductRAG()

    test_questions = [

        "برای سوراخ 30 میلی متر روی فولاد چه ابزاری؟",

        "برای سوراخ 10 میلی متر روی آلومینیوم چه ابزاری مناسب است؟",

        "برای ایجاد رزوه M10 روی فولاد چه قلاویزی پیشنهاد می کنید؟",

        "برای شیارزنی روی فولاد چه فرزی مناسب است؟",

        "برای تراشکاری فولاد چه المانی مناسب است؟",

        "برای سوراخ کاری چه ابزاری خوبه؟",

    ]

    for question in test_questions:

        print("\n")
        print("=" * 70)

        print(
            "QUESTION:",
            question
        )

        print("=" * 70)

        hits = rag.search(
            question,
            top_k=5,
        )

        if not hits:

            print(
                "هیچ محصول مناسبی پیدا نشد."
            )

        for i, hit in enumerate(
            hits,
            start=1,
        ):

            print(
                f"{i}. "
                f"{hit.get('name')} | "
                f"score={hit.get('_score', 0):.3f} | "
                f"intent={hit.get('_intent')} | "
                f"diameter={hit.get('_diameter', '')}"
            )