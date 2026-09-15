import json
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import PRODUCTS_FILE, KNOWLEDGE_FILE


# =========================================================
# Normalization
# =========================================================

def normalize_text(text):
    """
    یکسان‌سازی متن فارسی و اعداد
    """

    if text is None:
        return ""

    text = str(text)

    # حروف عربی → فارسی
    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    # حذف نیم‌فاصله
    text = text.replace("\u200c", " ")

    # اعداد فارسی
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"

    for p, e in zip(persian_digits, english_digits):
        text = text.replace(p, e)

    # اعداد عربی
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"

    for a, e in zip(arabic_digits, english_digits):
        text = text.replace(a, e)

    # فاصله‌های اضافی
    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()


# =========================================================
# Intent detection
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
# Diameter extraction
# =========================================================

def extract_diameter(query):
    """
    استخراج قطر سوراخ از سؤال کاربر.

    مثال:
    سوراخ 30 میلی متر → 30
    سوراخ ۱۲ میلی‌متر → 12
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
# Product text
# =========================================================

def get_product_text(product):
    """
    تمام اطلاعات متنی محصول را برای جستجو ترکیب می‌کند.
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
            value = " ".join(str(x) for x in value)

        elif isinstance(value, dict):
            value = " ".join(
                f"{k} {v}" for k, v in value.items()
            )

        values.append(str(value))

    return normalize_text(" ".join(values))


# =========================================================
# Diameter matching
# =========================================================

def product_matches_diameter(product, diameter):
    """
    بررسی می‌کند آیا محصول برای قطر موردنظر مناسب است یا نه.

    مثال:

    محصول:
    مته 1 تا 13 میلی متر

    سؤال:
    سوراخ 30 میلی متر

    نتیجه:
    False

    اما:

    سؤال:
    سوراخ 10 میلی متر

    نتیجه:
    True
    """

    if diameter is None:
        return True

    text = get_product_text(product)

    # -----------------------------------------------------
    # بازه‌ها
    # مثال:
    # 1 تا 13 میلی متر
    # 2-10 میلی متر
    # 2 - 10 mm
    # -----------------------------------------------------

    range_patterns = [
        r"(\d+(?:\.\d+)?)\s*تا\s*(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
        r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
    ]

    found_range = False

    for pattern in range_patterns:

        matches = re.findall(pattern, text)

        for min_value, max_value in matches:

            found_range = True

            min_value = float(min_value)
            max_value = float(max_value)

            if min_value <= diameter <= max_value:
                return True

    # -----------------------------------------------------
    # اندازه‌های تکی
    # مثال:
    # مته 10 میلی متر
    # مته 12mm
    # -----------------------------------------------------

    single_patterns = [
        r"(\d+(?:\.\d+)?)\s*(?:میلی\s*متر|میلیمتر|mm)",
    ]

    for pattern in single_patterns:

        matches = re.findall(pattern, text)

        for value in matches:

            value = float(value)

            if abs(value - diameter) < 0.001:
                return True

    # -----------------------------------------------------
    # اگر محصول بازه مشخص داشت ولی قطر داخل بازه نبود
    # -----------------------------------------------------

    if found_range:
        return False

    # اگر اطلاعات اندازه مشخصی در محصول نبود،
    # فعلاً محصول را حذف نمی‌کنیم.
    return True


# =========================================================
# Operation matching
# =========================================================

def product_matches_intent(product, intent):
    """
    بررسی می‌کند محصول با نوع عملیات موردنظر هماهنگ است یا نه.
    """

    text = get_product_text(product)

    name = normalize_text(product.get("name", ""))
    category = normalize_text(product.get("category", ""))

    # -----------------------------------------------------
    # Center drilling
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Drilling
    # -----------------------------------------------------

    if intent == "drilling":

        drilling_keywords = [
            "مته",
            "drill",
            "drilling",
            "مته hss",
            "مته کبالت",
            "مته کارباید",
        ]

        wrong_keywords = [
            "قلاویز",
            "tap",
            "tapping",
            "فرز",
            "تراش",
            "الماس تراش",
            "رنده تراش",
            "مهره",
            "کولت",
            "هلدر",
        ]

        has_drilling = any(
            word in text
            for word in drilling_keywords
        )

        has_wrong = any(
            word in name or word in category
            for word in wrong_keywords
        )

        if has_wrong:
            return False

        return has_drilling

    # -----------------------------------------------------
    # Tapping
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Milling
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Turning
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # General
    # -----------------------------------------------------

    return True


