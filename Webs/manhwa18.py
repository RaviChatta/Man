from .scraper import Scraper
import json
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin, quote, quote_plus
import re
from loguru import logger
from typing import Dict, List, Optional, Union, Any


class Manhwa18Webs(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://manhwa18.cc/"
        self.bg = None
        self.sf = "ma18"
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

    async def search(self, query: str = "") -> List[Dict[str, str]]:
        url = f"https://manhwa18.cc/search?q={quote_plus(query)}"
        results = []
        
        try:
            mangas = await self.get(url)
            if not mangas:
                return results
                
            bs = BeautifulSoup(mangas, "html.parser")
            container = bs.find('div', {'class': 'manga-lists'}) if bs else None
            cards = container.find_all("div", {"class": "manga-item"}) if container else []
            
            for card in cards:
                try:
                    if not isinstance(card, Tag):
                        continue
                        
                    link = card.find("a")
                    img = card.find("img")
                    
                    if not link or not img:
                        continue
                        
                    data = {
                        'url': urljoin(self.url, link.get("href", "")),
                        'title': link.get("title", ""),
                        'poster': img.get("src", ""),
                    }
                    results.append(data)
                except Exception as e:
                    logger.debug(f"Error processing search card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Search failed: {e}")
            
        return results

    async def get_chapters(self, data: Dict[str, Any], page: int = 1) -> Dict[str, Any]:
        results = data.copy()
        if 'url' not in results:
            return results
            
        try:
            content = await self.get(results['url'])
            if not content:
                return results
                
            bs = BeautifulSoup(content, "html.parser")
            if not bs:
                return results
                
            # Get genres
            container = bs.find(class_="genres-content")
            geners = container.get_text(strip=True) if container else "N/A"
            
            msg = f"<b>{results.get('title', '')}</b>\n"
            msg += f"<b>Url</b>: {results.get('url', '')}\n"
            msg += f"<b>Genres</b>: <code>{geners}</code>\n\n"
            
            # Get description
            container = bs.find(class_="dsct")
            des = container.get_text(strip=True) if container else "N/A"
            msg += f"<b>Description</b>: <code>{des}</code>\n"
            
            results['msg'] = msg
            
            # Get chapters
            chapters_container = bs.find("ul", {"class": "row-content-chapter"})
            chapters = chapters_container.find_all("li", {"class": "a-h"}) if chapters_container else []
            results['chapters'] = chapters
            
        except Exception as e:
            logger.error(f"Error getting chapters: {e}")
            
        return results

    def iter_chapters(self, data: Dict[str, Any], page: int = 1) -> List[Dict[str, str]]:
        chapters_list = []
        if not data or 'chapters' not in data:
            return chapters_list
            
        try:
            for card in data['chapters']:
                if not isinstance(card, Tag):
                    continue
                    
                try:
                    link = card.find("a")
                    if not link:
                        continue
                        
                    chapters_list.append({
                        "title": link.get_text(strip=True),
                        "url": urljoin(self.url, link.get('href', '')),
                        "manga_title": data.get('title', ''),
                        "poster": data.get('poster'),
                    })
                except Exception as e:
                    logger.debug(f"Error processing chapter card: {e}")
                    continue
                    
            if page != 1:
                start = (page - 1) * 60
                end = page * 60
                return chapters_list[start:end]
                
        except Exception as e:
            logger.error(f"Error iterating chapters: {e}")
            
        return chapters_list

    async def get_pictures(self, url: str, data: Optional[Dict] = None) -> List[str]:
        images_url = []
        if not url:
            return images_url
            
        try:
            content = await self.get(url)
            if not content:
                return images_url
                
            bs = BeautifulSoup(content, "html.parser")
            container = bs.find("div", {"class": "read-content wleft tcenter"})
            cards = container.find_all("img") if container else []
            
            images_url = [
                quote(img.get("src", ""), safe=':/%') 
                for img in cards 
                if img and img.get("src")
            ]
            
        except Exception as e:
            logger.error(f"Error getting pictures: {e}")
            
        return images_url

    async def get_updates(self, page: int = 1) -> List[Dict[str, str]]:
        output = []
        max_pages = 2
        
        while page <= max_pages:
            url = f"https://manhwa18.cc/page/{page}/"
            try:
                content = await self.get(url)
                if not content:
                    page += 1
                    continue
                    
                bs = BeautifulSoup(content, "html.parser")
                cards = bs.find_all("div", {"class": "data wleft"}) if bs else []
                
                for card in cards:
                    try:
                        if not isinstance(card, Tag):
                            continue
                            
                        data = {
                            'url': '',
                            'manga_title': '',
                            'title': '',
                            'chapter_url': '',
                        }
                        
                        # Get main link
                        main_link = card.find("a")
                        if main_link:
                            data['url'] = urljoin(self.url, main_link.get("href", ""))
                            data['manga_title'] = main_link.get("title", "")
                        
                        # Get chapter link
                        span_tag = card.find("a", class_="btn-link")
                        if span_tag:
                            data['title'] = span_tag.get_text(strip=True)
                            chapter_link = span_tag.find("a")
                            if chapter_link:
                                data['chapter_url'] = urljoin(self.url, chapter_link.get('href', ''))
                        
                        if data['url'] or data['chapter_url']:
                            output.append(data)
                    except Exception as e:
                        logger.debug(f"Error processing update card: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error getting updates page {page}: {e}")
                
            page += 1
            
        return output
