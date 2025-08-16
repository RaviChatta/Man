"""
This module provides functions to download, convert, and compress images, and then convert them into a PDF file.
Enhanced for high-quality output while maintaining original function names.

Copyright (c):- Rahat4089 and VOATcb
Modified:- Dra-Sama
Quality Enhanced by: [Your Name]
"""

from pathlib import Path
from PIL import Image, ImageEnhance, UnidentifiedImageError
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from loguru import logger
import os

import pillow_avif  # This registers AVIF format support with Pillow
import pillow_heif

import requests
import shutil

from cloudscraper import create_scraper
from asyncio import to_thread
import asyncio

import PyPDF2

def thumbnali_images(image_url, download_dir, quality=95, file_name="thumb.jpg"):
    """Download thumbnail image with enhanced quality"""
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    try:
        image_response = requests.get(image_url, stream=True)
        if image_response.status_code == 200:
            img_path = os.path.join(download_dir, file_name)
            
            # Save original first
            with open(img_path, 'wb') as img_file:
                for chunk in image_response.iter_content(1024):
                    img_file.write(chunk)
            
            # Enhance quality
            with Image.open(img_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Apply quality enhancements
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.2)
                
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.1)
                
                img.save(img_path, "JPEG", quality=quality, optimize=True, subsampling=0)
            
            return img_path
    except Exception as e:
        logger.error(f"Error in thumbnali_images: {e}")
    return None

async def download_through_cloudscrapper(image_urls, download_dir, quality=95):
    """Download images through cloudscraper with quality enhancements"""
    scraper = create_scraper()
    
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    images_file = []
    for idx, image_url in enumerate(image_urls, 1):
        retries = 0
        while retries < 4:
            try:
                image_response = await to_thread(scraper.get, image_url, stream=True)
                if image_response.status_code == 200:
                    img_path = os.path.join(download_dir, f"{idx}.jpg")
                    
                    # Save original
                    with open(img_path, 'wb') as img_file:
                        for chunk in image_response.iter_content(1024):
                            img_file.write(chunk)
                    
                    # Enhance quality
                    with Image.open(img_path) as img:
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Quality enhancements
                        enhancer = ImageEnhance.Sharpness(img)
                        img = enhancer.enhance(1.15)
                        
                        img.save(img_path, "JPEG", quality=quality, optimize=True, subsampling=0)
                    
                    images_file.append(img_path)
                    break
                else:
                    logger.error(f"Download failed (attempt {retries + 1}): {image_url}")
                    retries += 1
                    await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Error in download_through_cloudscrapper: {e}")
                retries += 1
                await asyncio.sleep(3)
                
    return images_file

def download_and_convert_images(images, download_dir, quality=95, target_width=None):
    """Download and convert images with quality preservation"""
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    image_files = []
    for idx, image_url in enumerate(images, 1):
        retries = 0
        while retries < 4:
            try:
                image_response = requests.get(image_url, stream=True)
                if image_response.status_code == 200:
                    img_path = os.path.join(download_dir, f"{idx}.jpg")
                    
                    # Save original
                    with open(img_path, 'wb') as img_file:
                        for chunk in image_response.iter_content(1024):
                            img_file.write(chunk)
                    
                    # Process with quality
                    with Image.open(img_path) as img:
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        if target_width:
                            aspect = img.height / img.width
                            new_height = int(target_width * aspect)
                            img = img.resize((target_width, new_height), Image.LANCZOS)
                        
                        # Quality enhancements
                        enhancer = ImageEnhance.Sharpness(img)
                        img = enhancer.enhance(1.1)
                        
                        img.save(img_path, "JPEG", quality=quality, optimize=True, subsampling=0)
                    
                    image_files.append(img_path)
                    break
                else:
                    logger.error(f"Download failed (attempt {retries + 1}): {image_url}")
                    retries += 1
            except Exception as e:
                logger.error(f"Error in download_and_convert_images: {e}")
                retries += 1

    return image_files

def compress_image(image_path, output_path, quality=90, target_width=None):
    """Compress image while preserving quality"""
    try:
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            if target_width:
                aspect = img.height / img.width
                new_height = int(target_width * aspect)
                img = img.resize((target_width, new_height), Image.LANCZOS)
            
            # Apply subtle quality enhancements
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.05)
            
            img.save(output_path, "JPEG", quality=quality, optimize=True, subsampling=0)
            return output_path
    except Exception as e:
        logger.error(f"Error in compress_image: {e}")
        return image_path

def convert_images_to_pdf(image_files, pdf_output_path, compressed_dir, password=None, compression_quality=90):
    """Convert images to PDF with high quality output"""
    if not image_files:
        logger.warning("No images provided for PDF conversion.")
        return "No images provided for PDF conversion."

    if not os.path.exists(compressed_dir):
        os.makedirs(compressed_dir)
    
    temp_pdf_path = str(pdf_output_path).replace(".pdf", "_temp.pdf")
    
    # Create high-quality PDF canvas
    c = canvas.Canvas(temp_pdf_path, pagesize=letter, enforceColorSpace='RGB')
    c.setPageCompression(0)  # Disable compression for quality
    
    # Process images with quality preservation
    for image_file in image_files:
        try:
            with Image.open(image_file) as img:
                # Maintain original aspect ratio
                img_width, img_height = img.size
                aspect = img_height / img_width
                
                # Use full page width while maintaining aspect
                page_width = letter[0] - 40  # Add margins
                new_height = page_width * aspect
                
                # Center on page
                y_position = (letter[1] - new_height) / 2 if new_height < letter[1] else 0
                
                # Draw high-quality image
                c.drawImage(image_file, 20, y_position, width=page_width, height=new_height,
                          preserveAspectRatio=True, mask='auto')
                c.showPage()
        except Exception as e:
            logger.error(f"Failed to process image {image_file}: {e}")
            continue
    
    c.save()
    
    # Handle encryption if needed
    if password:
        encrypt_pdf(temp_pdf_path, str(pdf_output_path), password)
        os.remove(temp_pdf_path)
    else:
        os.rename(temp_pdf_path, str(pdf_output_path))
    
    # Cleanup
    shutil.rmtree(compressed_dir, ignore_errors=True)
    
    logger.success(f"High-quality PDF created at {pdf_output_path}")
    return None

def encrypt_pdf(input_path, output_path, password):
    """Encrypt PDF without quality loss"""
    try:
        with open(input_path, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)
            writer = PyPDF2.PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            writer.encrypt(user_password=password, owner_password=None, 
                          use_128bit=True, encrypt_metadata=True)
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

    except Exception as e:
        logger.error(f"Failed to encrypt PDF: {e}")
        raise
