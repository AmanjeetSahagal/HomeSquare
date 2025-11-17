from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from statistics import mean
from urllib.parse import urljoin
import json


# -------------------------------------------------
# Always runs Chrome visibly (head-full)
# -------------------------------------------------
def _build_driver():
    opts = Options()
    # No headless flag → visible browser
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # keeps the Chrome window open after script finishes
    opts.add_experimental_option("detach", True)

    # Selenium Manager picks the correct driver automatically
    return webdriver.Chrome(options=opts)


# -------------------------------------------------
def scrape_listing(url):
    if "redfin.com" in url:
        return scrape_redfin_listing(url)
    elif "zillow.com" in url:
        return scrape_zillow_listing(url)
    else:
        raise ValueError("Unsupported listing site.")


# ---------------- Z I L L O W ---------------------
def scrape_zillow_listing(url):
    driver = _build_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        price_tag = soup.find("span", attrs={"data-testid": "price"})
        price = (
            price_tag.get_text(strip=True)
            if price_tag
            else "N/A"
        )

        beds = baths = sqft = "N/A"
        for div in soup.find_all("div", {"data-testid": "bed-bath-sqft-fact-container"}):
            text = div.get_text(" ", strip=True).lower()
            if "bed" in text:
                beds = text.split()[0]
            elif "bath" in text:
                baths = text.split()[0]
            elif "sqft" in text:
                sqft = text.split()[0].replace(",", "")

        address_tag = soup.find("h1") or soup.find("h2")
        address = (
            re.sub(r"\s+", " ", address_tag.get_text(strip=True))
            if address_tag
            else "N/A"
        )

        zest_tag = soup.find("p", attrs={"data-testid": "primary-zestimate"})
        zestimate = zest_tag.get_text(strip=True) if zest_tag else "N/A"

        df = pd.DataFrame(
            [{
                "Address": address,
                "Price": price,
                "Beds": beds,
                "Baths": baths,
                "Square Footage": sqft,
                "Estimated Price": zestimate,
                "URL": url,
            }]
        )
        return df.to_dict(orient="records")[0]
    finally:
        driver.quit()

