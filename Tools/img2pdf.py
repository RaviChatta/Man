"""
This module provides functions to download, convert, and compress images, and then convert them into a PDF file.

Copy right (c):-  Rahat4089 and VOATcb
Modified:- Dra-Sama
"""

from pathlib import Path
from PIL import Image, UnidentifiedImageError
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
import io
import imghdr

def thumbnali_images(image_url, download_dir, quality=80, file_name="thumb.jpg"):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    image_response = requests.get(image_url)
    if image_response.status_code == 200:
        img_path = os.path.join(download_dir, file_name)
        with open(img_path, 'wb') as img_file:
            img_file.write(image_response.content)
        
        return img_path
    else:
        return None

async def download_through_cloudscrapper(image_urls, download_dir, quality=90):
    scraper = create_scraper()
    
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    images_file = []
    for idx, image_url in enumerate(image_urls, 1):
        retries = 0
        while retries < 3:  # Reduced retries for 404
            try:
                image_response = await to_thread(scraper.get, image_url)
                if image_response.status_code == 200:
                    img_path = os.path.join(download_dir, f"{idx}.jpg")
                    with open(img_path, 'wb') as img_file:
                        img_file.write(image_response.content)
                        try:
                            # Convert any image format to JPEG
                            with Image.open(img_path) as img:
                                # Convert to RGB if necessary
                                if img.mode in ('RGBA', 'LA', 'P'):
                                    img = img.convert("RGB")
                                img.save(img_path, "JPEG", quality=quality, optimize=True)
                                
                        except UnidentifiedImageError:
                            # Try to handle corrupted images
                            logger.warning(f"Corrupted image detected: {img_path}, trying to recover")
                            try:
                                # Try to read the file and check if it's actually an image
                                with open(img_path, 'rb') as f:
                                    content = f.read()
                                    # Check if it has a valid image header
                                    if imghdr.what(None, h=content) is not None:
                                        # Try to force open as JPEG
                                        img = Image.open(io.BytesIO(content))
                                        if img.mode in ('RGBA', 'LA', 'P'):
                                            img = img.convert("RGB")
                                        img.save(img_path, "JPEG", quality=quality, optimize=True)
                                    else:
                                        os.remove(img_path)
                                        logger.warning(f"Invalid image content, skipping: {image_url}")
                                        break
                            except Exception as e:
                                logger.warning(f"Error recovering image {image_url}: {e}")
                                os.remove(img_path)
                                break
                        except Exception as e:
                            logger.warning(f"Error converting image {image_url}: {e}")
                            os.remove(img_path)
                            break
                        
                        images_file.append(img_path)
                        logger.info(f"Successfully downloaded image {idx}/{len(image_urls)}")
                        break
                elif image_response.status_code == 404:
                    logger.warning(f"Image not found (404): {image_url}")
                    break  # Don't retry for 404 errors
                else:
                    logger.warning(f"Download failed for {image_url}: Status {image_response.status_code} (attempt {retries + 1})")
                    retries += 1
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.warning(f"Error downloading {image_url}: {e} (attempt {retries + 1})")
                retries += 1
                await asyncio.sleep(2)
                
    logger.info(f"Downloaded {len(images_file)}/{len(image_urls)} images successfully")
    return images_file

def download_and_convert_images(images, download_dir, quality=80, target_width=None):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    image_files = []
    total_images = len(images)
    
    for idx, image_url in enumerate(images, 1):
        retries = 0
        success = False
        
        while retries < 3 and not success:  # Reduced retries for efficiency
            try:
                image_response = requests.get(image_url, timeout=30)
                if image_response.status_code == 200:
                    img_path = os.path.join(download_dir, f"{idx}.jpg")
                    
                    # Write the image file
                    with open(img_path, 'wb') as img_file:
                        img_file.write(image_response.content)
                        
                    # Validate and convert the image
                    try:
                        with Image.open(img_path) as img:
                            # Convert to RGB if necessary
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert("RGB")
                            img_width, img_height = img.size
                            if target_width:
                                new_height = int((target_width / img_width) * img_height)
                                img = img.resize((target_width, new_height), Image.LANCZOS)
                            img.save(img_path, "JPEG", quality=quality, optimize=True)
                            
                            image_files.append(img_path)
                            success = True
                            logger.info(f"Successfully processed image {idx}/{total_images}")
                            break
                            
                    except UnidentifiedImageError:
                        logger.warning(f"Corrupted image detected: {img_path}")
                        os.remove(img_path)
                        retries += 1
                        continue
                        
                    except Exception as e:
                        logger.warning(f"Error processing image {image_url}: {e}")
                        os.remove(img_path)
                        retries += 1
                        continue
                        
                elif image_response.status_code == 404:
                    logger.warning(f"Image not found (404): {image_url}")
                    break  # Don't retry for 404 errors
                    
                else:
                    logger.warning(f"Download failed for {image_url}: Status {image_response.status_code} (attempt {retries + 1})")
                    retries += 1
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout downloading {image_url} (attempt {retries + 1})")
                retries += 1
                
            except Exception as e:
                logger.warning(f"Error downloading {image_url}: {e} (attempt {retries + 1})")
                retries += 1

    logger.info(f"Successfully downloaded {len(image_files)}/{total_images} images")
    return image_files

