from .scraper import Scraper
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote, quote_plus
import re
from loguru import logger
import asyncio


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
        url = f"{self.url}/search/?q={quote_plus(query)}"
        logger.info(f"Searching NHentai with URL: {url}")
        
        results = await self.get(url, headers=self.headers, cs=True)
        
        if not results:
            return []
            
        bs = BeautifulSoup(results, "html.parser")
        results_list = []
        
        # Find gallery items - nhentai.to uses specific structure
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

    async def get_information(self, slug, data):
        # For NHentai, we use the get_chapters method to get info
        pass

    async def get_chapters(self, data, page: int = 1):
        if 'url' not in data:
            return data
            
        content = await self.get(data['url'], headers=self.headers, cs=True)
        if not content:
            return data
            
        bs = BeautifulSoup(content, "html.parser")
        
        # Get title
        title_elem = bs.find("h1", class_="title") or bs.find("h2", class_="title") or bs.find("title")
        if title_elem:
            data['title'] = title_elem.text.strip()
        
        # Get tags
        tags_section = bs.find("section", id="tags")
        tags = []
        if tags_section:
            tag_links = tags_section.find_all("a", class_="tag")
            tags = [tag.find("span", class_="name").text.strip() for tag in tag_links if tag.find("span", class_="name")]
        
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
            page_links = thumb_container.find_all("a", class_="gallerythumb")
            total_pages = len(page_links)
        
        # Build message
        msg = f"<b>{data['title']}</b>\n\n"
        if tags:
            msg += f"<b>Tags:</b> <code>{', '.join(tags[:10])}</code>\n\n"
        msg += f"<b>Pages:</b> {total_pages}\n"
        msg += f"<b>URL:</b> {data['url']}"
        
        data['msg'] = msg
        data['total_pages'] = total_pages
        data['tags'] = tags
        
        return data

    def iter_chapters(self, data):
        # For NHentai, each gallery is one "chapter"
        if not data:
            return []
            
        chapters_list = [{
            "title": f"{data.get('title', 'NHentai Gallery')} - {data.get('total_pages', 0)} pages",
            "url": data.get('url', ''),
            "slug": data.get('id', ''),
            "manga_title": data.get('title', 'NHentai Gallery'),
            "poster": data.get('poster', ''),
            "total_pages": data.get('total_pages', 0)
        }]
        
        return chapters_list

    async def get_pictures(self, url, data=None):
        content = await self.get(url, headers=self.headers, cs=True)
        if not content:
            return []
            
        bs = BeautifulSoup(content, "html.parser")
        image_urls = []
        
        # Method 1: Get images from thumbnail container
        thumb_container = bs.find("div", id="thumbnail-container")
        if thumb_container:
            thumb_links = thumb_container.find_all("a", class_="gallerythumb")
            for thumb_link in thumb_links:
                img = thumb_link.find("img")
                if img:
                    img_src = img.get('data-src') or img.get('src')
                    if img_src:
                        # Convert thumbnail URL to full image URL
                        # Thumbnail: https://t.nhentai.to/galleries/2381456/1t.jpg
                        # Full image: https://i.nhentai.to/galleries/2381456/1.jpg
                        if 't.nhentai.to' in img_src:
                            full_img_url = img_src.replace('t.nhentai.to', 'i.nhentai.to').replace('t.jpg', '.jpg').replace('t.png', '.png')
                            image_urls.append(full_img_url)
                        else:
                            # Try to construct full image URL from pattern
                            match = re.search(r'/galleries/(\d+)/(\d+)t\.', img_src)
                            if match:
                                gallery_id = match.group(1)
                                page_num = match.group(2)
                                full_img_url = f"https://i.nhentai.to/galleries/{gallery_id}/{page_num}.jpg"
                                image_urls.append(full_img_url)
        
        # Method 2: Try to find image URLs in script tags
        if not image_urls:
            scripts = bs.find_all('script')
            for script in scripts:
                if script.string and 'images' in script.string:
                    # Look for JSON data
                    json_match = re.search(r'JSON\.parse\(\'(.+?)\'\)', script.string)
                    if json_match:
                        try:
                            json_str = json_match.group(1).replace('\\"', '"').replace("\\'", "'")
                            images_data = json.loads(json_str)
                            if 'images' in images_data:
                                gallery_id = images_data.get('media_id', '')
                                pages = images_data['images'].get('pages', [])
                                for i, page in enumerate(pages, 1):
                                    ext = page.get('t', 'jpg')
                                    if ext == 'j': ext = 'jpg'
                                    elif ext == 'p': ext = 'png'
                                    elif ext == 'g': ext = 'gif'
                                    image_url = f"https://i.nhentai.to/galleries/{gallery_id}/{i}.{ext}"
                                    image_urls.append(image_url)
                        except:
                            pass
        
        # Method 3: Fallback - try to find any image patterns
        if not image_urls:
            all_images = bs.find_all('img')
            for img in all_images:
                img_src = img.get('src') or img.get('data-src')
                if img_src and any(x in img_src for x in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif not img_src.startswith('http'):
                        img_src = urljoin(self.url, img_src)
                    image_urls.append(img_src)
        
        return list(dict.fromkeys(image_urls))  # Remove duplicates while preserving order

    async def get_updates(self, page: int = 1):
        # NHentai doesn't have a traditional updates page, so we'll use the front page
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
