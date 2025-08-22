from .scraper import Scraper
import json 
from bs4 import BeautifulSoup
from loguru import logger
import re
import aiohttp
from PIL import Image
import io
import imghdr


class ToonilyScraper(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://toonily.com"
        self.bg = None
        self.sf = "tn"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://toonily.com/",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        self.search_query = dict()
    
    async def get_information(self, slug, data):
        url = f"{self.url}/webtoon/{slug}/"
        response = await self.get(url, cs=True, headers=self.headers)
        soup = BeautifulSoup(response, "html.parser")
        
        # Remove any overlays/popups that might block content
        for overlay in soup.find_all(["div", "section"], class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['popup', 'overlay', 'modal', 'discord', 'advertisement'])):
            overlay.decompose()
        
        # Extract title
        title_element = soup.find("h1", class_="entry-title")
        title = title_element.text.strip() if title_element else "N/A"
        
        # Extract cover image
        cover_element = soup.find("div", class_="summary_image")
        if cover_element:
            img_element = cover_element.find("img")
            cover = img_element["src"] if img_element else "N/A"
        else:
            cover = "N/A"
        
        # Extract description
        desc_element = soup.find("div", class_="summary__content")
        desc = desc_element.text.strip() if desc_element else "N/A"
        
        # Extract genres
        genres = "N/A"
        genres_element = soup.find("div", class_="genres-content")
        if genres_element:
            genres_elements = genres_element.find_all("a")
            genres_list = [genre.text.strip() for genre in genres_elements]
            genres = ", ".join(genres_list) or "N/A"
        
        # Extract status
        status = "N/A"
        for div in soup.find_all("div", class_="summary-content"):
            if "Status" in div.text:
                status_div = div.find_next_sibling("div")
                if status_div:
                    status = status_div.text.strip()
                break
        
        # Extract authors
        authors = "N/A"
        for div in soup.find_all("div", class_="author-content"):
            authors = div.text.strip()
            break
        
        # Extract rating
        rating_element = soup.find("span", class_="score")
        rating = rating_element.text.strip() if rating_element else "N/A"
        
        # Extract last chapter
        last_chap = "N/A"
        chapter_elements = soup.find_all("li", class_="wp-manga-chapter")
        if chapter_elements:
            last_chap_element = chapter_elements[0].find("a")
            last_chap = last_chap_element.text.strip() if last_chap_element else "N/A"
        
        # Construct message
        msg = f"<b>{title}</b>\n\n"
        msg += f"<b>Rating:</b> <code>{rating}</code>\n"
        msg += f"<b>Genres:</b> <code>{genres}</code>\n"
        msg += f"<b>Last Chapter:</b> <code>{last_chap}</code>\n"
        msg += f"<b>Status:</b> <code>{status}</code>\n"
        msg += f"<b>Authors:</b> <code>{authors}</code>\n"

        # Add description if it fits
        if len(desc) + len(msg) < 1024:
            msg += f"\n<i>{desc}</i>"
        else:
            msg += f"\n<b><a href='{url}'>Read more...</a></b>"

        if len(msg) > 1024:
            msg = msg[:1021] + "..."  # Truncate with ellipsis
        
        data['msg'] = msg
        data['poster'] = cover
        data['url'] = url
      
    async def search(self, query: str = ""):
        if query.lower() in self.search_query:
            return self.search_query[query.lower()]
        
        url = f"{self.url}/?s={query}&post_type=wp-manga"
        response = await self.get(url, cs=True, headers=self.headers)
        soup = BeautifulSoup(response, "html.parser")
        
        mangas = []
        results = soup.find_all("div", class_="page-item-detail")
        
        for result in results:
            title_element = result.find("h3").find("a")
            if not title_element:
                continue
                
            title = title_element.text.strip()
            url = title_element["href"]
            slug_match = re.search(r'/webtoon/([^/]+)/', url)
            slug = slug_match.group(1) if slug_match else url.split("/")[-2]
            
            image_element = result.find("img")
            poster = image_element["src"] if image_element else "N/A"
            
            mangas.append({
                "title": title,
                "slug": slug,
                "url": url,
                "poster": poster
            })
        
        self.search_query[query.lower()] = mangas
        return mangas
    
    async def get_chapters(self, data, page: int = 1):
        url = data['url']  # Use the manga URL directly
        response = await self.get(url, cs=True, headers=self.headers)
        soup = BeautifulSoup(response, "html.parser")
        
        # Remove overlays
        for overlay in soup.find_all(["div", "section"], class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['popup', 'overlay', 'modal', 'discord', 'advertisement'])):
            overlay.decompose()
        
        chapters = soup.find_all("li", class_="wp-manga-chapter")
        
        results = {
            "chapters": [],
            "title": data["title"],
            "slug": data["slug"],
            "url": data["url"]
        }
        
        for chapter in chapters:
            chapter_link = chapter.find("a")
            if not chapter_link:
                continue
                
            chapter_title = chapter_link.text.strip()
            chapter_url = chapter_link["href"]
            chapter_slug_match = re.search(r'/chapter-(\d+)/', chapter_url)
            chapter_slug = chapter_slug_match.group(1) if chapter_slug_match else chapter_url.split("/")[-2]
            
            results["chapters"].append({
                "title": chapter_title,
                "url": chapter_url,
                "slug": chapter_slug,
                "chap": chapter_slug  # Add chap field for consistency
            })
        
        await self.get_information(data['slug'], results)
        return results
  
    def iter_chapters(self, data):
        if not data or 'chapters' not in data:
            return []
        
        chapters_list = []
        for chapter in data['chapters']:
            chapters_list.append({
                "title": chapter["title"],
                "url": chapter["url"],
                "slug": chapter["slug"],
                "manga_title": data['title'],
                "poster": data.get('poster', None),
            })
        
        return chapters_list
    
    async def get_pictures(self, url, data=None):
        # Use different headers to avoid the overlay
        overlay_headers = self.headers.copy()
        overlay_headers.update({
            "Referer": "https://toonily.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
        })
        
        response = await self.get(url, cs=True, headers=overlay_headers)
        soup = BeautifulSoup(response, "html.parser")
        
        # Remove all overlays, popups, and Discord messages
        for element in soup.find_all(["div", "section"]):
            classes = element.get('class', [])
            if classes and any(keyword in str(classes).lower() for keyword in ['popup', 'overlay', 'modal', 'discord', 'advertisement', 'notification']):
                element.decompose()
            elif element.get('id') and any(keyword in element.get('id', '').lower() for keyword in ['popup', 'overlay', 'modal', 'discord']):
                element.decompose()
        
        # Also remove any elements containing Discord text
        for element in soup.find_all(string=re.compile(r'discord|join server|support creator', re.IGNORECASE)):
            if element.parent:
                element.parent.decompose()
        
        images = []
        reading_content = soup.find("div", class_="reading-content")
        
        if reading_content:
            img_elements = reading_content.find_all("img")
            for img in img_elements:
                if img.get("src"):
                    img_url = img["src"].strip()
                    # Skip placeholder/default images
                    if any(placeholder in img_url.lower() for placeholder in ["default", "placeholder", "logo", "icon", "discord", "ad"]):
                        continue
                    # Validate the image before adding
                    if await self.validate_image(img_url):
                        images.append(img_url)
        
        # If no valid images found, try alternative selectors
        if not images:
            # Try finding images in different ways
            all_images = soup.find_all("img")
            for img in all_images:
                if img.get("src"):
                    img_url = img["src"].strip()
                    # Look for images that might be chapter content
                    if ("chapter" in img_url.lower() or "wp-content" in img_url) and not any(placeholder in img_url.lower() for placeholder in ["default", "placeholder"]):
                        if await self.validate_image(img_url):
                            images.append(img_url)
        
        # If still no images, try JavaScript-loaded images
        if not images:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'images' in script.string:
                    # Look for image URLs in JavaScript
                    image_urls = re.findall(r'https?://[^\s"\']+\.(jpg|jpeg|png|gif|webp)', script.string, re.IGNORECASE)
                    for img_url in image_urls:
                        if not any(placeholder in img_url.lower() for placeholder in ["default", "placeholder", "logo", "icon"]):
                            if await self.validate_image(img_url):
                                images.append(img_url)
        
        return images
    
    async def validate_image(self, image_url):
        """Validate if the image is a real image file and not a placeholder"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, headers=self.headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # Check if it's a placeholder by file size
                        if len(content) < 2048:  # Less than 2KB is likely a placeholder
                            return False
                        
                        # Check if it's a valid image format
                        try:
                            # Try to detect image format
                            image_format = imghdr.what(None, h=content)
                            if image_format is None:
                                # Try with PIL as fallback
                                img = Image.open(io.BytesIO(content))
                                img.verify()
                            return True
                        except Exception as e:
                            logger.warning(f"Invalid image format for {image_url}: {e}")
                            return False
            return False
        except Exception as e:
            logger.warning(f"Error validating image {image_url}: {e}")
            return False
    
    async def get_updates(self, page: int = 1):
        output = []
        url = f"{self.url}/page/{page}/"
        
        response = await self.get(url, cs=True, headers=self.headers)
        soup = BeautifulSoup(response, "html.parser")
        
        # Remove overlays
        for overlay in soup.find_all(["div", "section"], class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['popup', 'overlay', 'modal', 'discord', 'advertisement'])):
            overlay.decompose()
        
        updates = soup.find_all("div", class_="page-item-detail")
        
        for item in updates:
            title_element = item.find("h3")
            if not title_element:
                continue
                
            title_link = title_element.find("a")
            if not title_link:
                continue
                
            title = title_link.text.strip()
            manga_url = title_link["href"]
            slug_match = re.search(r'/webtoon/([^/]+)/', manga_url)
            slug = slug_match.group(1) if slug_match else manga_url.split("/")[-2]
            
            chapter_element = item.find("span", class_="chapter")
            chapter_title = "N/A"
            chapter_url = "N/A"
            if chapter_element:
                chapter_link = chapter_element.find("a")
                if chapter_link:
                    chapter_title = chapter_link.text.strip()
                    chapter_url = chapter_link["href"]
                
            image_element = item.find("img")
            poster = image_element["src"] if image_element else "N/A"
            
            output.append({
                "manga_title": title,
                "url": manga_url,
                "slug": slug,
                "title": chapter_title,
                "chapter_url": chapter_url,
                "poster": poster
            })
        
        return output
