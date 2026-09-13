import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "products.json"
OUTPUT = ROOT / "data" / "products_full.json"
ERRORS = ROOT / "data" / "crawl_errors.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}

# کلمات کمکی برای پیدا کردن بخش‌های فارسی صفحه
DESC_WORDS = ["توضیحات", "معرفی", "شرح"]
FEATURE_WORDS = ["ویژگی", "ویژگی های", "ویژگی‌های", "مشخصات", "مشخصات فنی"]
ADV_WORDS = ["مزایا", "مزیت"]
APP_WORDS = ["کاربرد", "موارد استفاده", "موارد کاربرد"]

def clean(text):
    if not text:
        return ""
    text = str(text)
    text = text.replace("\xa0", " ")
    text = text.replace("\u200c", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()

def norm(text):
    return clean(text).replace("ي", "ی").replace("ك", "ک").lower()

def unique(items):
    result = []
    seen = set()
    for x in items:
        x = clean(x)
        if x and x not in seen:
            result.append(x)
            seen.add(x)
    return result

def text_of(node):
    return clean(node.get_text(" ", strip=True)) if node else ""

def find_heading_blocks(soup, keywords):
    """
    بخش‌هایی را پیدا می‌کند که heading/title آن‌ها شامل یکی از keywordهاست.
    به class وابسته نیست؛ برای قالب فعلی آریا صنعت مقاوم‌تر است.
    """
    blocks = []

    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"])

    for heading in headings:
        title = text_of(heading)
        nt = norm(title)

        if not title or not any(norm(k) in nt for k in keywords):
            continue

        pieces = []

        # حالت 1: محتوای بعد از heading تا heading بعدی
        for sib in heading.next_siblings:
            if getattr(sib, "name", None) in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                break
            if getattr(sib, "get_text", None):
                t = text_of(sib)
                if t:
                    pieces.append(t)

        # اگر sibling جواب نداد، والد را امتحان کن
        if not pieces and heading.parent:
            parent_text = text_of(heading.parent)
            if parent_text:
                parent_text = parent_text.replace(title, "", 1).strip()
                if parent_text:
                    pieces.append(parent_text)

        if pieces:
            blocks.append({
                "title": title,
                "text": clean("\n".join(pieces))
            })

    return blocks

def extract_lists_from_blocks(blocks):
    result = []
    for block in blocks:
        # متن heading + محتوا را نگه می‌داریم
        result.append(block["text"])
    return unique(result)

def extract_tables(soup):
    tables = []

    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            values = [text_of(c) for c in cells]
            values = [v for v in values if v]
            if values:
                rows.append(values)

        if rows:
            tables.append(rows)

    return tables

def tables_to_dict(tables):
    specs = {}

    for table in tables:
        for row in table:
            if len(row) >= 2:
                key = row[0]
                value = " | ".join(row[1:])
                if key and value:
                    specs[key] = value

    return specs

def extract_attributes(soup):
    """
    چند مدل جدول/ویژگی را پشتیبانی می‌کند:
    WooCommerce، جدول‌های ساده و tableهای سفارشی.
    """
    attrs = {}

    selectors = [
        "table.shop_attributes tr",
        ".woocommerce-product-attributes tr",
        ".product-attributes tr",
        ".product-specifications tr",
        ".specifications tr",
    ]

    rows = []
    for selector in selectors:
        rows.extend(soup.select(selector))

    for row in rows:
        cells = row.find_all(["th", "td"])
        vals = [text_of(x) for x in cells]
        vals = [x for x in vals if x]

        if len(vals) >= 2:
            attrs[vals[0]] = " | ".join(vals[1:])

    # اگر selectorهای بالا چیزی پیدا نکردند، تمام tableها را بررسی می‌کنیم.
    if not attrs:
        attrs = tables_to_dict(extract_tables(soup))

    return attrs

def find_main_content(soup):
    selectors = [
        ".single-product",
        ".product",
        "main",
        "#main",
        ".site-main",
        ".content-area",
        "article",
    ]

    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            return node

    return soup

def extract_product(html, url, fallback=None):
    soup = BeautifulSoup(html, "lxml")
    main = find_main_content(soup)

    # ---------- عنوان ----------
    title_node = (
        soup.select_one("h1.product_title")
        or soup.select_one("h1.entry-title")
        or soup.select_one("h1")
    )
    name = text_of(title_node)

    if not name and fallback:
        name = fallback.get("name", "")

    # ---------- قیمت ----------
    price_node = (
        soup.select_one(".price")
        or soup.select_one(".dina-product-price")
        or soup.select_one("[class*='price']")
    )
    price = text_of(price_node)
    if not price and fallback:
        price = fallback.get("price", "")

    # ---------- توضیح کوتاه ----------
    short_node = soup.select_one(
        ".woocommerce-product-details__short-description"
    )
    short_description = text_of(short_node)

    # ---------- بخش‌های صفحه ----------
    desc_blocks = find_heading_blocks(soup, DESC_WORDS)
    feature_blocks = find_heading_blocks(soup, FEATURE_WORDS)
    advantage_blocks = find_heading_blocks(soup, ADV_WORDS)
    application_blocks = find_heading_blocks(soup, APP_WORDS)

    # ---------- توضیحات استاندارد WooCommerce ----------
    standard_desc = soup.select_one(
        "#tab-description, .woocommerce-Tabs-panel--description"
    )
    description = text_of(standard_desc)

    # اگر تب توضیحات وجود داشت، آن را هم اضافه می‌کنیم.
    desc_parts = []
    if description:
        desc_parts.append(description)
    desc_parts.extend(extract_lists_from_blocks(desc_blocks))
    description = "\n\n".join(unique(desc_parts))

    # ---------- ویژگی‌ها ----------
    feature_text = extract_lists_from_blocks(feature_blocks)

    # ---------- مزایا ----------
    advantages = extract_lists_from_blocks(advantage_blocks)

    # ---------- کاربرد ----------
    applications = extract_lists_from_blocks(application_blocks)

    # ---------- جدول مشخصات ----------
    tables = extract_tables(main)
    technical_specs = tables_to_dict(tables)

    # ---------- ویژگی‌های WooCommerce ----------
    attributes = extract_attributes(main)

    # ادغام
    for k, v in technical_specs.items():
        attributes.setdefault(k, v)

    # ---------- SKU ----------
    sku_node = soup.select_one(".sku")
    sku = text_of(sku_node)

    # ---------- دسته ----------
    category_nodes = soup.select(
        ".posted_in a, .product_meta .posted_in a, "
        ".breadcrumb a"
    )
    categories = unique([text_of(x) for x in category_nodes])

    # ---------- برند ----------
    brand = ""
    for selector in [
        ".brand a",
        ".product-brand a",
        "[class*='brand'] a",
        "a[rel='tag']",
    ]:
        node = soup.select_one(selector)
        if node:
            brand = text_of(node)
            if brand:
                break

    # ---------- تصویر اصلی ----------
    image = ""
    for selector in [
        ".woocommerce-product-gallery__image img",
        ".product-image img",
        ".product img",
    ]:
        node = soup.select_one(selector)
        if node:
            image = (
                node.get("data-src")
                or node.get("data-lazy-src")
                or node.get("src")
                or ""
            )
            if image:
                image = urljoin(url, image)
                break

    # ---------- همه متن مهم ----------
    important_text = "\n\n".join(unique([
        name,
        short_description,
        description,
        "\n".join(feature_text),
        "\n".join(advantages),
        "\n".join(applications),
        "\n".join(f"{k}: {v}" for k, v in attributes.items()),
    ]))

    return {
        "name": name,
        "brand": brand,
        "sku": sku,
        "price": price,
        "category": " | ".join(categories),
        "short_description": short_description,
        "description": description,
        "features": feature_text,
        "advantages": advantages,
        "applications": applications,
        "attributes": attributes,
        "technical_specs": technical_specs,
        "image": image,
        "url": url,
        "search_text": important_text,
    }

def main():
    products = json.loads(INPUT.read_text(encoding="utf-8"))

    session = requests.Session()
    session.headers.update(HEADERS)

    results = []
    errors = []

    total = len(products)

    for i, old_product in enumerate(products, 1):
        url = old_product.get("url", "").strip()

        print(f"\n[{i}/{total}]")
        print(url)

        if not url:
            errors.append({
                "index": i,
                "error": "URL خالی است"
            })
            continue

        try:
            response = session.get(url, timeout=40)
            response.raise_for_status()

            item = extract_product(
                response.text,
                response.url,
                fallback=old_product
            )

            # اگر سایت اطلاعاتی را پیدا نکرد، داده قدیمی را از دست ندهیم.
            if not item["name"]:
                item["name"] = old_product.get("name", "")

            if not item["price"]:
                item["price"] = old_product.get("price", "")

            results.append(item)

            print("  OK:", item["name"])
            print("  features:", len(item["features"]))
            print("  advantages:", len(item["advantages"]))
            print("  applications:", len(item["applications"]))
            print("  attributes:", len(item["attributes"]))
            print("  description chars:", len(item["description"]))

        except Exception as e:
            print("  ERROR:", repr(e))
            errors.append({
                "index": i,
                "url": url,
                "name": old_product.get("name", ""),
                "error": str(e),
            })

            # محصول را حذف نکن
            results.append({
                **old_product,
                "brand": "",
                "sku": "",
                "category": "",
                "short_description": "",
                "description": "",
                "features": [],
                "advantages": [],
                "applications": [],
                "attributes": {},
                "technical_specs": {},
                "image": "",
                "search_text": old_product.get("name", ""),
            })

        time.sleep(0.7)

    OUTPUT.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    ERRORS.write_text(
        json.dumps(errors, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n==============================")
    print("FINISHED")
    print("Products:", len(results))
    print("Errors:", len(errors))
    print("Output:", OUTPUT)
    print("Errors file:", ERRORS)
    print("==============================")

if __name__ == "__main__":
    main()
