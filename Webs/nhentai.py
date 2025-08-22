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
        self.url = "https://nhentai.to/"
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
            "Referer": "https://nhentai.to/"
        }

    async def search(self, query: str = ""):
        url = f"https://nhentai.to/search/?q={quote_plus(query)}"
        results = await self.get(url, headers=self.headers, cs=True)
        
        if not results:
            return []
            
        bs = BeautifulSoup(results, "html.parser")
        
        # Find gallery containers - nhentai.to uses different structure
        results_list = []
        
        # Method 1: Look for gallery items
        gallery_items = bs.find_all("div", class_="gallery")
        if not gallery_items:
            # Method 2: Look for items with data-id (common on nhentai.to)
            gallery_items = bs.find_all("div", {"data-id": True})
        
        if not gallery_items:
            # Method 3: Look for any items that might contain galleries
            gallery_items = bs.find_all("a", href=re.compile(r'/g/\d+/'))
        
        for item in gallery_items[:20]:  # Limit to 20 results
            try:
                data = {}
                
                # Get URL
                if item.name == "a":
                    href = item.get('href')
                else:
                    link = item.find("a")
                    href = link.get('href') if link else None
                
                if not href:
                    continue
                    
                data['url'] = urljoin(self.url, href.strip())
                
                # Get image
                img = item.find("img")
                if img:
                    data['poster'] = img.get('src') or img.get('data-src') or img.get('data-srcset')
                    if data['poster'] and not data['poster'].startswith(('http', '//')):
                        data['poster'] = urljoin(self.url, data['poster'])
                
                # Get title
                title_selectors = [
                    ".caption", ".title", "h3", "h2", "[class*='title']",
                    "[class*='name']", ".gallery-title"
                ]
                
                title_elem = None
                for selector in title_selectors:
                    title_elem = item.select_one(selector)
                    if title_elem:
                        break
                
                if title_elem:
                    data['title'] = title_elem.text.strip()
                elif item.get('title'):
                    data['title'] = item.get('title').strip()
                else:
                    # Extract title from URL
                    title_from_url = data['url'].split('/')[-2].replace('-', ' ').title()
                    data['title'] = title_from_url
                
                # Get ID from URL
                data['id'] = data['url'].split('/')[-2] if data['url'].split('/')[-2].isdigit() else data['url'].split('/')[-1]
                
                if all(key in data for key in ['url', 'title']):
                    results_list.append(data)
                    
            except Exception as e:
                logger.error(f"Error parsing nhentai.to search result: {e}")
                continue
                
        return results_list

    async def get_chapters(self, data, page: int=1):
        results = data
        content = await self.get(results['url'], headers=self.headers, cs=True)
        if not content:
            return results
            
        bs = BeautifulSoup(content, "html.parser")
        
        # Get title
        title_elem = bs.find("h1", class_="title") or bs.find("h1") or bs.find("title")
        title = title_elem.text.strip() if title_elem else results['title']
        
        # Get tags/info
        info_container = bs.find("div", id="info") or bs.find("div", class_="info") or bs.find("section", id="tags")
        tags = []
        
        if info_container:
            tag_elements = info_container.find_all("a", class_="tag") or info_container.find_all("span", class_="tag")
            if tag_elements:
                tags = [tag.text.strip() for tag in tag_elements]
        
        # Get cover image
        cover_selectors = [
            "#cover", ".cover", ".thumb", "img[src*='cover']",
            "img[src*='thumb']", ".gallery-thumb"
        ]
        
        for selector in cover_selectors:
            cover = bs.select_one(selector)
            if cover:
                results['poster'] = cover.get('src') or cover.get('data-src') or cover.get('data-srcset')
                if results['poster'] and not results['poster'].startswith(('http', '//')):
                    results['poster'] = urljoin(self.url, results['poster'])
                break
        
        # Build message
        results['msg'] = f"<b>{title}</b>\n\n"
        if tags:
            results['msg'] += f"<b>Tags:</b>\n<blockquote expandable><code>{', '.join(tags)}</code></blockquote>\n\n"
        results['msg'] += f"<b>URL:</b> {results['url']}\n"
        
        # Store gallery info
        results['gallery_id'] = data['id']
        results['total_pages'] = self._get_total_pages(bs)
        
        return results

    def _get_total_pages(self, bs):
        # Try to find page count
        page_selectors = [
            ".num-pages", ".page-count", "[class*='page']", "[class*='count']",
            "span:contains('pages')", "div:contains('pages')"
        ]
        
        for selector in page_selectors:
            element = bs.select_one(selector)
            if element:
                text = element.text.strip()
                numbers = re.findall(r'\d+', text)
                if numbers:
                    return int(numbers[0])
        
        # Count image containers as fallback
        image_containers = bs.find_all("div", class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['page', 'image', 'thumb']))
        return len(image_containers) if image_containers else 0

    def iter_chapters(self, data, page: int=1):
        # For nhentai, each gallery is treated as one "chapter"
        chapters_list = [{
            "title": f"Gallery {data.get('gallery_id', 'Unknown')} - {data.get('total_pages', 0)} pages",
            "url": data['url'],
            "manga_title": data['title'],
            "poster": data.get('poster', ''),
            "gallery_id": data.get('gallery_id', ''),
            "total_pages": data.get('total_pages', 0)
        }]
        
        return chapters_list

    async def get_pictures(self, url, data=None):
        content = await self.get(url, headers=self.headers, cs=True)
        if not content:
            return []
            
        bs = BeautifulSoup(content, "html.parser")
        image_links = []
        
        # Method 1: Direct image tags in viewer
        viewer = bs.find("div", id="viewer") or bs.find("div", class_="viewer") or bs.find("div", id="image-container")
        if viewer:
            images = viewer.find_all("img")
            for img in images:
                img_url = img.get('src') or img.get('data-src') or img.get('data-srcset')
                if img_url:
                    if not img_url.startswith(('http', '//')):
                        img_url = urljoin(self.url, img_url)
                    image_links.append(img_url)
        
        # Method 2: JavaScript data
        if not image_links:
            script_tags = bs.find_all('script')
            for script in script_tags:
                if script.string and 'images' in script.string:
                    # Look for image arrays
                    patterns = [
                        r'images\s*:\s*\[([^\]]+)\]',
                        r'var images\s*=\s*\[([^\]]+)\]',
                        r'const images\s*=\s*\[([^\]]+)\]',
                        r'\"images\"\s*:\s*\[([^\]]+)\]'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script.string)
                        for match in matches:
                            urls = re.findall(r'\"([^\"]+\.(jpg|jpeg|png|gif|webp))\"', match)
                            for url, ext in urls:
                                if not url.startswith(('http', '//')):
                                    url = urljoin(self.url, url)
                                image_links.append(url)
        
        # Method 3: Data attributes
        if not image_links:
            elements_with_data = bs.find_all(attrs={"data-src": True})
            for elem in elements_with_data:
                img_url = elem.get('data-src')
                if img_url and any(ext in img_url for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    if not img_url.startswith(('http', '//')):
                        img_url = urljoin(self.url, img_url)
                    image_links.append(img_url)
        
        return list(set(image_links))

    async def get_updates(self, page:int=1):
        # nhentai.to doesn't have traditional updates, return empty
        return []
