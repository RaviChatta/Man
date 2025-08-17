"""
Tools for downloading, processing images and converting to PDF
"""

from pathlib import Path
from typing import List, Optional, Union
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import PyPDF2
import requests
import shutil
from cloudscraper import create_scraper
from asyncio import to_thread
import asyncio
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Register additional image formats
import pillow_avif
import pillow_heif

async def download_through_cloudscrapper(
    image_urls: List[str],
    download_dir: Union[str, Path],
    quality: int = 80
) -> List[Path]:
    """Download images while bypassing cloudflare protection"""
    scraper = create_scraper()
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)
    
    results: List[Path] = []
    
    for idx, url in enumerate(image_urls, 1):
        for attempt in range(3):
            try:
                response = await to_thread(scraper.get, url)
                if response.status_code == 200:
                    img_path = download_path / f"{idx}.jpg"
                    img_path.write_bytes(response.content)
                    
                    # Convert and optimize the image
                    with Image.open(img_path) as img:
                        img = img.convert("RGB")
                        img.save(img_path, "JPEG", quality=quality, optimize=True)
                    
                    results.append(img_path)
                    break
                else:
                    logger.warning(f"Attempt {attempt + 1} failed for {url}")
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
            await asyncio.sleep(2)
    
    return results

def download_and_convert_images(
    image_urls: List[str],
    download_dir: Union[str, Path],
    quality: int = 80,
    target_width: Optional[int] = None
) -> List[Path]:
    """Download and process images with optional resizing"""
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)
    results: List[Path] = []

    for idx, url in enumerate(image_urls, 1):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            img_path = download_path / f"{idx}.jpg"
            img_path.write_bytes(response.content)
            
            with Image.open(img_path) as img:
                img = img.convert("RGB")
                if target_width:
                    ratio = target_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((target_width, new_height), Image.LANCZOS)
                img.save(img_path, "JPEG", quality=quality, optimize=True)
            
            results.append(img_path)
        except Exception as e:
            logger.error(f"Failed to process {url}: {e}")
    
    return results

def thumbnali_images(
    image_url: str,
    download_dir: Union[str, Path],
    quality: int = 80,
    file_name: str = "thumb.jpg"
) -> Optional[Path]:
    """Download and create a thumbnail image"""
    try:
        download_path = Path(download_dir)
        download_path.mkdir(parents=True, exist_ok=True)
        
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        img_path = download_path / file_name
        img_path.write_bytes(response.content)
        
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            img.save(img_path, "JPEG", quality=quality, optimize=True)
        
        return img_path
    except Exception as e:
        logger.error(f"Thumbnail creation failed: {e}")
        return None

def convert_images_to_pdf(
    image_files: List[Union[str, Path]],
    pdf_output_path: Union[str, Path],
    compressed_dir: Union[str, Path],
    password: Optional[str] = None,
    quality: int = 90
) -> Optional[str]:
    """Convert images to PDF with optional encryption"""
    if not image_files:
        return "No images provided"
    
    pdf_path = Path(pdf_output_path)
    temp_pdf = pdf_path.with_name(f"temp_{pdf_path.name}")
    compressed_path = Path(compressed_dir)
    compressed_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create PDF
        c = canvas.Canvas(str(temp_pdf), pagesize=letter)
        
        for img_file in image_files:
            img_path = Path(img_file)
            compressed_img = compressed_path / img_path.name
            
            # Compress image
            with Image.open(img_path) as img:
                img = img.convert("RGB")
                img.save(compressed_img, "JPEG", quality=quality, optimize=True)
            
            # Add to PDF
            with Image.open(compressed_img) as img:
                width, height = img.size
                c.setPageSize((width, height))
                c.drawImage(str(compressed_img), 0, 0, width=width, height=height)
                c.showPage()
        
        c.save()
        
        # Encrypt if password provided
        if password:
            if not _encrypt_pdf(temp_pdf, pdf_path, password):
                return "PDF encryption failed"
            temp_pdf.unlink(missing_ok=True)
        else:
            temp_pdf.rename(pdf_path)
        
        return None
    
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        return str(e)
    finally:
        shutil.rmtree(compressed_path, ignore_errors=True)

def _encrypt_pdf(
    input_path: Path,
    output_path: Path,
    password: str
) -> bool:
    """Internal function to encrypt a PDF file"""
    try:
        with input_path.open('rb') as f_in, output_path.open('wb') as f_out:
            reader = PyPDF2.PdfReader(f_in)
            writer = PyPDF2.PdfWriter()
            
            for page in reader.pages:
                writer.add_page(page)
            
            writer.encrypt(
                user_password=password,
                owner_password=None,
                use_128bit=True
            )
            writer.write(f_out)
        
        return True
    except Exception as e:
        logger.error(f"PDF encryption error: {e}")
        return False
