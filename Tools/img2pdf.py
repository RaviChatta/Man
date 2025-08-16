"""
Tools/img2pdf.py
Provides robust functions to download, validate, convert, compress images, and convert them to PDF.
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
# Utility functions
# -------------------------------

def validate_image(image_path):
    """Verify image integrity and return dimensions if valid"""
    try:
        with Image.open(image_path) as img:
            img.verify()  # Verify file integrity
            img = Image.open(image_path)  # Must reopen after verify
            if not img.size or 0 in img.size:
                raise ValueError("Invalid image dimensions")
            return img.size
    except (IOError, SyntaxError, ValueError, UnidentifiedImageError) as e:
        logger.error(f"Invalid image {image_path}: {e}")
        if os.path.exists(image_path):
            os.remove(image_path)  # Clean up corrupted file
        return None

def cleanup_directory(dir_path):
    """Safely remove a directory and its contents"""
    try:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error cleaning up directory {dir_path}: {e}")

# -------------------------------
# Download functions
# -------------------------------

def thumbnail_image(image_url, download_dir, quality=80, file_name="thumb.jpg"):
    """Download and create thumbnail from image URL"""
    os.makedirs(download_dir, exist_ok=True)
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            img_path = os.path.join(download_dir, file_name)
            with open(img_path, "wb") as f:
                f.write(response.content)
            if validate_image(img_path):
                return img_path
    except Exception as e:
        logger.error(f"Error downloading thumbnail: {e}")
    return None

async def download_through_cloudscraper(image_urls, download_dir, quality=80):
    """Download images through cloudscraper with validation"""
    os.makedirs(download_dir, exist_ok=True)
    scraper = create_scraper()
    saved_files = []

    for idx, url in enumerate(image_urls, 1):
        retries = 0
        while retries < 4:
            try:
                resp = await asyncio.to_thread(scraper.get, url, timeout=15)
                if resp.status_code == 200:
                    path = os.path.join(download_dir, f"{idx}.jpg")
                    with open(path, "wb") as f:
                        f.write(resp.content)
                    
                    if validate_image(path):
                        try:
                            with Image.open(path) as img:
                                img.convert("RGB").save(path, "JPEG", quality=quality, optimize=True)
                            saved_files.append(path)
                            break
                        except Exception as e:
                            logger.exception(f"Error converting image: {e}")
                    else:
                        logger.warning(f"Downloaded invalid image from {url}")
                retries += 1
            except Exception as e:
                logger.error(f"Download failed for {url} (attempt {retries + 1}): {e}")
                retries += 1
            
            if retries < 4:
                await asyncio.sleep(2 * retries)  # Exponential backoff

    return saved_files

def download_and_convert_images(images, download_dir, quality=80, target_width=None):
    """Download and convert images with optional resizing"""
    os.makedirs(download_dir, exist_ok=True)
    saved_files = []

    for idx, url in enumerate(images, 1):
        retries = 0
        while retries < 4:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    path = os.path.join(download_dir, f"{idx}.jpg")
                    with open(path, "wb") as f:
                        f.write(resp.content)
                    
                    if validate_image(path):
                        try:
                            with Image.open(path) as img:
                                img = img.convert("RGB")
                                if target_width and target_width > 0:
                                    w, h = img.size
                                    new_h = int(target_width * h / w)
                                    if new_h > 0:  # Only resize if valid dimensions
                                        img = img.resize((target_width, new_h), Image.LANCZOS)
                                img.save(path, "JPEG", quality=quality, optimize=True)
                                saved_files.append(path)
                                break
                        except Exception as e:
                            logger.exception(f"Error processing image: {e}")
                    else:
                        logger.warning(f"Downloaded invalid image from {url}")
                retries += 1
            except Exception as e:
                logger.error(f"Download failed for {url}: {e}")
                retries += 1

    return saved_files

# -------------------------------
# Compression & PDF functions
# -------------------------------

def compress_image(image_path, output_path, quality=80, target_width=None):
    """Compress image with optional resizing"""
    try:
        dimensions = validate_image(image_path)
        if not dimensions:
            return None

        img = Image.open(image_path).convert("RGB")
        
        if target_width and target_width > 0:
            w, h = dimensions
            new_h = int(target_width * h / w)
            if new_h <= 0:
                raise ValueError("Invalid target height calculation")
            img = img.resize((target_width, new_h), Image.LANCZOS)
        
        img.save(output_path, "JPEG", quality=quality, optimize=True)
        return output_path
    except Exception as e:
        logger.error(f"Error compressing image {image_path}: {e}")
        return None

def encrypt_pdf(input_path, output_path, password):
    """Encrypt PDF with password protection"""
    try:
        with open(input_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            writer = PyPDF2.PdfWriter()
            
            for page in reader.pages:
                writer.add_page(page)
            
            writer.encrypt(
                user_password=password,
                owner_password=None,
                use_128bit=True
            )
            
            with open(output_path, "wb") as out_f:
                writer.write(out_f)
        return True
    except Exception as e:
        logger.error(f"Failed to encrypt PDF: {e}")
        return False

def convert_images_to_pdf(image_files, pdf_output_path, compressed_dir, password=None, compression_quality=50):
    """Convert multiple images to PDF with optional compression and encryption"""
    if not image_files:
        logger.warning("No images to convert.")
        return False
    
    os.makedirs(compressed_dir, exist_ok=True)
    temp_pdf = str(pdf_output_path).replace(".pdf", "_temp.pdf")
    success = False

    try:
        # Filter and validate images first
        valid_images = [img for img in image_files if validate_image(img)]
        
        if not valid_images:
            logger.error("No valid images found for PDF conversion")
            return False

        # Calculate target width based on valid images
        try:
            target_width = min(Image.open(f).width for f in valid_images)
            if target_width <= 0:
                raise ValueError("Invalid target width calculated")
        except Exception as e:
            logger.error(f"Error calculating target width: {e}")
            target_width = None

        c = canvas.Canvas(temp_pdf, pagesize=letter)
        compressed_images = []
        
        for img_path in valid_images:
            out_path = os.path.join(compressed_dir, os.path.basename(img_path))
            compressed = compress_image(
                img_path, 
                out_path, 
                quality=compression_quality, 
                target_width=target_width
            )
            
            if compressed:
                try:
                    img = Image.open(compressed)
                    w, h = img.size
                    new_h = int(target_width * h / w) if target_width else h
                    c.setPageSize((target_width, new_h))
                    c.drawImage(compressed, 0, 0, width=target_width, height=new_h)
                    c.showPage()
                    compressed_images.append(compressed)
                except Exception as e:
                    logger.error(f"Failed to add image {compressed} to PDF: {e}")

        if not compressed_images:
            logger.error("No images successfully added to PDF")
            return False

        c.save()

        # Handle PDF encryption if needed
        if password:
            if not encrypt_pdf(temp_pdf, str(pdf_output_path), password):
                return False
        else:
            os.rename(temp_pdf, str(pdf_output_path))
        
        success = True
        logger.info(f"PDF successfully created at {pdf_output_path}")

    except Exception as e:
        logger.error(f"Critical error during PDF creation: {e}")
    finally:
        # Cleanup temporary files
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)
        cleanup_directory(compressed_dir)

    return success
