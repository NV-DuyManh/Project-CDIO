import time
import urllib.parse
from selenium.webdriver.common.by import By

from scrapers.base_scraper import get_chrome_driver
from utils.price_parser import parse_price, sanitize_product
from config.config import SCRAPE_MAX_PRODUCTS, SCRAPE_WAIT_SECONDS


def scrape_clickbuy(keyword):
    """
    Cào dữ liệu sản phẩm từ Clickbuy.
    Trả về list các dict sản phẩm đã được sanitize.
    """
    driver = get_chrome_driver()
    data   = []
    try:
        url = f"https://clickbuy.com.vn/tim-kiem?key={urllib.parse.quote(keyword)}"
        driver.get(url)
        time.sleep(SCRAPE_WAIT_SECONDS)

        products = driver.find_elements(By.CSS_SELECTOR, ".list-products__item ")
        for product in products[:SCRAPE_MAX_PRODUCTS]:
            try:
                title     = product.find_element(By.CSS_SELECTOR, ".title_name").text
                price_str = product.find_element(By.CSS_SELECTOR, ".new-price").text
                img       = product.find_element(By.CSS_SELECTOR, ".lazyload").get_attribute("src")
                link      = product.find_element(By.TAG_NAME, "a").get_attribute("href")
                item      = sanitize_product({
                    "site":      "Clickbuy",
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
