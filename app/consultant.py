import re


# =========================================================
# Normalize
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
# Operation Detection
# =========================================================

def detect_operation(message):

    q = normalize_text(message)

    if any(x in q for x in [
        "مته مرغک",
        "مرغک",
        "سوراخ مرکز",
        "سوراخ مرکزی",
        "center drill",
    ]):
        return "center_drilling"

    if any(x in q for x in [
        "قلاویز",
        "قلاویزکاری",
        "قلاویز کاری",
        "رزوه داخلی",
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
# Product Operation Matching
# =========================================================

def product_matches_operation(product, operation):

    name = normalize_text(
        product.get("name", "")
    )

    category = normalize_text(
        product.get("category", "")
    )

    text = normalize_text(
        " ".join([
            str(product.get("name", "")),
            str(product.get("description", "")),
            str(product.get("features", "")),
            str(product.get("applications", "")),
            str(product.get("technical_specs", "")),
        ])
    )

    # -----------------------------------------------------
    # Center drilling
    # -----------------------------------------------------

    if operation == "center_drilling":

        return any(x in text for x in [
            "مته مرغک",
            "مرغک",
            "center drill",
            "center drilling",
        ])

    # -----------------------------------------------------
    # Drilling
    # -----------------------------------------------------

    if operation == "drilling":

        if any(x in name for x in [
            "قلاویز",
            "tap",
            "فرز",
            "تراش",
            "الماس تراش",
            "مهره",
            "کولت",
            "هلدر",
        ]):
            return False

        return any(x in text for x in [
            "مته",
            "drill",
            "drilling",
        ])

    # -----------------------------------------------------
    # Tapping
    # -----------------------------------------------------

    if operation == "tapping":

        return any(x in text for x in [
            "قلاویز",
            "tap",
            "tapping",
            "رزوه داخلی",
        ])

    # -----------------------------------------------------
    # Milling
    # -----------------------------------------------------

    if operation == "milling":

        return any(x in text for x in [
            "فرز",
            "فرزکاری",
            "milling",
            "mill",
            "end mill",
            "face mill",
        ])

    # -----------------------------------------------------
    # Turning
    # -----------------------------------------------------

    if operation == "turning":

        return any(x in text for x in [
            "تراش",
            "تراشکاری",
            "الماس تراش",
            "رنده تراش",
            "turning",
            "lathe",
            "insert",
        ])

    return True


# =========================================================
# Missing Information
# =========================================================

def detect_missing_info(message):

    q = normalize_text(message)

    operation = detect_operation(q)

    missing = []

    # برای سوراخکاری
    if operation == "drilling":

        if not any(
            x in q
            for x in [
                "میلی متر",
                "میلیمتر",
                "mm",
            ]
        ):
            missing.append("قطر سوراخ")

        if not any(
            x in q
            for x in [
                "فولاد",
                "آلومینیوم",
                "استیل",
                "چدن",
                "مس",
                "برنج",
                "تیتانیوم",
                "پلاستیک",
            ]
        ):
            missing.append("جنس قطعه")

    return missing


# =========================================================
# Build Advice
# =========================================================

def build_advice(message, hits):

    operation = detect_operation(message)

    # -----------------------------------------------------
    # Filter products one more time
    # -----------------------------------------------------

    valid_hits = []

    for product in hits:

        if product_matches_operation(
            product,
            operation,
        ):
            valid_hits.append(product)

    # -----------------------------------------------------
    # No result
    # -----------------------------------------------------

    if not valid_hits:

        return (
            "برای این درخواست محصول مناسبی در اطلاعات فعلی "
            "پیدا نکردم. اگر قطر، جنس قطعه و نوع عملیات را "
            "بگویید، می‌توانم دقیق‌تر بررسی کنم."
        )

    # -----------------------------------------------------
    # Greeting
    # -----------------------------------------------------

    q = normalize_text(message)

    if any(x in q for x in [
        "سلام",
        "درود",
        "hello",
        "hi",
    ]):

        return (
            "سلام 🌷\n"
            "من مشاور تخصصی ابزارهای صنعتی هستم. "
            "سؤالتان را درباره انتخاب ابزار بپرسید."
        )

    # -----------------------------------------------------
    # Product recommendation
    # -----------------------------------------------------

    lines = []

    if operation == "drilling":

        lines.append(
            "برای سوراخ‌کاری، بر اساس اطلاعات محصولات موجود، "
            "این گزینه‌ها به درخواست شما نزدیک‌تر هستند:"
        )

    elif operation == "tapping":

        lines.append(
            "برای قلاویزکاری، این محصولات مرتبط‌تر هستند:"
        )

    elif operation == "milling":

        lines.append(
            "برای فرزکاری، این محصولات مرتبط‌تر هستند:"
        )

    elif operation == "turning":

        lines.append(
            "برای تراشکاری، این محصولات مرتبط‌تر هستند:"
        )

    elif operation == "center_drilling":

        lines.append(
            "برای سوراخ‌مرکزی، این محصولات مرتبط‌تر هستند:"
        )

    else:

        lines.append(
            "محصولات مرتبط با درخواست شما:"
        )

    # -----------------------------------------------------
    # Products
    # -----------------------------------------------------

    for index, product in enumerate(
        valid_hits[:3],
        start=1,
    ):

        name = product.get(
            "name",
            "محصول بدون نام",
        )

        brand = product.get(
            "brand",
            "",
        )

        url = product.get(
            "url",
            "",
        )

        line = f"{index}. {name}"

        if brand:
            line += f" — برند: {brand}"

        if url:
            line += f"\n   لینک: {url}"

        lines.append(line)

    # -----------------------------------------------------
    # Technical note
    # -----------------------------------------------------

    if operation == "drilling":

        lines.append(
            "\nنکته: برای انتخاب دقیق مته، "
            "قطر سوراخ، جنس قطعه و نوع دستگاه اهمیت دارد."
        )

    elif operation == "tapping":

        lines.append(
            "\nنکته: برای انتخاب قلاویز، "
            "سایز رزوه، گام رزوه و جنس قطعه اهمیت دارد."
        )

    return "\n".join(lines)