def create_placeholder_image(width=800, height=1200, text="Image Not Available", output_path=None):
    """Create a placeholder image for missing pages"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a blank image
        img = Image.new('RGB', (width, height), color='lightgray')
        draw = ImageDraw.Draw(img)
        
        # Try to use a font (this might fail in some environments)
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
            except:
                font = ImageFont.load_default()
        
        # Calculate text position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw the text
        draw.text((x, y), text, fill='darkgray', font=font)
        
        if output_path:
            img.save(output_path, "JPEG", quality=85, optimize=True)
            return output_path
        return img
        
    except Exception as e:
        logger.error(f"Error creating placeholder image: {e}")
        return None

def compress_image(image_path, output_path, quality=80, target_width=None):
    """Compress the image by resizing and reducing its quality."""
    try:
        img = Image.open(image_path).convert("RGB")
        img_width, img_height = img.size

        if target_width:
            new_height = int((target_width / img_width) * img_height)
            img = img.resize((target_width, new_height), Image.LANCZOS)

        img.save(output_path, "JPEG", quality=quality, optimize=True)
        return output_path
    except Exception as e:
        logger.error(f"Error compressing image {image_path}: {e}")
        return image_path

def convert_images_to_pdf(image_files, pdf_output_path, compressed_dir, password=None, compression_quality=85):
    if not image_files:
        logger.warning("No images provided for PDF conversion.")
        # Create a placeholder PDF with error message
        try:
            c = canvas.Canvas(str(pdf_output_path), pagesize=letter)
            c.drawString(100, 700, "No images were available for this chapter.")
            c.drawString(100, 680, "The images may have been removed from the source.")
            c.save()
            return None
        except Exception as e:
            return f"Failed to create PDF: {e}"

    if not os.path.exists(compressed_dir):
        os.makedirs(compressed_dir)
    
    temp_pdf_path = str(pdf_output_path).replace(".pdf", "_temp.pdf")
    
    c = canvas.Canvas(str(temp_pdf_path), pagesize=letter)

    # Calculate target width based on available images
    valid_images = []
    for img_file in image_files:
        if os.path.exists(img_file) and os.path.getsize(img_file) > 0:
            valid_images.append(img_file)
    
    if not valid_images:
        logger.warning("No valid images found for PDF conversion")
        c.drawString(100, 700, "No valid images were available for this chapter.")
        c.save()
        os.rename(temp_pdf_path, str(pdf_output_path))
        return None

    try:
        target_width = min(Image.open(img_file).width for img_file in valid_images)
    except Exception as e:
        logger.warning(f"Error calculating target width: {e}")
        target_width = 800  # Default width

    def draw_image(image_file):
        try:
            if not os.path.exists(image_file) or os.path.getsize(image_file) == 0:
                logger.warning(f"Image file missing or empty: {image_file}")
                # Create placeholder for missing image
                placeholder_path = os.path.join(compressed_dir, f"placeholder_{len(valid_images)}.jpg")
                create_placeholder_image(text=f"Page {len(valid_images)} Not Available", output_path=placeholder_path)
                if os.path.exists(placeholder_path):
                    image_file = placeholder_path
                else:
                    return
            
            img = Image.open(image_file)
            img_width, img_height = img.size
            # Calculate the new height maintaining the aspect ratio
            new_height = int(target_width * img_height / img_width)
            c.setPageSize((target_width, new_height))
            c.drawImage(str(image_file), 0, 0, width=target_width, height=new_height)
            c.showPage()  # Create a new page for each image
        except Exception as e:
            logger.error(f"Failed to process image {image_file}: {e}")
            # Create placeholder for failed image
            try:
                placeholder_path = os.path.join(compressed_dir, f"error_{len(valid_images)}.jpg")
                create_placeholder_image(text=f"Page {len(valid_images)} Error", output_path=placeholder_path)
                if os.path.exists(placeholder_path):
                    img = Image.open(placeholder_path)
                    img_width, img_height = img.size
                    new_height = int(target_width * img_height / img_width)
                    c.setPageSize((target_width, new_height))
                    c.drawImage(str(placeholder_path), 0, 0, width=target_width, height=new_height)
                    c.showPage()
            except Exception as placeholder_error:
                logger.error(f"Failed to create placeholder: {placeholder_error}")

    # Process and compress the images
    compressed_images = []
    for image_file in valid_images:
        compressed_image_path = f"{compressed_dir}/{os.path.basename(image_file)}"
        compressed_image = compress_image(image_file, compressed_image_path, quality=compression_quality, target_width=target_width)
        compressed_images.append(compressed_image)
        draw_image(compressed_image)

    c.save()
    
    if password:
        try:
            encrypt_pdf(temp_pdf_path, str(pdf_output_path), password)
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)  # Remove the temporary unprotected PDF
        except Exception as e:
            logger.error(f"Error encrypting PDF: {e}")
            os.rename(temp_pdf_path, str(pdf_output_path))
    else:
        os.rename(temp_pdf_path, str(pdf_output_path))

    # Clean up
    try:
        shutil.rmtree(compressed_dir, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Error cleaning up compressed directory: {e}")

    logger.info(f"PDF created at {pdf_output_path} with {len(valid_images)} pages")
    return None

def encrypt_pdf(input_path, output_path, password):
    """Encrypt a PDF with a password using PyPDF2"""
    try:
        with open(input_path, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)
            writer = PyPDF2.PdfWriter()

            # Add all pages to the writer
            for page in reader.pages:
                writer.add_page(page)

            # Encrypt the PDF
            writer.encrypt(user_password=password, owner_password=None, 
                          use_128bit=True)

            # Save the encrypted PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

    except Exception as e:
        logger.error(f"Failed to encrypt PDF: {e}")
        # If encryption fails, copy the original file
        shutil.copy2(input_path, output_path)
