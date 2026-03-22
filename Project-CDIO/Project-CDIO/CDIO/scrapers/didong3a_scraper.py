import time
import urllib.parse
from selenium.webdriver.common.by import By

from scrapers.base_scraper import get_chrome_driver
from utils.price_parser import parse_price, sanitize_product
from config.config import SCRAPE_MAX_PRODUCTS, SCRAPE_WAIT_SECONDS


def scrape_didong3a(keyword):
    driver = get_chrome_driver()
    data   = []
    try:
        url = f"https://didong3a.vn/search?query={urllib.parse.quote(keyword)}"
        driver.get(url)
        time.sleep(SCRAPE_WAIT_SECONDS + 1)

        products = driver.find_elements(By.CSS_SELECTOR, ".news-item-products")
        for product in products[:SCRAPE_MAX_PRODUCTS]:
            try:
                a_tag = product.find_element(By.TAG_NAME, "a")
                link  = a_tag.get_attribute("href")
                title = a_tag.get_attribute("title")

                try:
                    img_tag = product.find_element(By.TAG_NAME, "img")
                    img = img_tag.get_attribute("data-src") or img_tag.get_attribute("src")
                except Exception:
                    img = ""

                try:
                    price_str = product.find_element(By.CSS_SELECTOR, ".price strong").text
                    if not price_str:
                        price_str = product.find_element(By.CSS_SELECTOR, ".price").text.split()[0]
                except Exception:
                    price_str = ""

                item = sanitize_product({
                    "site":      "Di Động 3A",
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