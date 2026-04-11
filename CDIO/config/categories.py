# config/categories.py
# Chỉ lấy dữ liệu từ DB — không tự cào khi vào trang danh mục

CATEGORIES = {
    "iphone": {
        "label": "iPhone",
        "series": {
            "iphone-17": {
                "label": "iPhone 17 Series",
                "models": [
                    {"label": "iPhone 17 Pro Max", "keyword": "iPhone 17 Pro Max"},
                    {"label": "iPhone 17 Pro",     "keyword": "iPhone 17 Pro"},
                    {"label": "iPhone 17 Plus",    "keyword": "iPhone 17 Plus"},
                    {"label": "iPhone 17",         "keyword": "iPhone 17"},
                ],
            },
            "iphone-16": {
                "label": "iPhone 16 Series",
                "models": [
                    {"label": "iPhone 16 Pro Max", "keyword": "iPhone 16 Pro Max"},
                    {"label": "iPhone 16 Pro",     "keyword": "iPhone 16 Pro"},
                    {"label": "iPhone 16 Plus",    "keyword": "iPhone 16 Plus"},
                    {"label": "iPhone 16",         "keyword": "iPhone 16"},
                ],
            },
            "iphone-15": {
                "label": "iPhone 15 Series",
                "models": [
                    {"label": "iPhone 15 Pro Max", "keyword": "iPhone 15 Pro Max"},
                    {"label": "iPhone 15 Pro",     "keyword": "iPhone 15 Pro"},
                    {"label": "iPhone 15 Plus",    "keyword": "iPhone 15 Plus"},
                    {"label": "iPhone 15",         "keyword": "iPhone 15"},
                ],
            },
            "iphone-14": {
                "label": "iPhone 14 Series",
                "models": [
                    {"label": "iPhone 14 Pro Max", "keyword": "iPhone 14 Pro Max"},
                    {"label": "iPhone 14 Pro",     "keyword": "iPhone 14 Pro"},
                    {"label": "iPhone 14 Plus",    "keyword": "iPhone 14 Plus"},
                    {"label": "iPhone 14",         "keyword": "iPhone 14"},
                ],
            },
        },
    },
    "samsung": {
        "label": "Samsung",
        "series": {
            "samsung-s": {
                "label": "Galaxy S Series",
                "models": [
                    {"label": "Galaxy S25 Ultra", "keyword": "Samsung Galaxy S25 Ultra"},
                    {"label": "Galaxy S25 Plus",  "keyword": "Samsung Galaxy S25 Plus"},
                    {"label": "Galaxy S25",       "keyword": "Samsung Galaxy S25"},
                    {"label": "Galaxy S24 Ultra", "keyword": "Samsung Galaxy S24 Ultra"},
                    {"label": "Galaxy S24 Plus",  "keyword": "Samsung Galaxy S24 Plus"},
                    {"label": "Galaxy S24",       "keyword": "Samsung Galaxy S24"},
                ],
            },
            "samsung-a": {
                "label": "Galaxy A Series",
                "models": [
                    {"label": "Galaxy A56", "keyword": "Samsung Galaxy A56"},
                    {"label": "Galaxy A55", "keyword": "Samsung Galaxy A55"},
                    {"label": "Galaxy A35", "keyword": "Samsung Galaxy A35"},
                    {"label": "Galaxy A15", "keyword": "Samsung Galaxy A15"},
                ],
            },
            "samsung-z": {
                "label": "Galaxy Z Series",
                "models": [
                    {"label": "Galaxy Z Fold 6",  "keyword": "Samsung Galaxy Z Fold 6"},
                    {"label": "Galaxy Z Flip 6",  "keyword": "Samsung Galaxy Z Flip 6"},
                    {"label": "Galaxy Z Fold 5",  "keyword": "Samsung Galaxy Z Fold 5"},
                    {"label": "Galaxy Z Flip 5",  "keyword": "Samsung Galaxy Z Flip 5"},
                ],
            },
        },
    },
}