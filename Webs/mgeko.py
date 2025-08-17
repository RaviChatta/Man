from .scraper import Scraper
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote, quote_plus
import re
from loguru import logger
from typing import Dict, List, Optional, Union, Any


class MgekoWebs(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://www.mgeko.cc/"
        self.bg = None
        self.sf = "mgeko"
        self.headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "connection": "keep-alive",
            "host": "www.mgeko.cc",
            "referer": "https://www.mgeko.cc/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

    async def search(self, query: str = "") -> List[Dict[str, str]]:
        url = f"https://www.mgeko.cc/autocomplete?term={quote_plus(query)}"
        mangas = await self.get(url, headers=self.headers)
        if not mangas:
            return []

        bs = BeautifulSoup(mangas, "html.parser")
        cards = bs.find_all("li") if bs else []
        results = []
        
        for card in cards:
            try:
                if not isinstance(card, BeautifulSoup):
                    continue
                    
                link = card.find_next("a")
                img = card.find_next("img")
                
                if not link or not img:
                    continue
                    
                data = {
                    'title': link.get('title', ''),
                    'poster': img.get('src', ''),
                    'url': urljoin(self.url, link.get('href', '')),
                }
                results.append(data)
            except Exception as e:
                logger.debug(f"Error processing search result: {e}")
                continue

        return results

    async def get_chapters(self, data: Dict[str, Any], page: int = 1) -> Dict[str, Any]:
        if not data or 'url' not in data:
            return data
            
        results = data.copy()
        content = await self.get(results['url'], cs=True)
        if not content:
            return results

        bs = BeautifulSoup(content, "html.parser")
        if not bs:
            return results

        msg = f"<b>{results.get('title', '')}</b>\n\n"
        msg += f"<b>Url:</b> {results.get('url', '')}\n\n"
        
        con = bs.find(class_="categories")
        if con:
            genres = ' '.join([
                a.text.strip() 
                for a in con.find_all("a") 
                if a and a.text
            ])
            msg += f"<b>Genres:</b> <code>{genres or 'N/A'}</code>\n"
            
            des = bs.find("p", class_="description")
            description = des.text.strip() if des else "N/A"
            msg += f"<b>Description:</b> <code>{description}</code>"

        results['msg'] = msg
        
        chapters_url = f"{results['url']}all-chapters/"
        chapters = await self.get(chapters_url, headers=self.headers)
        results['chapters'] = chapters if chapters else None
        
        return results

    def iter_chapters(self, data: Dict[str, Any], page: int = 1) -> List[Dict[str, str]]:
        chapters_list = []
        if not data or 'chapters' not in data or not data['chapters']:
            return chapters_list

        bs = BeautifulSoup(data['chapters'], "html.parser")
        ul = bs.find('div', {'id': 'chpagedlist'}) if bs else None
        lis = ul.find_all('li') if ul else []

        for card in lis:
            try:
                link = card.find_next("a")
                if not link:
                    continue
                    
                chapter_slug = link.get('title', '')
                chapter_search = re.search(
                    r"chapter-([\d]+(?:\.[\d]+)?)\-([\w-]+)", 
                    chapter_slug
                )
                
                if chapter_search:
                    chapter_text = f"{chapter_search.group(1)}-{chapter_search.group(2)}"
                else:
                    chapter_text = chapter_slug
                
                chapters_list.append({
                    "title": chapter_text,
                    "url": urljoin(self.url, link.get('href', '')),
                    "manga_title": data.get('title', ''),
                    "poster": data.get('poster'),
                })
            except Exception as e:
                logger.debug(f"Error processing chapter: {e}")
                continue

        if page != 1:
            start = (page - 1) * 60
            end = page * 60
            return chapters_list[start:end]
        return chapters_list

    async def get_pictures(self, url: str, data: Optional[Dict] = None) -> List[str]:
        content = await self.get(url, headers=self.headers)
        if not content:
            return []

        bs = BeautifulSoup(content, "html.parser")
        ul = bs.find("div", {"id": "chapter-reader"}) if bs else None
        images = ul.find_all('img') if ul else []
        
        return [
            quote(img.get('src', ''), safe=':/%') 
            for img in images 
            if img and img.get('src')
        ]

    async def get_updates(self, page: int = 1) -> List[Dict[str, str]]:
        output = []
        max_pages = 3
        
        while page <= max_pages:
            url = f"https://www.mgeko.cc/jumbo/manga/?results={page}&filter=All"
            try:
                content = await self.get(url, cs=True, headers=self.headers)
            except Exception as e:
                logger.debug(f"Error fetching updates page {page}: {e}")
                content = None

            if not content:
                page += 1
                continue

            bs = BeautifulSoup(content, "html.parser")
            lis = bs.find_all('li', class_='novel-item') if bs else []
            
            for card in lis:
                try:
                    rdata = card.find_next("a")
                    if not rdata:
                        continue
                        
                    data = {
                        'url': urljoin(self.url, rdata.get('href', '')),
                        'manga_title': '',
                        'poster': '',
                        'chapter_url': '',
                        'title': '',
                    }
                    
                    h4 = rdata.find_next("h4")
                    if h4 and h4.text:
                        data['manga_title'] = h4.text.strip()
                        
                    img = card.find_next("img")
                    if img and img.get('data-src'):
                        data['poster'] = img['data-src']
                    
                    h5 = rdata.find_next("h5")
                    if h5 and h5.text:
                        chapter_title = h5.text.strip()
                        chapter_search = re.search(
                            r"chapter-([\d]+(?:\.[\d]+)?)\-([\w-]+)", 
                            chapter_title
                        )
                        if chapter_search:
                            data['title'] = f"{chapter_search.group(1)}-{chapter_search.group(2)}"
                        else:
                            data['title'] = chapter_title
                    
                    chapter_url = f"{data['url']}all-chapters/"
                    content = await self.get(chapter_url, headers=self.headers)
                    if content:
                        bs_chapter = BeautifulSoup(content, "html.parser")
                        ul = bs_chapter.find('div', {'id': 'chpagedlist'}) if bs_chapter else None
                        li = ul.find('li') if ul else None
                        if li:
                            link = li.find_next("a")
                            if link and link.get('href'):
                                data['chapter_url'] = urljoin(self.url, link['href'])
                    
                    output.append(data)
                except Exception as e:
                    logger.debug(f"Error processing update item: {e}")
                    continue
                    
            page += 1 
            
        return output
