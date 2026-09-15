import re


def normalize_msg(message: str) -> str:
    m = (message or "").strip().lower()

    for a, b in [
        ("ي", "ی"),
        ("ك", "ک"),
        ("\u200c", " "),
    ]:
        m = m.replace(a, b)

    # تبدیل اعداد فارسی و عربی
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"

    for p, e in zip(persian_digits, english_digits):
        m = m.replace(p, e)

    for p, e in zip(arabic_digits, english_digits):
        m = m.replace(p, e)

    return re.sub(r"\s+", " ", m)


# =========================================================
# INTENT
# =========================================================

def detect_intent(message: str) -> str:

    m = normalize_msg(message)
    words = m.split()

    greetings = [
        "سلام", "درود", "صبح بخیر", "عصر بخیر", "شب بخیر",
        "وقت بخیر", "hello", "hi", "hey",
        "خوبی", "چطوری", "چطورید", "حالت چطوره",
    ]

    if any(g in m for g in greetings) and len(words) <= 6:
        return "greeting"

    goodbyes = [
        "خداحافظ", "خدانگهدار", "بای", "bye",
        "goodbye", "see you", "خدا نگهدار",
        "فعلا", "فعلاً", "شب خوش",
    ]

    if any(g in m for g in goodbyes) and len(words) <= 6:
        return "goodbye"

    thanks = [
        "ممنون", "متشکرم", "مرسی", "تشکر",
        "خیلی ممنون", "thanks", "thank you",
    ]

    if any(t in m for t in thanks) and len(words) <= 5:
        return "thanks"

    contact_words = [
        "تماس", "آدرس", "شماره", "تلفن",
        "واتساپ", "whatsapp", "ایمیل",
        "محل", "کجا هستید", "چطور تماس",
        "پشتیبانی", "ساعت کاری", "ساعات کار",
        "راه ارتباطی", "contact", "address",
        "phone", "call", "location",
    ]

    if any(c in m for c in contact_words):
        return "contact"

    about_words = [
        "درباره", "شرکت", "آریا صنعت",
        "نمایندگی", "برندها",
        "شما کیستید", "چیکار میکنید",
        "about", "who are you",
        "what do you do", "company",
    ]

    if any(a in m for a in about_words) and not any(
        x in m
        for x in [
            "مته",
            "قلاویز",
            "کولت",
            "ساعت",
            "drill",
            "tap",
        ]
    ):
        return "about"

    return "product"


# =========================================================
# TECHNICAL OPERATION
# =========================================================

def detect_operation(message: str) -> str | None:

    m = normalize_msg(message)

    # ترتیب مهم است
    # چون «مته مرغک» نباید فقط به عنوان «مته» تشخیص داده شود.

    if any(
        x in m
        for x in [
            "مته مرغک",
            "مرغک",
            "center drill",
            "center drilling",
        ]
    ):
        return "center_drilling"

    if any(
        x in m
        for x in [
            "قلاویز",
            "قلاویزکاری",
            "رزوه داخلی",
            "رزوه زنی",
            "رزوه‌زنی",
            "tapping",
            "tap",
        ]
    ):
        return "tapping"

    if any(
        x in m
        for x in [
            "فرزکاری",
            "فرز",
            "فرز انگشتی",
            "milling",
            "end mill",
        ]
    ):
        return "milling"

    if any(
        x in m
        for x in [
            "تراشکاری",
            "تراش",
            "turning",
            "lathe",
        ]
    ):
        return "turning"

    if any(
        x in m
        for x in [
            "سوراخ",
            "سوراخکاری",
            "سوراخ کاری",
            "دریل",
            "ایجاد سوراخ",
            "drilling",
            "drill",
            "hole",
        ]
    ):
        return "drilling"

    return None


# =========================================================
# MISSING INFORMATION
# =========================================================

def detect_missing_info(message: str) -> list[str]:

    m = normalize_msg(message)
    missing = []

    operation = detect_operation(m)

    if operation == "drilling":

        if not any(
            x in m
            for x in [
                "فولاد",
                "استیل",
                "آلومینیوم",
                "چدن",
                "برنج",
                "مس",
                "ماده",
                "جنس",
                "steel",
                "aluminum",
            ]
        ):
            missing.append(
                "جنس قطعه (مثلاً فولاد یا آلومینیوم)"
            )

        if not re.search(
            r"\d+(?:\.\d+)?\s*(?:میلی.?متر|mm|میل)",
            m,
        ):

            if any(
                x in m
                for x in [
                    "سوراخ",
                    "قطر",
                    "diameter",
                ]
            ):
                missing.append(
                    "قطر سوراخ (میلی‌متر)"
                )

    return missing


# =========================================================
# PRODUCT FILTER
# =========================================================

