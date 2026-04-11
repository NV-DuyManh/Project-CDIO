"""
services/email_service.py
=========================
Gửi email HTML thông báo giá giảm qua Gmail SMTP.
Cấu hình qua biến môi trường (.env):
    MAIL_USERNAME=your_gmail@gmail.com
    MAIL_PASSWORD=your_app_password      # Gmail App Password (không phải mật khẩu thường)
    MAIL_FROM_NAME=PriceHunt             # Tuỳ chọn, mặc định "PriceHunt Alert"
"""

import os
import smtplib
import traceback
from email.message import EmailMessage
from email.utils import formataddr


# ════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════

MAIL_USERNAME  = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD  = os.environ.get('MAIL_PASSWORD', '')
MAIL_FROM_NAME = os.environ.get('MAIL_FROM_NAME', 'PriceHunt Alert')
MAIL_SMTP_HOST = 'smtp.gmail.com'
MAIL_SMTP_PORT = 587


# ════════════════════════════════════════════════════════════════════
# EMAIL TEMPLATE
# ════════════════════════════════════════════════════════════════════

def _build_html(product_title: str, new_price: int, target_price: int,
                link: str, keyword: str) -> str:
    """Tạo nội dung email HTML đẹp, dark-themed, inline CSS."""

    price_formatted        = f"{new_price:,}đ".replace(',', '.')
    target_price_formatted = f"{target_price:,}đ".replace(',', '.')
    discount_pct = 0
    if target_price > 0:
        discount_pct = round((target_price - new_price) / target_price * 100, 1)

    discount_line = ''
    if discount_pct > 0:
        discount_line = f'<p style="margin:0;font-size:13px;color:#22c55e;">▼ Thấp hơn {discount_pct}% so với mức giá bạn đặt</p>'

    return f"""<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Thông báo giá từ PriceHunt</title></head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Segoe UI',Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0f;padding:40px 0;">
    <tr><td align="center">

      <!-- Card -->
      <table width="580" cellpadding="0" cellspacing="0"
             style="background:#111118;border:1px solid rgba(255,255,255,0.08);
                    border-radius:16px;overflow:hidden;max-width:100%;">

        <!-- Header gradient bar -->
        <tr>
          <td style="height:4px;background:linear-gradient(90deg,#f5a623,#ff6b35);"></td>
        </tr>

        <!-- Logo row -->
        <tr>
          <td style="padding:28px 36px 0;text-align:left;">
            <table cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:linear-gradient(135deg,#f5a623,#ff6b35);
                            border-radius:8px;width:36px;height:36px;
                            text-align:center;vertical-align:middle;font-size:18px;">⚡</td>
                <td style="padding-left:10px;font-size:18px;font-weight:800;
                            color:#f0f0f5;letter-spacing:-0.02em;">PriceHunt</td>
                <td style="padding-left:8px;">
                  <span style="background:rgba(245,166,35,0.15);color:#f5a623;
                               border:1px solid rgba(245,166,35,0.3);border-radius:4px;
                               font-size:10px;font-weight:700;padding:2px 7px;
                               letter-spacing:0.06em;">ALERT</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Bell icon + headline -->
        <tr>
          <td style="padding:28px 36px 0;text-align:center;">
            <div style="width:72px;height:72px;background:rgba(245,166,35,0.1);
                        border:2px solid rgba(245,166,35,0.3);border-radius:50%;
                        display:inline-flex;align-items:center;justify-content:center;
                        font-size:32px;margin-bottom:16px;">🔔</div>
            <h1 style="margin:0 0 8px;font-size:24px;font-weight:800;color:#f0f0f5;
                        letter-spacing:-0.02em;">Giá đã xuống!</h1>
            <p style="margin:0;color:#8888a0;font-size:15px;line-height:1.5;">
              Sản phẩm bạn đang theo dõi vừa đạt mức giá mong muốn
            </p>
          </td>
        </tr>

        <!-- Product info card -->
        <tr>
          <td style="padding:24px 36px;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#1a1a24;border:1px solid rgba(255,255,255,0.06);
                           border-radius:12px;overflow:hidden;">
              <!-- Product title -->
              <tr>
                <td style="padding:20px 24px 16px;">
                  <p style="margin:0 0 4px;font-size:11px;font-weight:700;
                              text-transform:uppercase;letter-spacing:0.08em;color:#555568;">
                    Sản phẩm
                  </p>
                  <p style="margin:0;font-size:16px;font-weight:600;color:#eeeef5;
                              line-height:1.4;">{product_title}</p>
                </td>
              </tr>
              <!-- Divider -->
              <tr><td style="height:1px;background:rgba(255,255,255,0.06);"></td></tr>
              <!-- Price comparison -->
              <tr>
                <td style="padding:16px 24px;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="width:50%;text-align:center;padding:8px;">
                        <p style="margin:0 0 4px;font-size:11px;font-weight:700;
                                    text-transform:uppercase;letter-spacing:0.08em;
                                    color:#555568;">Mục tiêu của bạn</p>
                        <p style="margin:0;font-size:20px;font-weight:700;
                                    color:#8888a0;text-decoration:line-through;">
                          {target_price_formatted}
                        </p>
                      </td>
                      <td style="width:0;border-left:1px solid rgba(255,255,255,0.06);"></td>
                      <td style="width:50%;text-align:center;padding:8px;">
                        <p style="margin:0 0 4px;font-size:11px;font-weight:700;
                                    text-transform:uppercase;letter-spacing:0.08em;
                                    color:#22c55e;">Giá hiện tại</p>
                        <p style="margin:0;font-size:26px;font-weight:800;color:#f5a623;">
                          {price_formatted}
                        </p>
                        {discount_line}
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- CTA Button -->
        <tr>
          <td style="padding:0 36px 28px;text-align:center;">
            <a href="{link}"
               style="display:inline-block;background:linear-gradient(135deg,#f5a623,#ff6b35);
                       color:#000;text-decoration:none;font-size:15px;font-weight:700;
                       padding:14px 40px;border-radius:99px;
                       box-shadow:0 4px 20px rgba(245,166,35,0.35);
                       letter-spacing:0.01em;">
              Mua ngay trước khi hết →
            </a>
            <p style="margin:14px 0 0;font-size:12px;color:#555568;">
              Từ khóa theo dõi: <strong style="color:#8888a0;">{keyword}</strong>
            </p>
          </td>
        </tr>

        <!-- Divider -->
        <tr><td style="height:1px;background:rgba(255,255,255,0.06);margin:0 36px;"></td></tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 36px;text-align:center;">
            <p style="margin:0 0 6px;font-size:12px;color:#555568;line-height:1.6;">
              Bạn nhận được email này vì đã đặt theo dõi giá trên <strong style="color:#8888a0;">PriceHunt</strong>.<br>
              Thông báo này đã được tắt tự động để tránh spam.
            </p>
            <p style="margin:0;font-size:11px;color:#44445a;">
              © 2025 PriceHunt · So sánh giá thông minh
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""


# ════════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════════

def send_price_alert_email(user_email: str, product_title: str,
                           new_price: int, link: str,
                           keyword: str = '', target_price: int = 0) -> bool:
    """
    Gửi email thông báo giá giảm đến user_email.

    Parameters
    ----------
    user_email    : Email người nhận
    product_title : Tên sản phẩm
    new_price     : Giá hiện tại (int, VND)
    link          : Link sản phẩm trên cửa hàng
    keyword       : Từ khóa đã theo dõi
    target_price  : Mức giá mục tiêu user đặt ra

    Returns
    -------
    True nếu gửi thành công, False nếu lỗi
    """
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print('[Email] Chưa cấu hình MAIL_USERNAME / MAIL_PASSWORD trong .env')
        return False

    if not user_email:
        print('[Email] user_email trống, bỏ qua.')
        return False

    try:
        html_body = _build_html(product_title, new_price, target_price, link, keyword)

        msg = EmailMessage()
        msg['Subject'] = f'🔔 PriceHunt: Giá "{product_title[:40]}" đã xuống {new_price:,}đ!'
        msg['From']    = formataddr((MAIL_FROM_NAME, MAIL_USERNAME))
        msg['To']      = user_email

        # Plain-text fallback
        msg.set_content(
            f'Sản phẩm "{product_title}" bạn đang theo dõi trên PriceHunt '
            f'vừa giảm xuống {new_price:,}đ (mục tiêu: {target_price:,}đ).\n'
            f'Xem ngay: {link}'
        )
        # HTML version
        msg.add_alternative(html_body, subtype='html')

        with smtplib.SMTP(MAIL_SMTP_HOST, MAIL_SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
            smtp.send_message(msg)

        print(f'[Email] ✅ Đã gửi alert tới {user_email} — "{product_title}" @ {new_price:,}đ')
        return True

    except smtplib.SMTPAuthenticationError:
        print('[Email] ❌ Sai MAIL_USERNAME hoặc MAIL_PASSWORD. '
              'Với Gmail hãy dùng App Password (https://myaccount.google.com/apppasswords).')
        return False
    except Exception:
        print(f'[Email] ❌ Lỗi gửi email:\n{traceback.format_exc()}')
        return False