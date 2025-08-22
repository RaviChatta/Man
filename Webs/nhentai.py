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
        # Image servers from your code
        self.IMG_BASE_URLS = [
            'https://i2.nhentai.net/galleries',
            'https://i3.nhentai.net/galleries', 
            'https://i5.nhentai.net/galleries',
            'https://i7.nhentai.net/galleries'
        ]

    async def search(self, query: str = ""):
        # Handle direct gallery ID search (like #585898)
        if query.startswith('#') and query[1:].isdigit():
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
        
        # Find gallery items
        gallery_items = bs.find_all("div", class_="gallery")
        
        for item in gallery_items[:15]:
            try:
                data = {}
                
                # Get the link
                link = item.find("a", class_="cover")
                if not link:
                    continue
                    
                data['url'] = urljoin(self.url, link.get('href', '').strip())
                
                # Get gallery ID from URL
                gallery_id = data['url'].split('/')[-2]
                if gallery_id.isdigit():
                    data['id'] = gallery_id
                else:
                    continue
                
                # Get thumbnail image
                img = link.find("img")
                if img:
                    img_src = img.get('data-src') or img.get('src')
                    if img_src:
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        data['poster'] = img_src
                
                # Get title
                caption = item.find("div", class_="caption")
                data['title'] = caption.text.strip() if caption else f"Gallery {data['id']}"
                
                results_list.append(data)
                    
            except Exception as e:
                logger.error(f"Error parsing result: {e}")
                continue
                
        return results_list

    async def _get_gallery_data(self, url, gallery_id):
        """Get basic gallery data"""
        return {
            "title": f"Gallery {gallery_id}",
            "url": url,
            "id": gallery_id,
            "poster": None
        }

    async def get_chapters(self, data, page: int = 1):
        if 'url' not in data:
            return data
            
        content = await self.get(data['url'], headers=self.headers, cs=True)
        if not content:
            return data
            
        bs = BeautifulSoup(content, "html.parser")
        
        # Extract title
        title_elem = bs.find("h1") or bs.find("h2")
        if title_elem:
            jap_title = title_elem.find("span", class_="pretty")
            data['title'] = jap_title.text.strip() if jap_title else title_elem.text.strip()
        
        # Extract tags
        tags = []
        tags_section = bs.find("section", id="tags")
        if tags_section:
            tag_links = tags_section.find_all("a", class_="tag")
            for tag in tag_links:
                tag_name = tag.find("span", class_="name")
                if tag_name:
                    tags.append(tag_name.text.strip())
        
        # Extract total pages
        total_pages = 0
        thumb_container = bs.find("div", id="thumbnail-container")
        if thumb_container:
            total_pages = len(thumb_container.find_all("div", class_="thumb-container"))
        
        # Extract additional info
        info_section = bs.find("div", id="info")
        uploaded = "N/A"
        favorites = "0"
        if info_section:
            upload_elem = info_section.find("time")
            if upload_elem:
                uploaded = upload_elem.text.strip()
            
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
        
        return data

    def iter_chapters(self, data):
        if not data:
            return []
            
        return [{
            "title": f"{data.get('title', 'NHentai Gallery')} - {data.get('total_pages', 0)} pages",
            "url": data.get('url', ''),
            "slug": data.get('id', ''),
            "manga_title": data.get('title', 'NHentai Gallery'),
            "poster": data.get('poster', ''),
            "total_pages": data.get('total_pages', 0),
            "gallery_id": data.get('id', '')
        }]

    async def get_pictures(self, url, data=None):
        """Extract image URLs using the pattern from your NHentai code"""
        content = await self.get(url, headers=self.headers, cs=True)
        if not content:
            return []
            
        bs = BeautifulSoup(content, "html.parser")
        image_urls = []
        
        # Extract gallery ID
        gallery_id = url.split('/')[-2]
        if not gallery_id.isdigit():
            return []
        
        # Extract media_id from JavaScript (crucial for your image URLs)
        media_id = None
        scripts = bs.find_all('script')
        for script in scripts:
            if script.string and 'media_id' in script.string:
                media_match = re.search(r'"media_id"\s*:\s*["\']?(\d+)["\']?', script.string)
                if media_match:
                    media_id = media_match.group(1)
                    break
        
        # Use gallery_id as fallback if media_id not found
        if not media_id:
            media_id = gallery_id
        
        # Get total pages
        total_pages = 0
        thumb_container = bs.find("div", id="thumbnail-container")
        if thumb_container:
            total_pages = len(thumb_container.find_all("div", class_="thumb-container"))
        
        # Construct image URLs using YOUR pattern
        if total_pages > 0:
            for page_num in range(1, total_pages + 1):
                # Try different extensions
                for ext in ['jpg', 'png', 'gif', 'webp']:
                    # Try different image servers from your code
                    for img_base_url in self.IMG_BASE_URLS:
                        image_url = f"{img_base_url}/{media_id}/{page_num}.{ext}"
                        if await self._validate_image_url(image_url):
                            image_urls.append(image_url)
                            break
                    else:
                        continue
                    break
        
        return image_urls

    async def _validate_image_url(self, url):
        """Validate image URL exists"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, headers=self.headers, timeout=5) as response:
                    return response.status == 200
        except:
            return False

    async def get_updates(self, page: int = 1):
        # Get latest galleries from front page
        url = f"{self.url}/" if page == 1 else f"{self.url}/?page={page}"
        
        content = await self.get(url, headers=self.headers, cs=True)
        if not content:
            return []
            
        bs = BeautifulSoup(content, "html.parser")
        updates = []
        
        gallery_items = bs.find_all("div", class_="gallery")[:10]
        
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
                logger.error(f"Error parsing update: {e}")
                continue
        
        return updates
