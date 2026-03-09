import time
import urllib.parse
from selenium.webdriver.common.by import By

from scrapers.base_scraper import get_chrome_driver
from utils.price_parser import parse_price, sanitize_product
from config.config import SCRAPE_MAX_PRODUCTS, SCRAPE_WAIT_SECONDS


def scrape_smartviets(keyword):
    driver = get_chrome_driver()
    data   = []
    try:
        url = f"https://smartviets.com/?s={urllib.parse.quote(keyword)}"
        driver.get(url)
        time.sleep(SCRAPE_WAIT_SECONDS)

        products = driver.find_elements(By.CSS_SELECTOR, ".product-small")
        for product in products[:SCRAPE_MAX_PRODUCTS]:
            try:
                a_tag = product.find_element(By.TAG_NAME, "a")
                link  = a_tag.get_attribute("href")

                try:
                    title = product.find_element(By.CSS_SELECTOR, ".title-wrapper").text
                except Exception:
                    title = a_tag.get_attribute("title")

                try:
                    img_tag = product.find_element(By.TAG_NAME, "img")
                    img = img_tag.get_attribute("data-src") or img_tag.get_attribute("src")
                except Exception:
                    img = ""

                try:
                    price_str = product.find_element(By.CSS_SELECTOR, ".price-wrapper").text
                    # Bỏ giá cũ bị gạch chéo nếu có
                    if price_str and '\n' in price_str:
                        price_str = price_str.split('\n')[0]
                    elif price_str and ' ' in price_str:
                        price_str = price_str.split()[0]
                except Exception:
                    price_str = ""

                item = sanitize_product({
                    "site":      "Smart Việt",
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