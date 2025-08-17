"""
This module provides functions to download, convert, and compress images, and then convert them into a PDF file.

Copyright (c): Rahat4089 and VOATcb
Modified: Dra-Sama
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union
from PIL import Image, UnidentifiedImageError
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from loguru import logger
import os
import pillow_avif  # Registers AVIF format support
import pillow_heif
import requests
import shutil
from cloudscraper import create_scraper
from asyncio import to_thread
import asyncio
import PyPDF2

async def download_through_cloudscrapper(
    image_urls: List[str],
    download_dir: Union[str, Path],
    quality: int = 80
) -> List[Path]:
    """
    Download images through cloudflare protection with retry logic.
    
    Args:
        image_urls: List of image URLs to download
        download_dir: Directory to save downloaded images
        quality: JPEG quality (1-100)
    
    Returns:
        List of Path objects to downloaded images
    """
    scraper = create_scraper()
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)
    
    images_files: List[Path] = []
    
    for idx, image_url in enumerate(image_urls, 1):
        retries = 0
        while retries < 4:
            try:
                response = await to_thread(scraper.get, image_url)
                if response.status_code == 200:
                    img_path = download_path / f"{idx}.jpg"
                    img_path.write_bytes(response.content)
                    
                    try:
                        with Image.open(img_path) as img:
                            img = img.convert("RGB")
                            img.save(img_path, "JPEG", quality=quality, optimize=True)
                            images_files.append(img_path)
                            break
                    except Exception as e:
                        logger.error(f"Error processing {image_url}: {e}")
                        retries += 1
                else:
                    logger.warning(f"Download failed (attempt {retries}): {image_url}")
                    retries += 1
            except Exception as e:
                logger.error(f"Error downloading {image_url}: {e}")
                retries += 1
            
            await asyncio.sleep(3)
                
    return images_files

def download_and_convert_images(
    image_urls: List[str],
    download_dir: Union[str, Path],
    quality: int = 80,
    target_width: Optional[int] = None
) -> List[Path]:
    """
    Download and convert images with optional resizing.
    
    Args:
        image_urls: List of image URLs to download
        download_dir: Directory to save downloaded images  
        quality: JPEG quality (1-100)
        target_width: Optional width to resize images to
        
    Returns:
        List of Path objects to downloaded images
    """
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)
    image_files: List[Path] = []

    for idx, image_url in enumerate(image_urls, 1):
        retries = 0
        while retries < 4:
            try:
                response = requests.get(image_url)
                if response.status_code == 200:
                    img_path = download_path / f"{idx}.jpg"
                    img_path.write_bytes(response.content)
                    
                    with Image.open(img_path) as img:
                        img = img.convert("RGB")
                        if target_width:
                            width_percent = target_width / float(img.size[0])
                            new_height = int(float(img.size[1]) * float(width_percent))
                            img = img.resize((target_width, new_height), Image.LANCZOS)
                        img.save(img_path, "JPEG", quality=quality, optimize=True)
                        image_files.append(img_path)
                        break
                else:
                    logger.warning(f"Download failed (attempt {retries}): {image_url}")
                    retries += 1
            except Exception as e:
                logger.error(f"Error processing {image_url}: {e}")
                retries += 1

    return image_files

def compress_image(
    image_path: Union[str, Path],
    output_path: Union[str, Path],
    quality: int = 80,
    target_width: Optional[int] = None
) -> Path:
    """
    Compress an image with optional resizing.
    
    Args:
        image_path: Path to source image
        output_path: Path to save compressed image
        quality: JPEG quality (1-100)
        target_width: Optional width to resize to
        
    Returns:
        Path to compressed image
    """
    image_path = Path(image_path)
    output_path = Path(output_path)
    
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            if target_width:
                width_percent = target_width / float(img.size[0])
                new_height = int(float(img.size[1]) * float(width_percent))
                img = img.resize((target_width, new_height), Image.LANCZOS)
            img.save(output_path, "JPEG", quality=quality, optimize=True)
            return output_path
    except Exception as e:
        logger.error(f"Error compressing {image_path}: {e}")
        return image_path

def convert_images_to_pdf(
    image_files: List[Union[str, Path]],
    pdf_output_path: Union[str, Path],
    compressed_dir: Union[str, Path],
    password: Optional[str] = None,
    compression_quality: int = 100
) -> Optional[str]:
    """
    Convert images to PDF with optional password protection.
    
    Args:
        image_files: List of image paths to include
        pdf_output_path: Output PDF path
        compressed_dir: Temporary directory for compressed images
        password: Optional PDF password
        compression_quality: Image quality (1-100)
        
    Returns:
        Error message if failed, None if successful
    """
    if not image_files:
        return "No images provided for PDF conversion"

    pdf_path = Path(pdf_output_path)
    compressed_path = Path(compressed_dir)
    compressed_path.mkdir(parents=True, exist_ok=True)
    
    temp_pdf = pdf_path.with_stem(f"{pdf_path.stem}_temp")
    
    # Calculate target width from smallest image
    try:
        target_width = min(Image.open(img).width for img in image_files)
    except Exception as e:
        logger.warning(f"Couldn't determine target width: {e}")
        target_width = None

    # Create PDF canvas
    c = canvas.Canvas(str(temp_pdf), pagesize=letter)
    
    # Process and add each image
    compressed_images: List[Path] = []
    for img_file in image_files:
        img_path = Path(img_file)
        compressed_img = compressed_path / img_path.name
        compress_image(img_path, compressed_img, compression_quality, target_width)
        compressed_images.append(compressed_img)
        
        try:
            with Image.open(compressed_img) as img:
                img_width, img_height = img.size
                if target_width:
                    new_height = int(target_width * img_height / img_width)
                    c.setPageSize((target_width, new_height))
                c.drawImage(str(compressed_img), 0, 0, width=target_width, height=new_height)
                c.showPage()
        except Exception as e:
            logger.error(f"Failed to process {img_file}: {e}")

    c.save()
    
    # Handle password protection
    if password:
        if not encrypt_pdf(temp_pdf, pdf_path, password):
            return "Failed to encrypt PDF"
        temp_pdf.unlink(missing_ok=True)
    else:
        temp_pdf.rename(pdf_path)
    
    # Cleanup
    shutil.rmtree(compressed_path, ignore_errors=True)
    logger.success(f"PDF created at {pdf_path}")
    return None

def encrypt_pdf(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    password: str
) -> bool:
    """
    Encrypt a PDF with password protection.
    
    Args:
        input_path: Source PDF path
        output_path: Encrypted PDF path
        password: Encryption password
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with Path(input_path).open('rb') as f:
            reader = PyPDF2.PdfReader(f)
            writer = PyPDF2.PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            writer.encrypt(
                user_password=password,
                owner_password=None,
                use_128bit=True
            )

            with Path(output_path).open('wb') as out:
                writer.write(out)
                
        return True
    except Exception as e:
        logger.error(f"PDF encryption failed: {e}")
        return False
