import time
import urllib.parse
from selenium.webdriver.common.by import By

from scrapers.base_scraper import get_chrome_driver
from utils.price_parser import parse_price, sanitize_product
from config.config import SCRAPE_MAX_PRODUCTS, SCRAPE_WAIT_SECONDS


def scrape_cellphones(keyword):
    """
    Cào dữ liệu sản phẩm từ CellphoneS.
    Trả về list các dict sản phẩm đã được sanitize.
    """
    driver = get_chrome_driver()
    data   = []
    try:
        url = f"https://cellphones.com.vn/catalogsearch/result?q={urllib.parse.quote(keyword)}"
        driver.get(url)
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(SCRAPE_WAIT_SECONDS)

        products = driver.find_elements(By.CSS_SELECTOR, ".product-item")
        for product in products[:SCRAPE_MAX_PRODUCTS]:
            try:
                title     = product.find_element(By.CSS_SELECTOR, ".product__name").text
                price_str = product.find_element(By.CSS_SELECTOR, ".product__price--show").text
                link      = product.find_element(By.TAG_NAME, "a").get_attribute("href")
                img_el    = product.find_element(By.CSS_SELECTOR, ".product__image img")
                img       = img_el.get_attribute("src")
                if not img or "base64" in img:
                    img = img_el.get_attribute("data-src")
                item = sanitize_product({
                    "site":      "CellphoneS",
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
