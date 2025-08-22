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
            "https://bato.to",
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
            "https://wto.to"
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
                    logger.warning(f"Mirror {self.current_mirror} failed: {e}, rotating...")
                    await self.rotate_mirror()
                    await asyncio.sleep(1)
                else:
                    logger.error(f"All mirrors failed: {e}")
                    raise e
        return None

    async def search(self, query: str = ""):
        url_path = f"/search?word={quote_plus(query)}"
        results = await self.request_with_mirror_fallback(url_path, headers=self.headers)
        
        if not results:
            return []
            
        bs = BeautifulSoup(results, "html.parser")
        
        # Try different selectors for search results
        results_list = []
        
        # Method 1: New Bato layout with div classes
        containers = [
            bs.find("div", class_="container"),
            bs.find("div", class_="main"),
            bs.find("div", class_="search-results"),
            bs.find("div", class_="manga-list"),
            bs.find("div", class_="series-list")
        ]
        
        container = None
        for c in containers:
            if c:
                container = c
                break
        
        if not container:
            # Try finding any manga items directly
            manga_items = bs.find_all("div", class_=lambda x: x and any(keyword in str(x).lower() for keyword in ["item", "card", "manga", "series"]))
            if manga_items:
                container = bs
            else:
                return []

        # Find all manga items using multiple selectors
        selectors = [
            "div.item", "div.card", "div.manga-item", "div.series-item",
            "a[href*='/series/']", "a[href*='/title/']",
            "div[class*='item']", "div[class*='card']"
        ]
        
        for selector in selectors:
            cards = container.select(selector)
            if cards:
                break
        else:
            # Fallback to finding any links that look like manga
            cards = container.find_all("a", href=re.compile(r'/series/|/title/|/manga/'))
        
        for card in cards[:20]:  # Limit to 20 results
            try:
                data = {}
                
                # Get URL
                if card.name == "a":
                    href = card.get('href')
                else:
                    link = card.find("a")
                    href = link.get('href') if link else None
                
                if not href:
                    continue
                    
                data['url'] = urljoin(self.current_mirror, href.strip())
                
                # Get image
                img = card.find("img")
                if img:
                    data['poster'] = img.get('src') or img.get('data-src')
                    if data['poster'] and not data['poster'].startswith(('http', '//')):
                        data['poster'] = urljoin(self.current_mirror, data['poster'])
                
                # Get title
                title_selectors = [
                    "h3", "h2", "h4", ".title", ".name", "span.title", 
                    "div.title", "a[title]", "[class*='title']", "[class*='name']"
                ]
                
                title_elem = None
                for selector in title_selectors:
                    if card.name == "a":
                        title_elem = card.select_one(selector)
                    else:
                        title_elem = card.find(selector)
                    if title_elem:
                        break
                
                if title_elem:
                    data['title'] = title_elem.text.strip()
                elif card.get('title'):
                    data['title'] = card.get('title').strip()
                else:
                    # Extract title from URL as last resort
                    title_from_url = data['url'].split('/')[-1].replace('-', ' ').title()
                    data['title'] = title_from_url
                
                # Get ID from URL
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
        description_selectors = [
            "div.description", "div.summary", "div.synopsis", "p.description",
            "[class*='description']", "[class*='summary']", "[class*='synopsis']"
        ]
        
        description = None
        for selector in description_selectors:
            description = bs.select_one(selector)
            if description:
                break
        
        desc_text = description.text.strip() if description else "No description available"
        
        # Get genres/tags
        genres = []
        genre_selectors = [
            "div.genres", "div.tags", "div.categories", "[class*='genre']",
            "[class*='tag']", "[class*='category']"
        ]
        
        for selector in genre_selectors:
            genre_container = bs.select_one(selector)
            if genre_container:
                genres = [a.text.strip() for a in genre_container.find_all("a")]
                if genres:
                    break
        
        # Get cover image if not already present
        if 'poster' not in results or not results['poster']:
            cover_selectors = [
                "img.cover", "img.poster", "div.cover img", "div.poster img",
                "img[src*='cover']", "img[src*='poster']"
            ]
            
            for selector in cover_selectors:
                cover = bs.select_one(selector)
                if cover:
                    results['poster'] = cover.get('src') or cover.get('data-src')
                    if results['poster'] and not results['poster'].startswith(('http', '//')):
                        results['poster'] = urljoin(self.current_mirror, results['poster'])
                    break
        
        # Build message
        results['msg'] = f"<b>{results['title']}</b>\n\n"
        results['msg'] += f"<b>Genres:</b> <blockquote expandable><code>{', '.join(genres)}</code></blockquote>\n\n"
        results['msg'] += f"<b>Description:</b> <blockquote expandable><code>{desc_text}</code></blockquote>\n"
        
        # Find chapters container
        chapter_selectors = [
            "div.chapters", "div.episodes", "div.chapter-list", "div.episode-list",
            "table.chapters", "table.episodes", "[class*='chapter']", "[class*='episode']"
        ]
        
        chapters_container = None
        for selector in chapter_selectors:
            chapters_container = bs.select_one(selector)
            if chapters_container:
                break
        
        results['chapters'] = chapters_container
        
        return results

    def iter_chapters(self, data, page: int=1):
        chapters_list = []
        
        if not data.get('chapters'):
            return chapters_list
            
        # Find all chapter links
        chapter_selectors = [
            "a.chapter", "a.episode", "tr.chapter", "tr.episode",
            "[href*='/chapter/']", "[href*='/episode/']", "[href*='/read/']"
        ]
        
        chapter_links = []
        for selector in chapter_selectors:
            chapter_links = data['chapters'].select(selector)
            if chapter_links:
                break
        
        if not chapter_links:
            # Fallback to finding any links that might be chapters
            chapter_links = data['chapters'].find_all("a", href=re.compile(r'/chapter/|/episode/|/read/'))
        
        for link in chapter_links:
            try:
                href = link.get('href')
                if not href:
                    continue
                    
                # Get chapter title
                title_selectors = ["span", "div", "td", "h3", "h4"]
                title = None
                for selector in title_selectors:
                    title_elem = link.find(selector)
                    if title_elem:
                        title = title_elem.text.strip()
                        break
                
                if not title:
                    title = link.text.strip() or f"Chapter {len(chapters_list) + 1}"
                
                chapter_data = {
                    "title": title,
                    "url": urljoin(self.current_mirror, href.strip()),
                    "manga_title": data['title'],
                    "poster": data.get('poster', '')
                }
                chapters_list.append(chapter_data)
            except Exception as e:
                logger.error(f"Error parsing chapter: {e}")
                continue
        
        # Reverse to show latest first
        chapters_list.reverse()
        
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
        image_links = []
        
        # Method 1: Direct img tags in reading container
        reading_selectors = [
            "div.reader", "div.viewer", "div.images", "div.pages",
            "div[class*='reader']", "div[class*='viewer']", "div[class*='image']"
        ]
        
        reading_container = None
        for selector in reading_selectors:
            reading_container = bs.select_one(selector)
            if reading_container:
                break
        
        if reading_container:
            images = reading_container.find_all("img")
            for img in images:
                img_url = img.get('data-src') or img.get('src') or img.get('data-url')
                if img_url:
                    if not img_url.startswith(('http', '//')):
                        img_url = urljoin(self.current_mirror, img_url)
                    image_links.append(img_url)
        
        # Method 2: JavaScript data
        if not image_links:
            script_tags = bs.find_all('script')
            for script in script_tags:
                if script.string:
                    # Look for image arrays in JS
                    patterns = [
                        r'const images\s*=\s*\[([^\]]+)\]',
                        r'var images\s*=\s*\[([^\]]+)\]',
                        r'images:\s*\[([^\]]+)\]',
                        r'\"images\"\s*:\s*\[([^\]]+)\]'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script.string)
                        for match in matches:
                            # Extract URLs from the array
                            urls = re.findall(r'\"([^\"]+\.(jpg|jpeg|png|gif|webp))\"', match)
                            for url, ext in urls:
                                if not url.startswith(('http', '//')):
                                    url = urljoin(self.current_mirror, url)
                                image_links.append(url)
        
        # Method 3: Data attributes
        if not image_links:
            divs_with_data = bs.find_all(["div", "img"], {"data-url": True})
            for elem in divs_with_data:
                img_url = elem.get('data-url')
                if img_url:
                    if not img_url.startswith(('http', '//')):
                        img_url = urljoin(self.current_mirror, img_url)
                    image_links.append(img_url)
        
        return list(set(image_links))  # Remove duplicates

    async def get_updates(self, page:int=1):
        output = []
        
        # Try different update pages
        update_paths = [
            f"/browse?page={page}&sort=update",
            f"/latest?page={page}",
            f"/recent?page={page}",
            f"/updates?page={page}"
        ]
        
        for path in update_paths:
            results = await self.request_with_mirror_fallback(path, headers=self.headers)
            if not results:
                continue
                
            bs = BeautifulSoup(results, "html.parser")
            
            # Try different update item selectors
            update_selectors = [
                "div.item", "div.card", "div.manga-item", "div.series-item",
                "tr.chapter", "tr.episode", "div.update-item"
            ]
            
            for selector in update_selectors:
                update_items = bs.select(selector)
                if update_items:
                    for item in update_items[:30]:  # Limit to 30 items
                        try:
                            data = {}
                            
                            # Find manga link
                            manga_link = item.select_one("a[href*='/series/'], a[href*='/title/'], a[href*='/manga/']")
                            if manga_link:
                                data['url'] = urljoin(self.current_mirror, manga_link.get('href').strip())
                                data['manga_title'] = manga_link.text.strip() or "Unknown Title"
                            
                            # Find chapter link
                            chapter_link = item.select_one("a[href*='/chapter/'], a[href*='/episode/'], a[href*='/read/']")
                            if chapter_link:
                                data['chapter_url'] = urljoin(self.current_mirror, chapter_link.get('href').strip())
                                data['title'] = chapter_link.text.strip() or "Latest Chapter"
                            
                            if all(key in data for key in ['url', 'chapter_url']):
                                output.append(data)
                                
                        except Exception as e:
                            logger.error(f"Error parsing Bato update: {e}")
                            continue
                    
                    if output:
                        return output
        
        return output