def product_matches_operation(
    product: dict,
    operation: str | None,
) -> bool:

    if not operation:
        return True

    text_parts = [
        product.get("name", ""),
        product.get("brand", ""),
        product.get("category", ""),
        product.get("description", ""),
        product.get("short_description", ""),
        product.get("features", ""),
        product.get("applications", ""),
        product.get("search_text", ""),
    ]

    text = normalize_msg(
        " ".join(
            str(x)
            for x in text_parts
            if x
        )
    )

    keywords = {

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
            "رنده",
            "تراش",
            "turning",
        ],

        "milling": [
            "فرز",
            "فرز انگشتی",
            "milling",
            "end mill",
        ],

        "center_drilling": [
            "مته مرغک",
            "مرغک",
            "center drill",
        ],
    }

    for keyword in keywords.get(operation, []):

        if normalize_msg(keyword) in text:
            return True

    return False


# =========================================================
# CONTACT
# =========================================================

CONTACT_TEXT_FA = """📞 راه‌های تماس با آریا صنعت:

آدرس:
تهران، خیابان امام خمینی، بعد از خیابان ۳۰ تیر، روبروی درمانگاه فرهنگیان، پلاک ۲۹

ساعات کاری:
شنبه تا چهارشنبه ۸ صبح تا ۱۸
پنجشنبه ۸ صبح تا ۱۴

تلفن دفتر فروش: 021-66722504
واتساپ پشتیبانی: 09194654017

سایت: https://microntoolss.ir"""


CONTACT_TEXT_EN = """📞 Contact Arya Sanat:

Address:
Tehran, Imam Khomeini St., after 30 Tir St., opposite Farhangian Clinic, No. 29

Working hours:
Saturday–Wednesday 8:00–18:00
Thursday 8:00–14:00

Sales phone: 021-66722504
WhatsApp support: 09194654017

Website: https://microntoolss.ir"""


# =========================================================
# ABOUT
# =========================================================

ABOUT_TEXT_FA = """شرکت آریا صنعت گنج با بیش از ۴۰ سال سابقه در واردات و فروش ابزارآلات صنعتی فعالیت می‌کند.

• ابزار تراشکاری و قالب‌سازی
• لوازم اندازه‌گیری و کنترل کیفی
• برندهایی مثل D’ANDREA، NAREX، ZPS، ASCUT و ALBERTI

اگر محصول خاصی می‌خواهید، نام یا کاربرد آن را بنویسید تا راهنمایی‌تان کنم."""


ABOUT_TEXT_EN = """Arya Sanat Ganj has over 40 years of experience in importing and selling industrial tools.

• Turning and mold-making tools
• Measuring and quality-control equipment
• Brands such as D’ANDREA, NAREX, ZPS, ASCUT and ALBERTI

Tell me the product or application you need and I will help."""


# =========================================================
# BASIC RESPONSES
# =========================================================

GREETING_TEXT_FA = """سلام، وقت‌تون بخیر 👋

من مشاور هوشمند آریا صنعت هستم.

می‌تونید درباره:
• انتخاب ابزار
• نام محصول
• برند
• کاربرد ابزار
• مشخصات فنی

از من سؤال کنید."""


GREETING_TEXT_EN = """Hello! 👋

I'm the AI consultant of Arya Sanat.

You can ask me about:
• Tool selection
• Products
• Brands
• Applications
• Technical specifications."""


GOODBYE_TEXT_FA = """خداحافظ! 👋
اگر سوالی داشتید، هر وقت خواستید برگردید.
موفق باشید."""


GOODBYE_TEXT_EN = """Goodbye! 👋
Feel free to come back anytime.
Have a great day."""


THANKS_TEXT_FA = """خواهش می‌کنم 🙏
اگر کمک دیگری لازم داشتید، در خدمتم."""


THANKS_TEXT_EN = """You're welcome! 🙏
If you need anything else, I'm here to help."""


# =========================================================
# LANGUAGE
# =========================================================

def is_english(message: str) -> bool:

    m = (message or "").strip()

    if not m:
        return False

    latin = len(
        re.findall(
            r"[a-zA-Z]",
            m,
        )
    )

    persian = len(
        re.findall(
            r"[\u0600-\u06FF]",
            m,
        )
    )

    return latin > persian


# =========================================================
# PRODUCT FORMAT
# =========================================================

def format_product_simple(
    p: dict,
    index: int,
    english: bool = False,
) -> str:

    name = p.get("name") or (
        "Product" if english else "محصول"
    )

    brand = (
        p.get("brand") or ""
    ).replace(
        "برند ",
        "",
    )

    price = (
        p.get("price")
        or p.get("price_text")
        or (
            "Contact us"
            if english
            else "تماس بگیرید"
        )
    )

    url = p.get("url") or ""

    desc = (
        p.get("short_description")
        or p.get("description")
        or ""
    ).strip()

    if desc:

        desc = re.sub(
            r"\s+",
            " ",
            desc,
        )

        if len(desc) > 180:

            desc = (
                desc[:180]
                .rsplit(" ", 1)[0]
                + "..."
            )

    if english:

        lines = [
            f"{index}) {name}",
        ]

        if brand:
            lines.append(
                f"   Brand: {brand}"
            )

        lines.append(
            f"   Price: {price}"
        )

        if desc:
            lines.append(
                f"   {desc}"
            )

        if url:
            lines.append(
                f"   Link: {url}"
            )

    else:

        lines = [
            f"{index}) {name}",
        ]

        if brand:
            lines.append(
                f"   برند: {brand}"
            )

        lines.append(
            f"   قیمت: {price}"
        )

        if desc:
            lines.append(
                f"   {desc}"
            )

        if url:
            lines.append(
                f"   لینک: {url}"
            )

    return "\n".join(lines)


