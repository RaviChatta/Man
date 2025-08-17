from .scraper import Scraper
import json
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin, quote, quote_plus
import re
from loguru import logger
from typing import Dict, List, Optional, Union, Any


class TempleToonsWebs(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://templetoons.com/"
        self.api_url = "https://api.templetoons.com/api/allComics"
        self.bg = None
        self.sf = "tt1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

    async def search(self, query: str = "") -> List[Dict[str, str]]:
        results = []
        try:
            mangas = await self.get(self.api_url, cs=True, rjson=True)
            if not isinstance(mangas, list):
                return results
                
            query_lower = query.lower()
            for card in mangas:
                if not isinstance(card, dict):
                    continue
                    
                title = card.get('title', '')
                if query_lower in title.lower():
                    series_slug = card.get('series_slug', '')
                    if not series_slug:
                        continue
                        
                    data = {
                        'title': title,
                        'poster': card.get('thumbnail', ''),
                        'url': f"{self.url}comic/{series_slug}",
                    }
                    results.append(data)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            
        return results

    async def get_chapters(self, data: Dict[str, Any], page: int = 1) -> Dict[str, Any]:
        results = data.copy()
        if 'url' not in results:
            return results
            
        try:
            content = await self.get(results['url'], cs=True)
            if not content:
                return results
                
            bs = BeautifulSoup(content, "html.parser")
            if not bs:
                return results
                
            con = bs.find(class_="px-5 py-7 rounded-b-xl text-white/90 shadow-red-400 shadow-md bg-black/50")
            msg = f"<b>{results.get('title', '')}</b>\n\n"
            msg += f"<b>Url:</b> {results.get('url', '')}\n\n"
            
            if con:
                for p in con.find_all("p"):
                    if p and p.text:
                        msg += p.text.strip() + "\n\n"

            results['msg'] = msg
            results['chapters'] = bs.find_all(
                "a", 
                class_="col-span-full sm:col-span-3 lg:col-span-2 flex flex-row gap-2 bg-[#131212] rounded-lg h-[90px] overflow-hidden"
            )
        except Exception as e:
            logger.error(f"Error getting chapters: {e}")
            
        return results

    def iter_chapters(self, data: Dict[str, Any], page: int = 1) -> List[Dict[str, str]]:
        chapters_list = []
        if not data or 'chapters' not in data or not data['chapters']:
            return chapters_list
            
        try:
            for card in data['chapters']:
                if not isinstance(card, Tag) or not card.get('href'):
                    continue
                    
                href = card['href'].strip("/")
                chapter_slug = href.split("/")[-1]
                url_parts = data.get('url', '').split("/")
                series_slug = url_parts[-1] if url_parts else ''
                
                title_element = card.find("h1", class_="text-sm md:text-normal")
                title = title_element.get_text(strip=True) if title_element else "Chapter"
                
                chapters_list.append({
                    "title": title,
                    "url": f"{self.url}comic/{series_slug}/{chapter_slug}",
                    "manga_title": data.get('title', ''),
                    "poster": data.get('poster'),
                })
                
            if page != 1:
                start = (page - 1) * 60
                end = page * 60
                return chapters_list[start:end]
        except Exception as e:
            logger.error(f"Error iterating chapters: {e}")
            
        return chapters_list

    async def get_pictures(self, url: str, data: Optional[Dict] = None) -> List[str]:
        images_urls = []
        if not url:
            return images_urls
            
        try:
            response = await self.get(url, cs=True)
            if not response:
                return images_urls
                
            bs = BeautifulSoup(response, 'html.parser')
            imgs_tags = bs.find("script", string=lambda text: text and "images" in text)
            if not imgs_tags or not imgs_tags.text:
                return images_urls
                
            # Clean up the script content
            script_content = imgs_tags.text.strip()
            cleaned_content = script_content
            for char in ['\n', '\\', '"self.__next_f.push(', ')', '"']:
                cleaned_content = cleaned_content.replace(char, ' ')
                
            # Find image URLs
            pattern = r'https?://[^\s"]+\.(?:jpg|jpeg|png|webp)'
            image_links = re.findall(pattern, cleaned_content)
            
            for img_url in image_links:
                if len(img_url.split('/')) > 8:  # Basic URL validation
                    images_urls.append(img_url)
        except Exception as e:
            logger.exception(f"Error processing images: {e}")
            
        return images_urls

    async def get_updates(self, page: int = 1) -> List[Dict[str, str]]:
        output = []
        try:
            results = await self.get(self.api_url, cs=True, rjson=True)
            if not isinstance(results, list):
                return output
                
            for data in results:
                if not isinstance(data, dict):
                    continue
                    
                try:
                    series_slug = data.get("series_slug", "")
                    if not series_slug:
                        continue
                        
                    chapters = data.get("Chapter", [])
                    if not chapters or not isinstance(chapters, list):
                        continue
                        
                    first_chapter = chapters[0] if isinstance(chapters[0], dict) else {}
                    chapter_slug = first_chapter.get("chapter_slug", "")
                    chapter_name = first_chapter.get("chapter_name", "Chapter")
                    
                    rdata = {
                        'url': f'{self.url}comic/{series_slug}',
                        'manga_title': data.get('title', ''),
                        'chapter_url': f'{self.url}comic/{series_slug}/{chapter_slug}',
                        'title': chapter_name,
                        'poster': data.get('thumbnail', ''),
                    }
                    output.append(rdata)
                except Exception as e:
                    logger.debug(f"Skipping invalid chapter data: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            
        return output