# =========================================================
# RAG Class
# =========================================================

class ProductRAG:

    def __init__(
        self,
        products_file=PRODUCTS_FILE,
        knowledge_file=KNOWLEDGE_FILE,
    ):

        self.products_file = Path(products_file)
        self.knowledge_file = Path(knowledge_file)

        self.products = self.load_json(
            self.products_file
        )

        self.knowledge = self.load_json(
            self.knowledge_file
        )

        self.documents = [
            get_product_text(product)
            for product in self.products
        ]

        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
        )

        if self.documents:
            self.matrix = self.vectorizer.fit_transform(
                self.documents
            )
        else:
            self.matrix = None

    # =====================================================
    # Load JSON
    # =====================================================

    @staticmethod
    def load_json(path):

        if not path.exists():
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

        query_normalized = normalize_text(query)

        intent = detect_intent(
            query_normalized
        )

        diameter = extract_diameter(
            query_normalized
        )

        # -------------------------------------------------
        # تبدیل سؤال به بردار
        # -------------------------------------------------

        query_vector = self.vectorizer.transform(
            [query_normalized]
        )

        similarities = cosine_similarity(
            query_vector,
            self.matrix,
        )[0]

        # -------------------------------------------------
        # ساخت نتایج
        # -------------------------------------------------

        results = []

        for index, product in enumerate(
            self.products
        ):

            score = float(
                similarities[index]
            )

            # ---------------------------------------------
            # فیلتر عملیات
            # ---------------------------------------------

            if not product_matches_intent(
                product,
                intent,
            ):
                continue

            # ---------------------------------------------
            # فیلتر قطر
            # ---------------------------------------------

            if not product_matches_diameter(
                product,
                diameter,
            ):
                continue

            # ---------------------------------------------
            # امتیاز عملیات
            # ---------------------------------------------

            if intent != "general":

                score += 0.15

            # ---------------------------------------------
            # امتیاز تطبیق قطر
            # ---------------------------------------------

            if diameter is not None:

                text = get_product_text(
                    product
                )

                diameter_text = str(
                    int(diameter)
                    if diameter.is_integer()
                    else diameter
                )

                if (
                    diameter_text in text
                ):
                    score += 0.20

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

        # -------------------------------------------------
        # مرتب‌سازی
        # -------------------------------------------------

        results.sort(
            key=lambda x: x.get(
                "_score",
                0
            ),
            reverse=True,
        )

        return results[:top_k]

    # =====================================================
    # Context
    # =====================================================

    def build_context(
        self,
        hits,
        max_items=5,
    ):

        if not hits:
            return "محصول مرتبطی پیدا نشد."

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
امتیاز تطبیق: {product.get("_score", 0):.3f}
نوع عملیات: {product.get("_intent", "")}
""".strip()
            )

        return "\n\n--------------------\n\n".join(
            parts
        )


# =========================================================
# تست مستقیم فایل
# =========================================================

if __name__ == "__main__":

    rag = ProductRAG()

    test_questions = [
        "برای سوراخ 30 میلی متر روی فولاد چه ابزاری؟",
        "برای سوراخ 10 میلی متر روی آلومینیوم چه ابزاری مناسب است؟",
        "برای ایجاد رزوه M10 روی فولاد چه قلاویزی پیشنهاد می کنید؟",
        "برای شیارزنی روی فولاد چه فرزی مناسب است؟",
        "برای تراشکاری فولاد چه المانی مناسب است؟",
    ]

    for question in test_questions:

        print("\n")
        print("=" * 70)
        print("QUESTION:")
        print(question)
        print("=" * 70)

        hits = rag.search(
            question,
            top_k=5,
        )

        for i, hit in enumerate(
            hits,
            start=1,
        ):

            print(
                f"{i}. "
                f"{hit.get('name')} | "
                f"score={hit.get('_score'):.3f} | "
                f"intent={hit.get('_intent')}"
            )