# =========================================================
# BUILD ADVICE
# =========================================================

def build_advice(
    message: str,
    hits: list[dict],
) -> str:

    intent = detect_intent(message)
    operation = detect_operation(message)
    english = is_english(message)

    # -----------------------------------------------------
    # Basic intents
    # -----------------------------------------------------

    if intent == "greeting":
        return (
            GREETING_TEXT_EN
            if english
            else GREETING_TEXT_FA
        )

    if intent == "goodbye":
        return (
            GOODBYE_TEXT_EN
            if english
            else GOODBYE_TEXT_FA
        )

    if intent == "thanks":
        return (
            THANKS_TEXT_EN
            if english
            else THANKS_TEXT_FA
        )

    if intent == "contact":
        return (
            CONTACT_TEXT_EN
            if english
            else CONTACT_TEXT_FA
        )

    if intent == "about":
        return (
            ABOUT_TEXT_EN
            if english
            else ABOUT_TEXT_FA
        )

    # -----------------------------------------------------
    # IMPORTANT:
    # Filter products AGAIN before displaying them.
    # -----------------------------------------------------

    if operation:

        filtered_hits = [
            p
            for p in hits
            if product_matches_operation(
                p,
                operation,
            )
        ]

        hits = filtered_hits

    # -----------------------------------------------------
    # No valid products
    # -----------------------------------------------------

    if not hits:

        if operation == "drilling":

            if english:

                return (
                    "I couldn't find a suitable "
                    "drilling tool in the current "
                    "product data.\n\n"
                    "Please provide the hole diameter "
                    "and workpiece material so I can "
                    "narrow the recommendation."
                )

            return (
                "در اطلاعات فعلی محصولات، "
                "ابزار سوراخکاری مناسبی برای این "
                "کار پیدا نکردم.\n\n"
                "لطفاً قطر سوراخ و جنس قطعه را "
                "هم بگویید تا بتوانم دقیق‌تر "
                "راهنمایی کنم."
            )

        if english:

            return (
                "I couldn't find a relevant product "
                "for this request."
            )

        return (
            "برای این درخواست محصول مرتبطی پیدا نکردم."
        )

    # -----------------------------------------------------
    # Product response
    # -----------------------------------------------------

    if english:

        lines = [
            "Here are the most relevant options:\n"
        ]

        for i, p in enumerate(
            hits[:3],
            1,
        ):

            lines.append(
                format_product_simple(
                    p,
                    i,
                    english=True,
                )
            )

            lines.append("")

        missing = detect_missing_info(message)

        if missing:

            lines.append(
                "For a more precise recommendation, "
                "please also provide:"
            )

            for item in missing:
                lines.append(
                    f"• {item}"
                )

            lines.append("")

        lines.append(
            "For current price and availability:"
        )

        lines.append(
            "Phone: 021-66722504"
        )

        lines.append(
            "WhatsApp: 09194654017"
        )

        return "\n".join(lines)

    # -----------------------------------------------------
    # Persian
    # -----------------------------------------------------

    operation_names = {
        "drilling": "سوراخکاری",
        "tapping": "قلاویزکاری",
        "turning": "تراشکاری",
        "milling": "فرزکاری",
        "center_drilling": "سوراخکاری با مته مرغک",
    }

    if operation in operation_names:

        lines = [
            f"برای {operation_names[operation]}، "
            "این گزینه‌ها از بین محصولات موجود "
            "مرتبط‌تر هستند:\n"
        ]

    else:

        lines = [
            "چند گزینه مرتبط پیدا کردم:\n"
        ]

    for i, p in enumerate(
        hits[:3],
        1,
    ):

        lines.append(
            format_product_simple(
                p,
                i,
                english=False,
            )
        )

        lines.append("")

    missing = detect_missing_info(message)

    if missing:

        lines.append(
            "اگر این اطلاعات را هم بگویید، "
            "دقیق‌تر پیشنهاد می‌دهم:"
        )

        for item in missing:

            lines.append(
                f"• {item}"
            )

        lines.append("")

    lines.append(
        "برای قیمت روز و موجودی:"
    )

    lines.append(
        "تلفن: 021-66722504"
    )

    lines.append(
        "واتساپ: 09194654017"
    )

    return "\n".join(lines)