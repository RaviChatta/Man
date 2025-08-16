from pathlib import Path
from PIL import Image, UnidentifiedImageError
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from loguru import logger
import os
import shutil
import requests
from cloudscraper import create_scraper
from asyncio import to_thread
import asyncio
import PyPDF2

import pillow_avif  # register AVIF
import pillow_heif  # register HEIF


async def download_images_cloudscraper(image_urls, download_dir, quality=80):
    scraper = create_scraper()
    os.makedirs(download_dir, exist_ok=True)
    downloaded = []

    for idx, url in enumerate(image_urls, 1):
        retries = 0
        while retries < 3:
            try:
                resp = await to_thread(scraper.get, url)
                if resp.status_code == 200:
                    img_path = os.path.join(download_dir, f"{idx}.jpg")
                    with open(img_path, "wb") as f:
                        f.write(resp.content)
                    # Verify image can open
                    try:
                        with Image.open(img_path) as img:
                            img = img.convert("RGB")
                            img.save(img_path, "JPEG", quality=quality, optimize=True)
                        downloaded.append(img_path)
                        break
                    except UnidentifiedImageError:
                        logger.error(f"Skipped invalid image: {url}")
                        os.remove(img_path)
                        break
                else:
                    retries += 1
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                retries += 1
    return downloaded


def compress_image(image_path, output_path, quality=80, target_width=None):
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            if target_width:
                w, h = img.size
                new_h = int((target_width / w) * h)
                img = img.resize((target_width, new_h), Image.LANCZOS)
            img.save(output_path, "JPEG", quality=quality, optimize=True)
        return output_path
    except Exception as e:
        logger.error(f"Failed compressing {image_path}: {e}")
        return None  # Skip invalid image


def convert_images_to_pdf(image_files, pdf_output_path, compressed_dir, password=None, compression_quality=50):
    if not image_files:
        logger.warning("No valid images to convert.")
        return

    os.makedirs(compressed_dir, exist_ok=True)
    temp_pdf = str(pdf_output_path).replace(".pdf", "_temp.pdf")
    c = canvas.Canvas(temp_pdf, pagesize=letter)

    # Target width
    try:
        target_width = min(Image.open(f).width for f in image_files)
    except Exception:
        target_width = None

    for img_file in image_files:
        compressed_img = os.path.join(compressed_dir, os.path.basename(img_file))
        compressed_img = compress_image(img_file, compressed_img, compression_quality, target_width)
        if not compressed_img:
            continue
        try:
            with Image.open(compressed_img) as img:
                w, h = img.size
                h_new = int(target_width * h / w) if target_width else h
                c.setPageSize((target_width, h_new) if target_width else (w, h))
                c.drawImage(compressed_img, 0, 0, width=target_width or w, height=h_new)
                c.showPage()
        except Exception as e:
            logger.error(f"Skipping image in PDF: {img_file} -> {e}")

    c.save()

    if password:
        encrypt_pdf(temp_pdf, str(pdf_output_path), password)
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
