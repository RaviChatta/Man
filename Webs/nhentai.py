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
        self.url = "https://nhentai.net/"
        self.bg = False  # Disable background updates for NSFW content
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
        if not query.strip():
            # If empty query, show popular from homepage
            return await self._get_popular()
            
        url = f"https://nhentai.net/search/?q={quote_plus(query)}"
        results = await self.get(url, headers=self.headers, cs=True)
        
        if not results:
            return []
            
        bs = BeautifulSoup(results, "html.parser")
        
        # Try multiple selectors for gallery containers
        galleries = bs.find_all("div", class_="gallery")
        if not galleries:
            # Fallback to container search
            container = bs.find("div", class_="container")
            if container:
                galleries = container.find_all("div", class_=lambda x: x and "gallery" in str(x).lower())
        
        results_list = []
        for gallery in galleries[:20]:  # Limit to 20 results
            try:
                data = {}
                
                # Get link
                link = gallery.find("a", class_="cover")
                if not link or not link.get('href'):
                    continue
                    
                data['url'] = urljoin(self.url, link.get('href').strip())
                
                # Get image
                img = link.find("img")
                if img:
                    data['poster'] = img.get('data-src') or img.get('src')
                    if data['poster'] and not data['poster'].startswith(('http', '//')):
                        data['poster'] = urljoin(self.url, data['poster'])
                
                # Get title
                caption = gallery.find("div", class_="caption")
                if caption:
                    data['title'] = caption.text.strip()
                else:
                    # Extract from URL as fallback
                    title_from_url = data['url'].split('/')[-2].replace('-', ' ').title()
                    data['title'] = title_from_url
                
                # Get ID from URL
                data['id'] = data['url'].split("/")[-2] if data['url'].split("/")[-2].isdigit() else data['url'].split("/")[-1]
                
                if all(key in data for key in ['url', 'title']):
                    results_list.append(data)
                    
            except Exception as e:
                logger.error(f"Error parsing nhentai search result: {e}")
                continue
                
        return results_list

    async def _get_popular(self):
        """Get popular galleries from homepage"""
        results = await self.get("https://nhentai.net/", headers=self.headers, cs=True)
        if not results:
            return []
            
        bs = BeautifulSoup(results, "html.parser")
        galleries = bs.find_all("div", class_="gallery")[:20]  # Limit to 20
        
        results_list = []
        for gallery in galleries:
            try:
                data = {}
                
                link = gallery.find("a", class_="cover")
                if not link or not link.get('href'):
                    continue
                    
                data['url'] = urljoin(self.url, link.get('href').strip())
                
                img = link.find("img")
                if img:
                    data['poster'] = img.get('data-src') or img.get('src')
                    if data['poster'] and not data['poster'].startswith(('http', '//')):
                        data['poster'] = urljoin(self.url, data['poster'])
                
                caption = gallery.find("div", class_="caption")
                if caption:
                    data['title'] = caption.text.strip()
                else:
                    title_from_url = data['url'].split('/')[-2].replace('-', ' ').title()
                    data['title'] = title_from_url
                
                data['id'] = data['url'].split("/")[-2]
                
                if all(key in data for key in ['url', 'title']):
                    results_list.append(data)
                    
            except Exception as e:
                logger.error(f"Error parsing nhentai popular result: {e}")
                continue
                
        return results_list

    async def get_chapters(self, data, page: int=1):
        results = data
        content = await self.get(results['url'], headers=self.headers, cs=True)
        if not content:
            return results
            
        bs = BeautifulSoup(content, "html.parser")
        
        # Get tags
        tags = []
        tags_container = bs.find("section", id="tags")
        if tags_container:
            for tag_group in tags_container.find_all("div", class_="tag-container"):
                tag_type = tag_group.find("span", class_="name")
                if tag_type:
                    tag_type = tag_type.text.strip()
                    tag_items = [a.text.strip() for a in tag_group.find_all("a", class_="tag")]
                    tags.append(f"{tag_type}: {', '.join(tag_items)}")
        
        # Get title
        title_elem = bs.find("h1", class_="title") or bs.find("h1")
        title = title_elem.text.strip() if title_elem else results['title']
        
        # Get cover image
        cover_elem = bs.find("div", id="cover") or bs.find("img", id="cover")
        if cover_elem:
            cover_img = cover_elem.find("img") if cover_elem.name == "div" else cover_elem
            if cover_img:
                results['poster'] = cover_img.get('data-src') or cover_img.get('src') or results.get('poster', '')
        
        # Build message
        results['msg'] = f"<b>{title}</b>\n\n"
        if tags:
            results['msg'] += f"<b>Tags:</b>\n<blockquote expandable><code>{chr(10).join(tags)}</code></blockquote>\n\n"
        results['msg'] += f"<b>URL:</b> {results['url']}\n"
        
        # Store gallery info
        results['gallery_id'] = results['url'].split("/")[-2] if results['url'].split("/")[-2].isdigit() else results['url'].split("/")[-1]
        results['total_pages'] = self._get_total_pages(bs)
        
        return results

    def _get_total_pages(self, bs):
        # Try to get total pages from thumbnail container
        thumb_container = bs.find("div", id="thumbnail-container")
        if thumb_container:
            return len(thumb_container.find_all("div", class_="thumb-container"))
        
        # Try to get from info
        info = bs.find("div", id="info")
        if info:
            pages_text = info.find(text=re.compile(r'pages?', re.IGNORECASE))
            if pages_text:
                numbers = re.findall(r'\d+', pages_text)
                if numbers:
                    return int(numbers[0])
        
        return 0

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
        # Extract gallery ID from URL
        gallery_id = None
        if data and 'gallery_id' in data:
            gallery_id = data['gallery_id']
        else:
            # Extract from URL
            parts = url.split('/')
            for part in parts:
                if part.isdigit():
                    gallery_id = part
                    break
        
        if not gallery_id:
            return []
        
        # Use API to get image URLs
        api_url = f"https://nhentai.net/api/gallery/{gallery_id}"
        response = await self.get(api_url, headers=self.headers, cs=True, rjson=True)
        
        if not response:
            return []
        
        image_links = []
        try:
            if 'images' in response and 'pages' in response['images']:
                media_id = response['media_id']
                for page in response['images']['pages']:
                    # Determine file extension
                    extension = page.get('t', 'jpg')
                    if extension == 'j': extension = 'jpg'
                    if extension == 'p': extension = 'png'
                    if extension == 'g': extension = 'gif'
                    
                    image_url = f"https://i.nhentai.net/galleries/{media_id}/{page['n']}.{extension}"
                    image_links.append(image_url)
        except Exception as e:
            logger.error(f"Error parsing nhentai API response: {e}")
        
        return image_links

    async def get_updates(self, page:int=1):
        # NHentai doesn't have traditional updates, return empty list
        # since bg=False should prevent this from being called anyway
        return []
