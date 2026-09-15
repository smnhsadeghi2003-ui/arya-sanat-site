import re


def normalize_msg(message: str) -> str:
    m = (message or "").strip().lower()
    for a, b in [("ي", "ی"), ("ك", "ک"), ("\u200c", " ")]:
        m = m.replace(a, b)
    return re.sub(r"\s+", " ", m)


def detect_intent(message: str) -> str:
    m = normalize_msg(message)
    words = m.split()

    # --- Greeting ---
    greetings = [
        "سلام", "درود", "صبح بخیر", "عصر بخیر", "شب بخیر", "وقت بخیر",
        "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
        "خوبی", "چطوری", "چطورید", "حالت چطوره",
    ]
    if any(g in m for g in greetings) and len(words) <= 6:
        return "greeting"

    # --- Goodbye ---
    goodbyes = [
        "خداحافظ", "خدانگهدار", "بای", "bye", "goodbye", "see you",
        "خدا نگهدار", "فعلا", "فعلاً", "شب خوش", "خداحافظی",
        "take care", "see ya", "later",
    ]
    if any(g in m for g in goodbyes) and len(words) <= 6:
        return "goodbye"

    # --- Thanks ---
    thanks = [
        "ممنون", "متشکرم", "مرسی", "تشکر", "خیلی ممنون",
        "thanks", "thank you", "thx", "ty",
    ]
    if any(t in m for t in thanks) and len(words) <= 5:
        return "thanks"

    # --- Contact ---
    contact_words = [
        "تماس", "آدرس", "شماره", "تلفن", "واتساپ", "واتsapp", "whatsapp",
        "ایمیل", "محل", "کجا هستید", "چطور تماس", "پشتیبانی",
        "ساعت کاری", "ساعات کار", "راه ارتباطی", "contact", "address",
        "phone", "call", "location", "where are you",
    ]
    if any(c in m for c in contact_words):
        return "contact"

    # --- About ---
    about_words = [
        "درباره", "شرکت", "آریا صنعت", "نمایندگی", "برندها",
        "شما کیستید", "چیکار میکنید", "about", "who are you",
        "what do you do", "company",
    ]
    if any(a in m for a in about_words) and not any(
        x in m for x in ["مته", "قلاویز", "کولت", "ساعت", "drill", "tap"]
    ):
        return "about"

    return "product"


def detect_missing_info(message: str) -> list[str]:
    m = normalize_msg(message)
    missing = []
    if any(x in m for x in ["سوراخ", "دریل", "مته", "drill"]):
        if not any(
            x in m
            for x in ["فولاد", "استیل", "آلومینیوم", "چدن", "برنج", "مس", "ماده", "جنس", "steel", "aluminum"]
        ):
            missing.append("جنس قطعه (مثلاً فولاد یا آلومینیوم)")
        if not re.search(r"\d+(?:\.\d+)?\s*(?:میلی.?متر|mm|میل)", m):
            if "سوراخ" in m or "قطر" in m or "diameter" in m:
                missing.append("قطر سوراخ (میلی‌متر)")
    return missing


CONTACT_TEXT_FA = """📞 راه‌های تماس با آریا صنعت:

آدرس:
تهران، خیابان امام خمینی، بعد از خیابان ۳۰ تیر، روبروی درمانگاه فرهنگیان، پلاک ۲۹

ساعات کاری:
شنبه تا چهارشنبه ۸ صبح تا ۱۸
پنجشنبه ۸ صبح تا ۱۴

تلفن دفتر فروش: 021-66722504
واتساپ پشتیبانی: 09194654017

سایت: https://arya-sanat.com"""

CONTACT_TEXT_EN = """📞 Contact Arya Sanat:

Address:
Tehran, Imam Khomeini St., after 30 Tir St., opposite Farhangian Clinic, No. 29

Working hours:
Saturday–Wednesday 8:00–18:00
Thursday 8:00–14:00

Sales phone: 021-66722504
WhatsApp support: 09194654017

Website: https://arya-sanat.com"""

ABOUT_TEXT_FA = """شرکت آریا صنعت گنج با بیش از ۴۰ سال سابقه در واردات و فروش ابزارآلات صنعتی کار می‌کند:

• ابزار تراشکاری و قالب‌سازی
• لوازم اندازه‌گیری و کنترل کیفی
• نمایندگی برندهایی مثل D’ANDREA، NAREX، ZPS، ASCUT، ALBERTI و ...

شعار ما: کیفیت برتر با ابزار دقیق‌تر

اگر محصول خاصی می‌خواهید، نامش را بنویسید تا راهنمایی‌تان کنم."""

ABOUT_TEXT_EN = """Arya Sanat Ganj has over 40 years of experience in importing and selling industrial tools:

• Turning and mold-making tools
• Measuring instruments and quality control equipment
• Exclusive representative of brands such as D’ANDREA, NAREX, ZPS, ASCUT, ALBERTI and more

Our motto: Superior quality with more precise tools

If you need a specific product, just tell me its name and I’ll help you."""

