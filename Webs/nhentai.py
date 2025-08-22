from .scraper import Scraper
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote, quote_plus
import re
from loguru import logger
import asyncio
import aiohttp


class NHentaiWebs(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://nhentai.net"
        self.bg = False
        self.sf = "nh"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
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

    async def search(self, query: str = ""):
        # Handle both gallery IDs and search queries
        if query.startswith('#') and query[1:].isdigit():
            # Direct gallery ID search
            gallery_id = query[1:]
            url = f"{self.url}/g/{gallery_id}/"
            return [await self._get_gallery_data(url, gallery_id)]
        elif query.isdigit():
            # Direct gallery ID without #
            url = f"{self.url}/g/{query}/"
            return [await self._get_gallery_data(url, query)]
        else:
            # Regular search
            url = f"{self.url}/search/?q={quote_plus(query)}"
        
        logger.info(f"Searching NHentai with URL: {url}")
        
        results = await self.get(url, headers=self.headers, cs=True)
        
        if not results:
            return []
            
        bs = BeautifulSoup(results, "html.parser")
        results_list = []
        
        # Find gallery items on nhentai.net
        gallery_items = bs.find_all("div", class_="gallery")
        
        for item in gallery_items[:15]:  # Limit to 15 results
            try:
                data = {}
                
                # Get the link
                link = item.find("a", class_="cover")
                if not link:
                    continue
                    
                data['url'] = urljoin(self.url, link.get('href', '').strip())
                
                # Get the gallery ID from URL
                gallery_id = data['url'].split('/')[-2]
                if gallery_id.isdigit():
                    data['id'] = gallery_id
                else:
                    continue  # Skip if no valid ID
                
                # Get image
                img = link.find("img")
                if img:
                    img_src = img.get('data-src') or img.get('src')
                    if img_src:
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        elif not img_src.startswith('http'):
                            img_src = urljoin(self.url, img_src)
                        data['poster'] = img_src
                
                # Get title from caption
                caption = item.find("div", class_="caption")
                if caption:
                    data['title'] = caption.text.strip()
                else:
                    # Fallback: use ID as title
                    data['title'] = f"Gallery {data['id']}"
                
                results_list.append(data)
                    
            except Exception as e:
                logger.error(f"Error parsing NHentai search result: {e}")
                continue
                
        return results_list

    async def _get_gallery_data(self, url, gallery_id):
        """Get gallery data for direct ID access"""
        content = await self.get(url, headers=self.headers, cs=True)
        if not content:
            return {"title": f"Gallery {gallery_id}", "url": url, "id": gallery_id}
            
        bs = BeautifulSoup(content, "html.parser")
        
        data = {
            "url": url,
            "id": gallery_id,
            "title": f"Gallery {gallery_id}",
            "poster": None
        }
        
        # Get title
        title_elem = bs.find("h1") or bs.find("h2") or bs.find("title")
        if title_elem:
            jap_title = title_elem.find("span", class_="pretty")
            if jap_title:
                data['title'] = jap_title.text.strip()
            else:
                data['title'] = title_elem.text.strip()
        
        # Get cover image
        cover_elem = bs.find("div", id="cover")
        if cover_elem:
            img = cover_elem.find("img")
            if img:
                img_src = img.get('data-src') or img.get('src')
                if img_src:
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif not img_src.startswith('http'):
                        img_src = urljoin(self.url, img_src)
                    data['poster'] = img_src
        
        return data

    async def get_chapters(self, data, page: int = 1):
        if 'url' not in data:
            return data
            
        content = await self.get(data['url'], headers=self.headers, cs=True)
        if not content:
            return data
            
        bs = BeautifulSoup(content, "html.parser")
        
        # Get title
        title_elem = bs.find("h1") or bs.find("h2") or bs.find("title")
        if title_elem:
            jap_title = title_elem.find("span", class_="pretty")
            if jap_title:
                data['title'] = jap_title.text.strip()
            else:
                data['title'] = title_elem.text.strip()
        
        # Get tags
        tags_section = bs.find("section", id="tags")
        tags = []
        if tags_section:
            tag_links = tags_section.find_all("a", class_="tag")
            for tag in tag_links:
                tag_name = tag.find("span", class_="name")
                if tag_name:
                    tags.append(tag_name.text.strip())
        
        # Get cover image
        cover_elem = bs.find("div", id="cover")
        if cover_elem:
            img = cover_elem.find("img")
            if img:
                img_src = img.get('data-src') or img.get('src')
                if img_src:
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif not img_src.startswith('http'):
                        img_src = urljoin(self.url, img_src)
                    data['poster'] = img_src
        
        # Get total pages
        total_pages = 0
        thumb_container = bs.find("div", id="thumbnail-container")
        if thumb_container:
            page_links = thumb_container.find_all("div", class_="thumb-container")
            total_pages = len(page_links)
        
        # Get additional info
        info_section = bs.find("div", id="info")
        uploaded = "N/A"
        favorites = "0"
        if info_section:
            # Get upload date
            upload_elem = info_section.find("time")
            if upload_elem:
                uploaded = upload_elem.text.strip()
            
            # Get favorites
            fav_elem = info_section.find("span", class_="favorites")
            if fav_elem:
                favorites = fav_elem.text.strip().replace(',', '')
        
        # Build message
        msg = f"<b>{data['title']}</b>\n\n"
        if tags:
            msg += f"<b>Tags:</b> <code>{', '.join(tags[:8])}</code>\n\n"
        msg += f"<b>Pages:</b> {total_pages}\n"
        msg += f"<b>Uploaded:</b> {uploaded}\n"
        msg += f"<b>Favorites:</b> {favorites}\n"
        msg += f"<b>URL:</b> {data['url']}"
        
        data['msg'] = msg
        data['total_pages'] = total_pages
        data['tags'] = tags
        data['uploaded'] = uploaded
        data['favorites'] = favorites
        
        return data

    def iter_chapters(self, data):
        # For NHentai, treat the entire gallery as one chapter for PDF creation
        if not data:
            return []
            
        chapters_list = [{
            "title": f"{data.get('title', 'NHentai Gallery')} - {data.get('total_pages', 0)} pages",
            "url": data.get('url', ''),
            "slug": data.get('id', ''),
            "manga_title": data.get('title', 'NHentai Gallery'),
            "poster": data.get('poster', ''),
            "total_pages": data.get('total_pages', 0),
            "gallery_id": data.get('id', '')
        }]
        
        return chapters_list

    async def get_pictures(self, url, data=None):
        """Get all image URLs from NHentai gallery for PDF creation"""
        content = await self.get(url, headers=self.headers, cs=True)
        if not content:
            return []
            
        bs = BeautifulSoup(content, "html.parser")
        image_urls = []
        
        # Extract gallery ID from URL
        gallery_id = url.split('/')[-2]
        if not gallery_id.isdigit():
            logger.error(f"Invalid gallery ID: {gallery_id}")
            return []
        
        logger.info(f"Extracting images for gallery {gallery_id}")
        
        # Method 1: Extract from JavaScript data (most reliable)
        scripts = bs.find_all('script')
        for script in scripts:
            if script.string and 'window._gallery' in script.string:
                try:
                    # Extract the JSON data from JavaScript
                    json_match = re.search(r'window\._gallery\s*=\s*JSON\.parse\(\s*[\'"](.+?)[\'"]\s*\)', script.string, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        # Unescape the JSON string
                        json_str = json_str.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
                        gallery_data = json.loads(json_str)
                        
                        media_id = gallery_data.get('media_id')
                        images = gallery_data.get('images', {}).get('pages', [])
                        
                        if media_id and images:
                            for i, image_data in enumerate(images, 1):
                                ext = self._get_extension(image_data.get('t'))
                                image_url = f"https://i.nhentai.net/galleries/{media_id}/{i}.{ext}"
                                image_urls.append(image_url)
                            logger.info(f"Found {len(image_urls)} images via JavaScript method")
                            break
                except Exception as e:
                    logger.error(f"Error parsing JavaScript gallery data: {e}")
                    continue
        
        # Method 2: Extract from thumbnail data attributes
        if not image_urls:
            thumb_container = bs.find("div", id="thumbnail-container")
            if thumb_container:
                thumb_links = thumb_container.find_all("a", class_="gallerythumb")
                for thumb_link in thumb_links:
                    img = thumb_link.find("img")
                    if img:
                        data_src = img.get('data-src')
                        if data_src:
                            # Convert thumbnail URL to full image URL
                            # Example: https://t.nhentai.net/galleries/2381456/1t.jpg -> https://i.nhentai.net/galleries/2381456/1.jpg
                            full_url = data_src.replace('t.nhentai.net', 'i.nhentai.net')
                            full_url = re.sub(r'(\d+)t\.(jpg|png|gif|webp)', r'\1.\2', full_url)
                            image_urls.append(full_url)
                logger.info(f"Found {len(image_urls)} images via thumbnail method")
        
        # Method 3: Try to find media_id in other script tags
        if not image_urls:
            media_id = None
            for script in scripts:
                if script.string and 'media_id' in script.string:
                    media_match = re.search(r'"media_id"\s*:\s*["\']?(\d+)["\']?', script.string)
                    if media_match:
                        media_id = media_match.group(1)
                        break
            
            if media_id:
                # Try to get total pages
                total_pages = data.get('total_pages', 0) if data else 0
                if total_pages == 0:
                    # Try to find total pages in the HTML
                    pages_elem = bs.find("span", class_="num-pages")
                    if pages_elem:
                        total_pages = int(pages_elem.text.strip())
                
                if total_pages > 0:
                    for page_num in range(1, total_pages + 1):
                        image_url = f"https://i.nhentai.net/g/{media_id}/{page_num}.jpg"
                        image_urls.append(image_url)
                logger.info(f"Found {len(image_urls)} images via media_id method")
        
        # Method 4: Direct construction as last resort
        if not image_urls:
            # Try different extensions for each possible page
            for page_num in range(1, 51):  # Assume max 50 pages
                extensions = ['jpg', 'png', 'gif', 'webp']
                for ext in extensions:
                    test_url = f"https://i.nhentai.net/galleries/{gallery_id}/{page_num}.{ext}"
                    if await self._validate_image_url(test_url):
                        image_urls.append(test_url)
                        break
            logger.info(f"Found {len(image_urls)} images via direct method")
        
        # Remove duplicates and ensure proper order
        unique_urls = []
        seen_urls = set()
        for url in image_urls:
            if url not in seen_urls:
                unique_urls.append(url)
                seen_urls.add(url)
        
        # Sort by page number
        def get_page_number(url):
            match = re.search(r'/(\d+)\.(jpg|png|gif|webp)', url)
            return int(match.group(1)) if match else 0
        
        unique_urls.sort(key=get_page_number)
        
        logger.info(f"Final image URLs: {unique_urls}")
        return unique_urls

    def _get_extension(self, format_code):
        """Convert NHentai format code to file extension"""
        extension_map = {
            'j': 'jpg',
            'p': 'png',
            'g': 'gif',
            'w': 'webp'
        }
        return extension_map.get(format_code, 'jpg')

    async def _validate_image_url(self, url):
        """Check if an image URL exists"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, headers=self.headers, timeout=5) as response:
                    return response.status == 200
        except:
            return False

    async def get_updates(self, page: int = 1):
        # NHentai front page as updates
        url = f"{self.url}/" if page == 1 else f"{self.url}/?page={page}"
        
        content = await self.get(url, headers=self.headers, cs=True)
        if not content:
            return []
            
        bs = BeautifulSoup(content, "html.parser")
        updates = []
        
        # Find popular or latest galleries
        gallery_items = bs.find_all("div", class_="gallery")[:10]  # Limit to 10
        
        for item in gallery_items:
            try:
                link = item.find("a", class_="cover")
                if not link:
                    continue
                    
                url = urljoin(self.url, link.get('href', '').strip())
                gallery_id = url.split('/')[-2]
                
                if not gallery_id.isdigit():
                    continue
                
                img = link.find("img")
                poster = None
                if img:
                    img_src = img.get('data-src') or img.get('src')
                    if img_src:
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        elif not img_src.startswith('http'):
                            img_src = urljoin(self.url, img_src)
                        poster = img_src
                
                caption = item.find("div", class_="caption")
                title = caption.text.strip() if caption else f"Gallery {gallery_id}"
                
                updates.append({
                    "manga_title": title,
                    "url": url,
                    "slug": gallery_id,
                    "title": "Latest Update",
                    "chapter_url": url,
                    "poster": poster
                })
                
            except Exception as e:
                logger.error(f"Error parsing NHentai update: {e}")
                continue
        
        return updates
