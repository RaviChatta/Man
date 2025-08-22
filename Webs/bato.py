from .scraper import Scraper
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote, quote_plus
import re
from loguru import logger
import asyncio
import random


class BatoWebs(Scraper):
    def __init__(self):
        super().__init__()
        self.mirrors = [
            "https://xbato.com",
            "https://xbato.net",
            "https://xbato.org",
            "https://zbato.com",
            "https://zbato.net",
            "https://zbato.org",
            "https://readtoto.com",
            "https://readtoto.net",
            "https://readtoto.org",
            "https://batocomic.com",
            "https://batocomic.net",
            "https://batocomic.org",
            "https://batotoo.com",
            "https://batotwo.com",
            "https://battwo.com",
            "https://comiko.net",
            "https://comiko.org",
            "https://mangatoto.com",
            "https://mangatoto.net",
            "https://mangatoto.org",
            "https://dto.to",
            "https://fto.to",
            "https://jto.to",
            "https://hto.to",
            "https://mto.to",
            "https://wto.to",
            "https://bato.to"
        ]
        self.current_mirror = self.mirrors[0]
        self.url = self.current_mirror
        self.bg = True
        self.sf = "bt"
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
            "Referer": "https://bato.to/"
        }

    async def rotate_mirror(self):
        """Rotate to a different mirror if current one fails"""
        current_index = self.mirrors.index(self.current_mirror)
        next_index = (current_index + 1) % len(self.mirrors)
        self.current_mirror = self.mirrors[next_index]
        self.url = self.current_mirror
        logger.info(f"Rotated to mirror: {self.current_mirror}")

    async def request_with_mirror_fallback(self, url_path, *args, **kwargs):
        """Make request with automatic mirror rotation on failure"""
        max_retries = len(self.mirrors)
        
        for attempt in range(max_retries):
            try:
                full_url = urljoin(self.current_mirror, url_path)
                response = await self.get(full_url, *args, **kwargs)
                if response:
                    return response
                else:
                    raise Exception("Empty response")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Mirror {self.current_mirror} failed, rotating...")
                    await self.rotate_mirror()
                    await asyncio.sleep(1)
                else:
                    raise e
        return None

    async def search(self, query: str = ""):
        url_path = f"/search?word={quote_plus(query)}"
        results = await self.request_with_mirror_fallback(url_path, headers=self.headers)
        
        if not results:
            return []
            
        bs = BeautifulSoup(results, "html.parser")
        container = bs.find("div", class_="container")
        
        results_list = []
        if container:
            # Find all manga items - Bato uses various card classes
            cards = container.find_all("div", class_=lambda x: x and ("item" in x or "card" in x or "manga" in x))
            
            for card in cards:
                try:
                    data = {}
                    # Find link
                    link = card.find("a")
                    if link and link.get('href'):
                        data['url'] = urljoin(self.current_mirror, link.get('href').strip())
                    
                    # Find image
                    img = card.find("img")
                    if img:
                        data['poster'] = img.get('src') or img.get('data-src')
                        if data['poster'] and not data['poster'].startswith(('http', '//')):
                            data['poster'] = urljoin(self.current_mirror, data['poster'])
                    
                    # Find title
                    title_elem = card.find("div", class_=lambda x: x and ("title" in x or "name" in x)) or card.find("h3") or card.find("h2")
                    if title_elem:
                        data['title'] = title_elem.text.strip()
                    
                    # Get ID from URL
                    if 'url' in data:
                        data['id'] = data['url'].split('/')[-1] or data['url'].split('/')[-2]
                    
                    if all(key in data for key in ['url', 'title']):
                        results_list.append(data)
                        
                except Exception as e:
                    logger.error(f"Error parsing Bato search result: {e}")
                    continue
                
        return results_list

    async def get_chapters(self, data, page: int=1):
        results = data
        if 'url' not in results:
            return results
            
        content = await self.request_with_mirror_fallback(results['url'], headers=self.headers)
        if not content:
            return results
            
        bs = BeautifulSoup(content, "html.parser")
        
        # Get description
        description = bs.find("div", class_=lambda x: x and ("description" in x or "summary" in x))
        desc_text = description.text.strip() if description else "No description available"
        
        # Get genres/tags
        genres = []
        genre_container = bs.find("div", class_=lambda x: x and ("genre" in x or "tag" in x))
        if genre_container:
            genres = [a.text.strip() for a in genre_container.find_all("a")]
        
        # Get cover image if not already present
        if 'poster' not in results or not results['poster']:
            cover = bs.find("img", class_=lambda x: x and ("cover" in x or "poster" in x))
            if cover:
                results['poster'] = cover.get('src') or cover.get('data-src')
                if results['poster'] and not results['poster'].startswith(('http', '//')):
                    results['poster'] = urljoin(self.current_mirror, results['poster'])
        
        # Build message
        results['msg'] = f"<b>{results['title']}</b>\n\n"
        results['msg'] += f"<b>Genres:</b> <blockquote expandable><code>{', '.join(genres)}</code></blockquote>\n\n"
        results['msg'] += f"<b>Description:</b> <blockquote expandable><code>{desc_text}</code></blockquote>\n"
        
        # Find chapters container
        chapters_container = bs.find("div", class_=lambda x: x and ("chapter" in x or "episode" in x or "list" in x))
        results['chapters'] = chapters_container
        
        return results

    def iter_chapters(self, data, page: int=1):
        chapters_list = []
        
        if not data.get('chapters'):
            return chapters_list
            
        # Find all chapter links
        chapter_links = data['chapters'].find_all("a", class_=lambda x: x and ("chapter" in x or "episode" in x))
        
        for link in chapter_links:
            try:
                chapter_data = {
                    "title": link.text.strip(),
                    "url": urljoin(self.current_mirror, link.get('href').strip()),
                    "manga_title": data['title'],
                    "poster": data.get('poster', '')
                }
                chapters_list.append(chapter_data)
            except Exception as e:
                logger.error(f"Error parsing chapter: {e}")
                continue
        
        # Pagination
        items_per_page = 50
        start_idx = (page - 1) * items_per_page
        end_idx = page * items_per_page
        
        return chapters_list[start_idx:end_idx] if page > 1 else chapters_list

    async def get_pictures(self, url, data=None):
        content = await self.request_with_mirror_fallback(url, headers=self.headers)
        if not content:
            return []
            
        bs = BeautifulSoup(content, "html.parser")
        
        # Bato uses various methods for images - try different selectors
        image_links = []
        
        # Method 1: Direct img tags with data-src or src
        images = bs.find_all("img", class_=lambda x: x and ("page" in x or "image" in x))
        for img in images:
            img_url = img.get('data-src') or img.get('src')
            if img_url:
                if not img_url.startswith(('http', '//')):
                    img_url = urljoin(self.current_mirror, img_url)
                image_links.append(img_url)
        
        # Method 2: JavaScript data (common in Bato)
        if not image_links:
            script_tags = bs.find_all('script')
            for script in script_tags:
                if script.string and 'const images' in script.string:
                    # Try to extract image URLs from JavaScript
                    pattern = r'https?://[^\s"\'\)]+\.(jpg|jpeg|png|gif|webp)'
                    matches = re.findall(pattern, script.string)
                    image_links.extend(matches)
        
        # Method 3: Data attributes
        if not image_links:
            divs_with_data = bs.find_all("div", {"data-url": True})
            for div in divs_with_data:
                img_url = div.get('data-url')
                if img_url:
                    if not img_url.startswith(('http', '//')):
                        img_url = urljoin(self.current_mirror, img_url)
                    image_links.append(img_url)
        
        return list(set(image_links))  # Remove duplicates

    async def get_updates(self, page:int=1):
        output = []
        
        # Bato usually has a updates/recent page
        url_path = f"/browse?page={page}&sort=update"
        results = await self.request_with_mirror_fallback(url_path, headers=self.headers)
        
        if not results:
            return output
            
        bs = BeautifulSoup(results, "html.parser")
        container = bs.find("div", class_="container")
        
        if container:
            # Find update items - could be cards, rows, or list items
            update_items = container.find_all("div", class_=lambda x: x and ("item" in x or "card" in x or "row" in x))
            
            for item in update_items:
                try:
                    data = {}
                    
                    # Find manga link
                    manga_link = item.find("a", class_=lambda x: x and ("manga" in x or "title" in x))
                    if manga_link:
                        data['url'] = urljoin(self.current_mirror, manga_link.get('href').strip())
                        data['manga_title'] = manga_link.text.strip()
                    
                    # Find chapter link
                    chapter_link = item.find("a", class_=lambda x: x and ("chapter" in x or "episode" in x))
                    if chapter_link:
                        data['chapter_url'] = urljoin(self.current_mirror, chapter_link.get('href').strip())
                        data['title'] = chapter_link.text.strip()
                    
                    if all(key in data for key in ['url', 'chapter_url']):
                        output.append(data)
                        
                except Exception as e:
                    logger.error(f"Error parsing Bato update: {e}")
                    continue
        
        return output