GREETING_TEXT_FA = """سلام، وقت‌تون بخیر 👋
من مشاور هوشمند آریا صنعت هستم.

می‌تونید بپرسید:
• نام محصول یا برند (مثلاً قلاویز NAREX)
• تماس و آدرس
• پیشنهاد ابزار برای کارتان

چطور می‌تونم کمکتون کنم؟"""

GREETING_TEXT_EN = """Hello! 👋
I'm the AI consultant of Arya Sanat.

You can ask me about:
• Product or brand name (e.g. NAREX taps)
• Contact information and address
• Tool recommendations for your work

How can I help you today?"""

GOODBYE_TEXT_FA = """خداحافظ! 👋
اگر سوالی داشتید، هر وقت خواستید برگردید.
موفق باشید."""

GOODBYE_TEXT_EN = """Goodbye! 👋
Feel free to come back anytime if you have questions.
Have a great day!"""

THANKS_TEXT_FA = """خواهش می‌کنم 🙏
اگر کمک دیگه‌ای لازم داشتید، در خدمتم."""

THANKS_TEXT_EN = """You're welcome! 🙏
If you need anything else, I'm here to help."""


def is_english(message: str) -> bool:
    """تشخیص تقریبی اینکه پیام عمدتاً انگلیسی است یا نه"""
    m = (message or "").strip()
    if not m:
        return False
    # اگر بیشتر حروف لاتین باشد
    latin = len(re.findall(r"[a-zA-Z]", m))
    persian = len(re.findall(r"[\u0600-\u06FF]", m))
    return latin > persian


def format_product_simple(p: dict, index: int, english: bool = False) -> str:
    name = p.get("name") or ("Product" if english else "محصول")
    brand = (p.get("brand") or "").replace("برند ", "")
    price = p.get("price") or p.get("price_text") or ("Contact us" if english else "تماس بگیرید")
    url = p.get("url") or ""
    desc = (p.get("short_description") or p.get("description") or "").strip()
    if desc:
        desc = re.sub(r"\s+", " ", desc)
        if len(desc) > 120:
            desc = desc[:120].rsplit(" ", 1)[0] + "..."
    else:
        desc = ""

    if english:
        lines = [f"{index}) {name}"]
        if brand:
            lines.append(f"   Brand: {brand}")
        lines.append(f"   Price: {price}")
        if desc:
            lines.append(f"   {desc}")
        if url:
            lines.append(f"   Link: {url}")
    else:
        lines = [f"{index}) {name}"]
        if brand:
            lines.append(f"   برند: {brand}")
        lines.append(f"   قیمت: {price}")
        if desc:
            lines.append(f"   {desc}")
        if url:
            lines.append(f"   لینک: {url}")
    return "\n".join(lines)


def build_advice(message: str, hits: list[dict]) -> str:
    intent = detect_intent(message)
    english = is_english(message)

    if intent == "greeting":
        return GREETING_TEXT_EN if english else GREETING_TEXT_FA

    if intent == "goodbye":
        return GOODBYE_TEXT_EN if english else GOODBYE_TEXT_FA

    if intent == "thanks":
        return THANKS_TEXT_EN if english else THANKS_TEXT_FA

    if intent == "contact":
        return CONTACT_TEXT_EN if english else CONTACT_TEXT_FA

    if intent == "about":
        return ABOUT_TEXT_EN if english else ABOUT_TEXT_FA

    if not hits:
        if english:
            return (
                "I couldn't find a relevant product for this.\n\n"
                "Please try one of these:\n"
                "• Product name (e.g. pipe tap)\n"
                "• Brand (e.g. NAREX or ZPS)\n"
                "• Or ask for contact information\n\n"
                f"{CONTACT_TEXT_EN}"
            )
        return (
            "برای این مورد محصول مرتبطی پیدا نکردم.\n\n"
            "لطفاً یکی از این‌ها را واضح‌تر بنویسید:\n"
            "• نام محصول (مثلاً قلاویز لوله)\n"
            "• برند (مثلاً NAREX یا ZPS)\n"
            "• یا بگویید تماس با ما\n\n"
            f"{CONTACT_TEXT_FA}"
        )

    if english:
        lines = ["Here are some relevant options:\n"]
        for i, p in enumerate(hits[:3], 1):
            lines.append(format_product_simple(p, i, english=True))
            lines.append("")
        missing = detect_missing_info(message)
        if missing:
            lines.append("If you also tell me these, I can give a more precise recommendation:")
            for m in missing:
                lines.append(f"• {m}")
            lines.append("")
        lines.append("For current price and availability:")
        lines.append("Phone: 021-66722504")
        lines.append("WhatsApp: 09194654017")
        return "\n".join(lines)

    lines = ["چند گزینه مرتبط پیدا کردم:\n"]
    for i, p in enumerate(hits[:3], 1):
        lines.append(format_product_simple(p, i, english=False))
        lines.append("")

    missing = detect_missing_info(message)
    if missing:
        lines.append("اگر این‌ها را هم بگویید دقیق‌تر پیشنهاد می‌دهم:")
        for m in missing:
            lines.append(f"• {m}")
        lines.append("")

    lines.append("برای قیمت روز و موجودی:")
    lines.append("تلفن: 021-66722504")
    lines.append("واتساپ: 09194654017")
    return "\n".join(lines)
