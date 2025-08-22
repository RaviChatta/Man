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
        self.bg = False  # Not suitable for background updates (NSFW content)
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
        url = f"https://nhentai.net/search/?q={quote_plus(query)}"
        results = await self.get(url, headers=self.headers, cs=True)
        
        if not results:
            return []
            
        bs = BeautifulSoup(results, "html.parser")
        container = bs.find_all("div", class_="gallery")
        
        results_list = []
        for gallery in container:
            try:
                data = {}
                # Get the link
                link = gallery.find("a", class_="cover")
                data['url'] = urljoin(self.url, link.get('href').strip())
                
                # Get the thumbnail
                img = link.find("img")
                data['poster'] = img.get('data-src') or img.get('src')
                
                # Get the title
                title_elem = gallery.find("div", class_="caption")
                data['title'] = title_elem.text.strip() if title_elem else "Unknown Title"
                
                # Get the ID from URL
                data['id'] = data['url'].split("/")[-2]  # URL format: /g/123456/
                
                results_list.append(data)
            except Exception as e:
                logger.error(f"Error parsing nhentai search result: {e}")
                continue
                
        return results_list

    async def get_chapters(self, data, page: int=1):
        results = data
        content = await self.get(results['url'], headers=self.headers, cs=True)
        if not content:
            return results
            
        bs = BeautifulSoup(content, "html.parser")
        
        # Get description/tags
        tags_container = bs.find("section", id="tags")
        tags = []
        if tags_container:
            for tag_group in tags_container.find_all("div", class_="tag-container"):
                tag_type = tag_group.find("span", class_="name").text.strip()
                tag_items = [a.text.strip() for a in tag_group.find_all("a", class_="tag")]
                tags.append(f"{tag_type}: {', '.join(tag_items)}")
        
        # Get title
        title_elem = bs.find("h1", class_="title")
        title = title_elem.text.strip() if title_elem else results['title']
        
        # Get cover image
        cover_elem = bs.find("div", id="cover")
        cover_img = cover_elem.find("img") if cover_elem else None
        cover_url = cover_img.get('data-src') or cover_img.get('src') if cover_img else results.get('poster', '')
        
        # Build message
        results['msg'] = f"<b>{title}</b>\n\n"
        results['msg'] += f"<b>Tags:</b>\n<blockquote expandable><code>{chr(10).join(tags)}</code></blockquote>\n\n"
        results['msg'] += f"<b>URL:</b> {results['url']}\n"
        
        # Store the gallery ID for getting pictures
        results['gallery_id'] = results['url'].split("/")[-2]
        results['total_pages'] = self._get_total_pages(bs)
        results['cover_url'] = cover_url
        
        return results

    def _get_total_pages(self, bs):
        # Get total number of pages from the thumbnail container
        thumbnails = bs.find("div", id="thumbnail-container")
        if thumbnails:
            return len(thumbnails.find_all("div", class_="thumb-container"))
        return 0

    def iter_chapters(self, data, page: int=1):
        # For nhentai, we treat each gallery as a single "chapter" with multiple pages
        chapters_list = [{
            "title": f"Gallery {data.get('gallery_id', 'Unknown')} - {data.get('total_pages', 0)} pages",
            "url": data['url'],
            "manga_title": data['title'],
            "poster": data.get('cover_url', data.get('poster', '')),
            "gallery_id": data.get('gallery_id', ''),
            "total_pages": data.get('total_pages', 0)
        }]
        
        return chapters_list

    async def get_pictures(self, url, data=None):
        gallery_id = url.split("/")[-2] if "/g/" in url else url.split("/")[-1]
        
        # nhentai API endpoint for getting gallery info
        api_url = f"https://nhentai.net/api/gallery/{gallery_id}"
        response = await self.get(api_url, headers=self.headers, cs=True, rjson=True)
        
        if not response:
            return []
        
        # Construct image URLs from the API response
        image_links = []
        if 'images' in response and 'pages' in response['images']:
            for page in response['images']['pages']:
                # nhentai image URL format: https://i.nhentai.net/galleries/{media_id}/{page_number}.{extension}
                media_id = response['media_id']
                page_num = page['t'] if page['t'] in ['j', 'p', 'g'] else page_num
                extension = page['t']  # j = jpg, p = png, g = gif
                
                image_url = f"https://i.nhentai.net/galleries/{media_id}/{page['n']}.{extension}"
                image_links.append(image_url)
        
        return image_links

    async def get_updates(self, page:int=1):
        # nhentai doesn't have a traditional update system like manga sites
        # We'll get popular or recent galleries instead
        output = []
        
        url = f"https://nhentai.net/?page={page}"
        results = await self.get(url, headers=self.headers, cs=True)
        
        if not results:
            return output
            
        bs = BeautifulSoup(results, "html.parser")
        galleries = bs.find_all("div", class_="gallery")
        
        for gallery in galleries:
            try:
                data = {}
                # Get the link
                link = gallery.find("a", class_="cover")
                data['url'] = urljoin(self.url, link.get('href').strip())
                
                # Get the title
                title_elem = gallery.find("div", class_="caption")
                data['manga_title'] = title_elem.text.strip() if title_elem else "Unknown Title"
                
                # Get the gallery ID for chapter URL
                gallery_id = data['url'].split("/")[-2]
                data['chapter_url'] = data['url']
                data['title'] = f"Gallery {gallery_id}"
                
                output.append(data)
            except Exception as e:
                logger.error(f"Error parsing nhentai update: {e}")
                continue
        
        return output
