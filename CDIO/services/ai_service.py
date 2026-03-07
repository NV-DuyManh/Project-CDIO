import re
import pathlib
import base64
import time
import os

from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


def detect_product_from_image(image_path):
    """
    Gửi ảnh lên Groq Vision (llama-4-scout), trả về keyword sản phẩm.
    Free, không bị block ở Việt Nam.
    """
    if not GROQ_AVAILABLE:
        print("[AI] Chưa cài groq. Chạy: pip install groq")
        return None

    if not GROQ_API_KEY:
        print("[AI] Chưa set GROQ_API_KEY trong file .env")
        return None

    # Đọc và encode ảnh base64
    ext = str(image_path).rsplit('.', 1)[-1].lower()
    mime_map = {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'png': 'image/png',  'webp': 'image/webp',
        'gif': 'image/gif'
    }
    mime_type = mime_map.get(ext, 'image/jpeg')
    image_b64 = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode('utf-8')

    prompt = (
        "Look at this product image carefully. "
        "Identify the product brand and model. "
        "Return ONLY a short search keyword (2-5 words, lowercase, no punctuation). "
        "Examples: 'iphone 15 pro', 'samsung galaxy s24', 'macbook air m3'. "
        "Return ONLY the keyword. Nothing else."
    )

    for attempt in range(3):
        try:
            client   = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type":      "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                max_tokens=50
            )

            keyword = response.choices[0].message.content.strip().lower()
            keyword = re.sub(r'["\'.\n\r]', '', keyword).strip()
            keyword = re.sub(r'\s+', ' ', keyword)

            if keyword and len(keyword) >= 2:
                print(f"[AI Groq] Nhận diện: '{keyword}'")
                return keyword

            return None

        except Exception as e:
            print(f"[AI Groq] Lần {attempt + 1}/3 lỗi: {e}")
            if attempt < 2:
                print("[AI Groq] Thử lại sau 2 giây...")
                time.sleep(2)

    print("[AI Groq] Thất bại sau 3 lần thử.")
    return None
