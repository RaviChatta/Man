"""
Tools/img2pdf.py
Provides functions to download, convert, compress images, and convert them to PDF.
"""

import os
import shutil
import asyncio
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from loguru import logger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import requests
from cloudscraper import create_scraper
import PyPDF2

# Register AVIF/HEIF support
import pillow_avif
import pillow_heif

# -------------------------------
# Download functions
# -------------------------------

def thumbnali_images(image_url, download_dir, quality=80, file_name="thumb.jpg"):
    os.makedirs(download_dir, exist_ok=True)
    response = requests.get(image_url)
    if response.status_code == 200:
        img_path = os.path.join(download_dir, file_name)
        with open(img_path, "wb") as f:
            f.write(response.content)
        return img_path
    return None


async def download_through_cloudscrapper(image_urls, download_dir, quality=80):
    os.makedirs(download_dir, exist_ok=True)
    scraper = create_scraper()
    saved_files = []

    for idx, url in enumerate(image_urls, 1):
        retries = 0
        while retries < 4:
            resp = await asyncio.to_thread(scraper.get, url)
            if resp.status_code == 200:
                path = os.path.join(download_dir, f"{idx}.jpg")
                with open(path, "wb") as f:
                    f.write(resp.content)
                try:
                    with Image.open(path) as img:
                        img.convert("RGB").save(path, "JPEG", quality=quality, optimize=True)
                except Exception as e:
                    logger.exception(f"Error converting image: {e}")
                saved_files.append(path)
                break
            else:
                retries += 1
                await asyncio.sleep(2)
    return saved_files


def download_and_convert_images(images, download_dir, quality=80, target_width=None):
    os.makedirs(download_dir, exist_ok=True)
    saved_files = []

    for idx, url in enumerate(images, 1):
        retries = 0
        while retries < 4:
            resp = requests.get(url)
            if resp.status_code == 200:
                path = os.path.join(download_dir, f"{idx}.jpg")
                with open(path, "wb") as f:
                    f.write(resp.content)
                try:
                    with Image.open(path) as img:
                        img = img.convert("RGB")
                        if target_width:
                            w, h = img.size
                            new_h = int(target_width * h / w)
                            img = img.resize((target_width, new_h), Image.LANCZOS)
                        img.save(path, "JPEG", quality=quality, optimize=True)
                except Exception as e:
                    logger.exception(f"Error converting image: {e}")
                saved_files.append(path)
                break
            else:
                retries += 1
    return saved_files


# -------------------------------
# Compression & PDF functions
# -------------------------------

def compress_image(image_path, output_path, quality=80, target_width=None):
    try:
        img = Image.open(image_path).convert("RGB")
        if target_width:
            w, h = img.size
            new_h = int(target_width * h / w)
            img = img.resize((target_width, new_h), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=quality, optimize=True)
        return output_path
    except Exception as e:
        logger.error(f"Error compressing image {image_path}: {e}")
        return image_path


def convert_images_to_pdf(image_files, pdf_output_path, compressed_dir, password=None, compression_quality=50):
    if not image_files:
        logger.warning("No images to convert.")
        return
    os.makedirs(compressed_dir, exist_ok=True)

    temp_pdf = str(pdf_output_path).replace(".pdf", "_temp.pdf")
    c = canvas.Canvas(temp_pdf, pagesize=letter)

    try:
        target_width = min(Image.open(f).width for f in image_files)
    except:
        target_width = None

    def draw_image(fpath):
        try:
            img = Image.open(fpath)
            w, h = img.size
            new_h = int(target_width * h / w)
            c.setPageSize((target_width, new_h))
            c.drawImage(str(fpath), 0, 0, width=target_width, height=new_h)
            c.showPage()
        except Exception as e:
            logger.error(f"Failed to draw image {fpath}: {e}")

    compressed_images = []
    for img_path in image_files:
        out_path = os.path.join(compressed_dir, os.path.basename(img_path))
        compressed = compress_image(img_path, out_path, quality=compression_quality, target_width=target_width)
        compressed_images.append(compressed)
        draw_image(compressed)

    c.save()

    if password:
        encrypt_pdf(temp_pdf, str(pdf_output_path), password)
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)
    else:
        os.rename(temp_pdf, str(pdf_output_path))

    shutil.rmtree(compressed_dir, ignore_errors=True)
    logger.info(f"PDF created at {pdf_output_path}")


def encrypt_pdf(input_path, output_path, password):
    try:
        with open(input_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            writer = PyPDF2.PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(user_password=password, owner_password=None, use_128bit=True)
            with open(output_path, "wb") as out_f:
                writer.write(out_f)
    except Exception as e:
        logger.error(f"Failed to encrypt PDF: {e}")
