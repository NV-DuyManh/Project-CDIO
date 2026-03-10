import os
import uuid
import urllib.parse

from flask import Blueprint, request, jsonify

from services.ai_service import detect_product_from_image
from config.config import UPLOAD_FOLDER, ALLOWED_EXT

upload_bp = Blueprint('upload_bp', __name__)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

@upload_bp.route("/upload-image", methods=["POST"])
def upload_image():
    """Nhận ảnh → Gemini AI nhận diện → trả về keyword để redirect."""

    if 'image' not in request.files:
        return jsonify({'error': 'Không tìm thấy file ảnh.'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'Chưa chọn file.'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'error': 'Định dạng không hỗ trợ. Dùng JPG, PNG hoặc WEBP.'}), 400

    # Lưu file tạm
    ext = file.filename.rsplit('.', 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(save_path)

    # Gọi AI xử lý qua hàm detect_product_from_image
    keyword = detect_product_from_image(save_path)

    # Xóa file tạm sau khi nhận diện xong
    try:
        os.remove(save_path)
    except Exception:
        pass

    if keyword:
        return jsonify({
            'success': True,
            'keyword': keyword,
            'redirect': f'/?keyword={urllib.parse.quote(keyword)}'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Không nhận diện được sản phẩm. Vui lòng thử ảnh khác hoặc nhập tên thủ công.'
        }), 422