def _json_like_to_obj(txt: str):
    """
    Extract the first JSON object from a JS assignment string like:
      window.__REDUX_STATE__ = {...};
    Returns a dict or None.
    """
    if not txt:
        return None
    # Find first '{' and parse until the matching '}' by counting braces
    start = txt.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(txt)):
        if txt[i] == "{":
            depth += 1
        elif txt[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(txt[start:i+1])
                except Exception:
                    return None
    return None

def _collect_redfin_comps_from_state(state: dict, limit: int = 60):
    """
    Walk the Redux/Next data blob and collect items that look like comps.
    We accept objects with numeric price & sqft, and optional beds/baths/address/url.
    Structure on Redfin varies, so we search broadly.
    """
    comps = []
    def walk(node):
        nonlocal comps
        if isinstance(node, dict):
            # Heuristic: looks like a home object
            keys = node.keys()
            if {"price", "sqFt"}.issubset({k.lower() for k in keys}):
                # normalize keys
                lower = {k.lower(): v for k, v in node.items()}
                price = lower.get("price")
                sqft  = lower.get("sqft")
                if isinstance(price, (int, float)) and isinstance(sqft, (int, float)):
                    item = {
                        "price": int(price),
                        "sqft": int(sqft),
                        "beds": lower.get("beds") or lower.get("bedrooms"),
                        "baths": lower.get("baths") or lower.get("bathrooms"),
                        "address": node.get("address") or node.get("formattedAddress"),
                        "detail_url": node.get("url") or node.get("homeUrl"),
                    }
                    comps.append(item)
                    if len(comps) >= limit:
                        return
            # keep walking
            for v in node.values():
                if len(comps) >= limit:
                    break
                walk(v)
        elif isinstance(node, list):
            for v in node:
                if len(comps) >= limit:
                    break
                walk(v)
    try:
        walk(state)
    except Exception:
        pass
    # Basic clean
    out = []
    for c in comps:
        try:
            price = int(c.get("price"))
            sqft  = int(c.get("sqft"))
            if price > 10000 and sqft > 200:
                out.append({
                    "price": price,
                    "sqft": sqft,
                    "beds": (float(c["beds"]) if c.get("beds") is not None else None),
                    "baths": (float(c["baths"]) if c.get("baths") is not None else None),
                    "address": c.get("address"),
                    "detail_url": c.get("detail_url"),
                })
        except Exception:
            continue
    return out[:limit]

# ---------------- R E D F I N ---------------------
def scrape_redfin_listing(url):
    driver = _build_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        with open("debug_redfin_listing.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())

        def get_stat(test_id):
            node = soup.find("div", {"data-rf-test-id": test_id})
            if not node:
                return "N/A"
            val = node.find("span", class_="statsValue") or node.find("div", class_="statsValue")
            return val.get_text(strip=True) if val else "N/A"

        price = get_stat("abp-price")
        beds = get_stat("abp-beds")

        baths_span = soup.find("span", class_="bath-flyout")
        baths = (
            baths_span.get_text(strip=True).replace("ba", "").replace(" ", "")
            if baths_span
            else get_stat("abp-baths")
        )
        sqft = get_stat("abp-sqFt")

        addr_tag = soup.find("header", class_="address")
        address = addr_tag.get_text(strip=True) if addr_tag else "Address Not Found"

        # clean numeric conversions
        def _to_int(x):
            try:
                return int(str(x).replace(",", ""))
            except Exception:
                return None
        def _to_float(x):
            try:
                return float(str(x).replace(",", ""))
            except Exception:
                return None

        beds_i = _to_int(beds)
        baths_i = int(_to_float(baths)) if _to_float(baths) else None
        sqft_i = _to_int(sqft)

        zip_code = None
        m = re.search(r"-(\d{5})/home", url)
        if m:
            zip_code = m.group(1)

        estimate = None
        try:
            estimate = get_redfin_estimate(driver)
        except Exception:
            pass

        avg_price = None
        if zip_code and beds_i and baths_i and sqft_i:
            avg_price = get_average_price_redfin(zip_code, beds_i, baths_i, sqft_i)

        state = None
        for s in soup.find_all("script"):
            txt = (s.string or s.get_text() or "").strip()
            if "__REDUX_STATE__" in txt or "__NEXT_DATA__" in txt:
                state = _json_like_to_obj(txt)
                if state:
                    break
        comps = _collect_redfin_comps_from_state(state or {}, limit=80)

        df = pd.DataFrame(
            [{
                "Address": address,
                "Price": price,
                "Beds": beds,
                "Baths": baths,
                "Square Footage": sqft,
                "Estimated Price": (
                    f"${int(avg_price):,}" if avg_price else (estimate or "N/A")
                ),
                "URL": url,
                "Comps": comps,
            }]
        )
        return df.to_dict(orient="records")[0]
    finally:
        driver.quit()


def get_redfin_estimate(driver, timeout=10):
    p = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "div.RedfinEstimateValueHeader p")
        )
    )
    raw = p.text.strip()
    return int(raw.replace("$", "").replace(",", ""))


def get_average_price_redfin(zip_code, beds, baths, sqft, tol=0.2):
    driver = _build_driver()
    try:
        min_beds, max_beds = max(0, beds - 1), beds + 1
        min_baths, max_baths = max(0, baths - 1), baths + 1
        min_sqft, max_sqft = int(sqft * (1 - tol)), int(sqft * (1 + tol))

        url = (
            f"https://www.redfin.com/zipcode/{zip_code}/filter/"
            f"include=sold-6mo,min-beds={min_beds},max-beds={max_beds},"
            f"min-baths={min_baths},max-baths={max_baths},"
            f"min-sqft={min_sqft},max-sqft={max_sqft}"
        )

        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        prices = []
        for tag in soup.select("span.bp-Homecard__Price--value"):
            try:
                val = int(tag.get_text(strip=True).replace("$", "").replace(",", ""))
                prices.append(val)
            except Exception:
                continue
        if not prices:
            return None
        return round(mean(prices))
    finally:
        driver.quit()
