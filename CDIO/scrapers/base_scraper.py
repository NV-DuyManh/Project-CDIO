from selenium import webdriver

def get_chrome_driver():
    """Tạo Chrome driver headless dùng chung cho tất cả scrapers."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    )
    
    # Bỏ hoàn toàn webdriver_manager, để Selenium tự động lo việc khớp phiên bản
    return webdriver.Chrome(options=options)