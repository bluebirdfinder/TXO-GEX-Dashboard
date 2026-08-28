"""
Bluebird Finder Social QR Code Generator
=============================================================================================
Generates HD QR Codes for Instagram & Threads with brand styling and ID tags.
Target URLs:
  - Instagram: https://www.instagram.com/bluebird_finder/
  - Threads:   https://www.threads.com/@bluebird_finder
"""

import os
import sys
import qrcode
from PIL import Image, ImageDraw, ImageFont

# Enable UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def create_styled_qr(url, platform_name, handle_id, output_path, primary_color="#00d2ff"):
    """
    Creates a styled QR code image card with crisp scanning contrast and handle ID label.
    """
    # 1. Generate QR Code matrix
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # 2. Make base QR image (black modules on white background for 100% scanner compatibility)
    qr_img = qr.make_image(fill_color="#0f172a", back_color="#ffffff").convert("RGBA")
    qr_w, qr_h = qr_img.size

    # Card dimensions
    card_w = qr_w + 32
    card_h = qr_h + 60  # Extra space for bottom ID label

    # Create canvas
    card = Image.new("RGBA", (card_w, card_h), (15, 23, 42, 255)) # Dark slate background #0f172a
    draw = ImageDraw.Draw(card)

    # Draw rounded border & background for QR area
    qr_box = (16, 16, 16 + qr_w, 16 + qr_h)
    
    # Create white rounded card for the QR code itself
    white_bg = Image.new("RGBA", (qr_w, qr_h), (255, 255, 255, 255))
    card.paste(white_bg, (16, 16))
    card.paste(qr_img, (16, 16), qr_img)

    # Draw outer border around QR
    draw.rectangle([14, 14, 18 + qr_w, 18 + qr_h], outline=primary_color, width=2)

    # Text formatting for ID Label under QR code
    font_size = 16
    try:
        # Try loading a system sans-serif font
        font = ImageFont.truetype("arial.ttf", font_size)
        font_bold = ImageFont.truetype("arialbd.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
        font_bold = font

    # Platform tag & ID line
    label_text = f"{platform_name}: {handle_id}"
    
    # Calculate text position to center it horizontally under the QR code
    bbox = draw.textbbox((0, 0), label_text, font=font_bold)
    text_w = bbox[2] - bbox[0]
    text_x = (card_w - text_w) // 2
    text_y = 16 + qr_h + 12

    # Draw background pill for label
    pill_padding = 8
    pill_box = (text_x - pill_padding, text_y - 2, text_x + text_w + pill_padding, text_y + 20)
    draw.rounded_rectangle(pill_box, radius=6, fill=(30, 41, 59, 255), outline=primary_color, width=1)

    # Draw label text
    draw.text((text_x, text_y), label_text, fill=(255, 255, 255, 255), font=font_bold)

    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    card.save(output_path, "PNG")
    print(f"[OK] Saved QR Code: {output_path} (URL: {url}, ID: {handle_id})")

def generate_all_qr_codes():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(root_dir, "assets")
    
    ig_url = "https://www.instagram.com/bluebird_finder/"
    threads_url = "https://www.threads.com/@bluebird_finder"
    handle_id = "@bluebird_finder"

    ig_path = os.path.join(assets_dir, "qr_instagram.png")
    threads_path = os.path.join(assets_dir, "qr_threads.png")

    # Generate Instagram QR (#e1306c / #00d2ff)
    create_styled_qr(ig_url, "IG", handle_id, ig_path, primary_color="#e1306c")

    # Generate Threads QR (#00f2fe / #ffffff)
    create_styled_qr(threads_url, "Threads", handle_id, threads_path, primary_color="#00f2fe")

if __name__ == "__main__":
    generate_all_qr_codes()
