import time
import urllib.parse
from selenium.webdriver.common.by import By

from scrapers.base_scraper import get_chrome_driver
from utils.price_parser import parse_price, sanitize_product
from config.config import SCRAPE_MAX_PRODUCTS, SCRAPE_WAIT_SECONDS


def scrape_bachlong(keyword):
    driver = get_chrome_driver()
    data   = []
    try:
        url = f"https://bachlongstore.vn/san-pham/search/?keyword={urllib.parse.quote(keyword)}"
        driver.get(url)
        time.sleep(SCRAPE_WAIT_SECONDS)

        products = driver.find_elements(By.CSS_SELECTOR, ".itproductmm")
        for product in products[:SCRAPE_MAX_PRODUCTS]:
            try:
                title = product.find_element(By.CSS_SELECTOR, ".dstitle h3").text

                a_tag = product.find_element(By.CSS_SELECTOR, ".mmthumb a")
                link  = a_tag.get_attribute("href")

                try:
                    img_tag = product.find_element(By.TAG_NAME, "img")
                    img = img_tag.get_attribute("data-src") or img_tag.get_attribute("src")
                except Exception:
                    img = ""

                try:
                    price_str = product.find_element(By.CSS_SELECTOR, ".pnews").text
                except Exception:
                    price_str = ""

                item = sanitize_product({
                    "site":      "Bạch Long Store",
                    "title":     title,
                    "price_str": price_str,
                    "raw_price": parse_price(price_str),
                    "img":       img,
                    "link":      link
                })
                if item:
                    data.append(item)
            except Exception:
                continue
    except Exception:
        pass
    finally:
        driver.quit()
    return data