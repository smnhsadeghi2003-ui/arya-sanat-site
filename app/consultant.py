import re


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


def detect_operation(message):
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


def extract_diameter(message):
    q = normalize_text(message)

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


def product_matches_operation(product, operation):
    name = normalize_text(product.get("name", ""))
    category = normalize_text(product.get("category", ""))

    text = normalize_text(
        " ".join([
            str(product.get("name", "")),
            str(product.get("description", "")),
            str(product.get("features", "")),
            str(product.get("applications", "")),
            str(product.get("technical_specs", "")),
        ])
    )

    if operation == "center_drilling":
        return any(
            x in text
            for x in [
                "مته مرغک",
                "مرغک",
                "center drill",
                "center drilling",
            ]
        )

    if operation == "drilling":

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

        return any(
            x in name
            for x in [
                "مته",
                "drill",
                "drilling",
            ]
        )

    if operation == "tapping":
        return any(
            x in text
            for x in [
                "قلاویز",
                "tap",
                "tapping",
                "رزوه داخلی",
            ]
        )

    if operation == "milling":
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

    if operation == "turning":
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


def build_advice(message, hits):
    operation = detect_operation(message)
    diameter = extract_diameter(message)

    valid_hits = []

    for product in hits:
        if product_matches_operation(product, operation):
            valid_hits.append(product)

    # -----------------------------------------
    # وقتی محصول مناسب پیدا نشده
    # -----------------------------------------

    if not valid_hits:

        if operation == "drilling":

            if diameter is not None:
                return (
                    f"برای سوراخ‌کاری با قطر "
                    f"{diameter:g} میلی‌متر، "
                    f"در محصولات فعلی گزینه مناسبی "
                    f"با این سایز پیدا نکردم.\n\n"
                    f"بنابراین مته‌هایی با بازه سایز کوچک‌تر "
                    f"را به‌عنوان گزینه مناسب پیشنهاد نمی‌کنم."
                )

            return (
                "برای سوراخ‌کاری محصول مناسبی "
                "در اطلاعات فعلی پیدا نکردم."
            )

        return (
            "برای این درخواست محصول مناسبی "
            "در اطلاعات فعلی پیدا نکردم."
        )

    # -----------------------------------------
    # پاسخ سلام
    # -----------------------------------------

    q = normalize_text(message)

    if any(
        x in q
        for x in [
            "سلام",
            "درود",
            "hello",
            "hi",
            "salam",
            "slm"
        ]
    ):
        return (
            "سلام 🌷\n"
            "من مشاور تخصصی ابزارهای صنعتی هستم. "
            "سؤال خود را درباره انتخاب ابزار بپرسید."
        )

    # -----------------------------------------
    # ساخت پاسخ
    # -----------------------------------------

    lines = []

    if operation == "drilling":

        if diameter is not None:
            lines.append(
                f"برای سوراخ‌کاری با قطر "
                f"{diameter:g} میلی‌متر، "
                f"محصولات مرتبط موجود در سیستم:"
            )
        else:
            lines.append(
                "برای سوراخ‌کاری، "
                "محصولات مرتبط موجود در سیستم:"
            )

    elif operation == "tapping":
        lines.append(
            "برای قلاویزکاری، "
            "محصولات مرتبط:"
        )

    elif operation == "milling":
        lines.append(
            "برای فرزکاری، "
            "محصولات مرتبط:"
        )

    elif operation == "turning":
        lines.append(
            "برای تراشکاری، "
            "محصولات مرتبط:"
        )

    elif operation == "center_drilling":
        lines.append(
            "برای سوراخ‌مرکزی، "
            "محصولات مرتبط:"
        )

    else:
        lines.append(
            "محصولات مرتبط با درخواست شما:"
        )

    # -----------------------------------------
    # نمایش محصولات
    # -----------------------------------------

    for index, product in enumerate(
        valid_hits[:3],
        start=1,
    ):

        name = product.get(
            "name",
            "محصول بدون نام"
        )

        brand = product.get(
            "brand",
            ""
        )

        url = product.get(
            "url",
            ""
        )

        line = f"{index}. {name}"

        if brand:
            line += f" — برند: {brand}"

        if url:
            line += f"\n   لینک: {url}"

        lines.append(line)

    # -----------------------------------------
    # نکته تخصصی
    # -----------------------------------------

    if operation == "drilling":
        lines.append(
            "\nنکته: برای انتخاب دقیق مته، "
            "قطر سوراخ، جنس قطعه، "
            "عمق سوراخ و نوع دستگاه "
            "اهمیت دارند."
        )

    elif operation == "tapping":
        lines.append(
            "\nنکته: برای انتخاب قلاویز، "
            "سایز رزوه، گام رزوه، "
            "جنس قطعه و نوع سوراخ "
            "اهمیت دارند."
        )

    elif operation == "milling":
        lines.append(
            "\nنکته: برای انتخاب فرز، "
            "جنس قطعه، نوع شیار، "
            "عمق براده‌برداری و دستگاه "
            "اهمیت دارند."
        )

    elif operation == "turning":
        lines.append(
            "\nنکته: برای انتخاب الماس تراش، "
            "جنس قطعه، نوع عملیات و "
            "شرایط ماشین‌کاری اهمیت دارند."
        )

    return "\n".join(lines)


# -----------------------------------------
# تست مستقیم فایل
# -----------------------------------------

if __name__ == "__main__":

    question = "برای سوراخ 30 میلی متر روی فولاد چه ابزاری؟"

    print("Operation:", detect_operation(question))
    print("Diameter:", extract_diameter(question))

    print(
        build_advice(
            question,
            []
        )
    )