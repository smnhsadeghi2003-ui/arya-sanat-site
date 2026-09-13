import re


def normalize_msg(message: str) -> str:
    m = (message or "").strip().lower()
    for a, b in [("ي", "ی"), ("ك", "ک"), ("\u200c", " ")]:
        m = m.replace(a, b)
    return re.sub(r"\s+", " ", m)


def detect_intent(message: str) -> str:
    m = normalize_msg(message)

    greetings = [
        "سلام", "درود", "صبح بخیر", "عصر بخیر", "شب بخیر",
        "hello", "hi", "hey", "خوبی", "چطوری", "وقت بخیر",
    ]
    if any(g in m for g in greetings) and len(m) < 40:
        if len(m.split()) <= 4:
            return "greeting"

    contact_words = [
        "تماس", "آدرس", "شماره", "تلفن", "واتساپ", "واتsapp",
        "ایمیل", "محل", "کجا هستید", "چطور تماس", "پشتیبانی",
        "ساعت کاری", "ساعات کار", "راه ارتباطی",
    ]
    if any(c in m for c in contact_words):
        return "contact"

    about_words = [
        "درباره", "شرکت", "آریا صنعت", "نمایندگی", "برندها",
        "شما کیستید", "چیکار میکنید",
    ]
    if any(a in m for a in about_words) and not any(
        x in m for x in ["مته", "قلاویز", "کولت", "ساعت"]
    ):
        return "about"

    return "product"


def detect_missing_info(message: str) -> list[str]:
    m = normalize_msg(message)
    missing = []
    if any(x in m for x in ["سوراخ", "دریل", "مته", "drill"]):
        if not any(
            x in m
            for x in ["فولاد", "استیل", "آلومینیوم", "چدن", "برنج", "مس", "ماده", "جنس"]
        ):
            missing.append("جنس قطعه (مثلاً فولاد یا آلومینیوم)")
        if not re.search(r"\d+(?:\.\d+)?\s*(?:میلی.?متر|mm|میل)", m):
            if "سوراخ" in m or "قطر" in m:
                missing.append("قطر سوراخ (میلی‌متر)")
    return missing


CONTACT_TEXT = """📞 راه‌های تماس با آریا صنعت:

آدرس:
تهران، خیابان امام خمینی، بعد از خیابان ۳۰ تیر، روبروی درمانگاه فرهنگیان، پلاک ۲۹

ساعات کاری:
شنبه تا چهارشنبه ۸ صبح تا ۱۸
پنجشنبه ۸ صبح تا ۱۴

تلفن دفتر فروش: 021-66722504
واتساپ پشتیبانی: 09194654017

سایت: https://arya-sanat.com"""


ABOUT_TEXT = """شرکت آریا صنعت گنج با بیش از ۴۰ سال سابقه در واردات و فروش ابزارآلات صنعتی کار می‌کند:

• ابزار تراشکاری و قالب‌سازی
• لوازم اندازه‌گیری و کنترل کیفی
• نمایندگی برندهایی مثل D’ANDREA، NAREX، ZPS، ASCUT، ALBERTI و ...

شعار ما: کیفیت برتر با ابزار دقیق‌تر

اگر محصول خاصی می‌خواهید، نامش را بنویسید تا راهنمایی‌تان کنم."""


GREETING_TEXT = """سلام، وقت‌تون بخیر 👋
من مشاور هوشمند آریا صنعت هستم.

می‌تونید بپرسید:
• نام محصول یا برند (مثلاً قلاویز NAREX)
• تماس و آدرس
• پیشنهاد ابزار برای کارتان

چطور می‌تونم کمکتون کنم؟"""


def format_product_simple(p: dict, index: int) -> str:
    name = p.get("name") or "محصول"
    brand = (p.get("brand") or "").replace("برند ", "")
    price = p.get("price") or p.get("price_text") or "تماس بگیرید"
    url = p.get("url") or ""
    desc = (p.get("short_description") or p.get("description") or "").strip()
    if desc:
        desc = re.sub(r"\s+", " ", desc)
        if len(desc) > 120:
            desc = desc[:120].rsplit(" ", 1)[0] + "..."
    else:
        desc = ""

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

    if intent == "greeting":
        return GREETING_TEXT

    if intent == "contact":
        return CONTACT_TEXT

    if intent == "about":
        return ABOUT_TEXT

    if not hits:
        return (
            "برای این مورد محصول مرتبطی پیدا نکردم.\n\n"
            "لطفاً یکی از این‌ها را واضح‌تر بنویسید:\n"
            "• نام محصول (مثلاً قلاویز لوله)\n"
            "• برند (مثلاً NAREX یا ZPS)\n"
            "• یا بگویید تماس با ما\n\n"
            f"{CONTACT_TEXT}"
        )

    lines = ["چند گزینه مرتبط پیدا کردم:\n"]
    for i, p in enumerate(hits[:3], 1):
        lines.append(format_product_simple(p, i))
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