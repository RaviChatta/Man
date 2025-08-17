from .scraper import Scraper, to_thread
import json
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin, quote, quote_plus, urlencode
import re
from loguru import logger
import asyncio
from typing import Dict, List, Optional, Union, Any


class WeebCentralWebs(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://weebcentral.com/"
        self.bg = None
        self.sf = "weebc"
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "weebcentral.com",
            "HX-Request": "true",
            "Origin": "https://weebcentral.com",
            "Referer": "https://weebcentral.com/",
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Windows",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

    async def search(self, query: str = "") -> List[Dict[str, str]]:
        results = []
        request_url = "https://weebcentral.com/search/simple?location=main"
        params = {"text": query}
        
        headers = self.headers.copy()
        headers.update({
            "Content-Length": str(len(query)),
            "HX-Current-URL": "https://weebcentral.com/",
            "HX-Target": "quick-search-result",
            "HX-Trigger": "quick-search-input",
            "HX-Trigger-Name": "text",
        })
        
        try:
            content = await to_thread(self.scraper.post, request_url, data=params, headers=headers)
            if content.status_code == 200:
                bs = BeautifulSoup(content.text, "html.parser")
                cards = bs.find_all("a")
                
                for card in cards:
                    if not isinstance(card, Tag):
                        continue
                        
                    try:
                        href = card.get('href', '').strip()
                        if not href:
                            continue
                            
                        img = card.find("img")
                        title_div = card.find("div")
                        
                        if not img or not title_div:
                            continue
                            
                        data = {
                            'url': urljoin(self.url, href),
                            'poster': img.get('src', '').strip(),
                            'title': title_div.get_text(strip=True),
                        }
                        results.append(data)
                    except Exception as e:
                        logger.debug(f"Error processing search card: {e}")
                        continue
        except Exception as e:
            logger.error(f"Search request failed: {e}")
            
        return results

    async def get_chapters(self, data: Dict[str, Any], page: int = 1) -> Dict[str, Any]:
        if not data or 'url' not in data:
            return data
            
        results = data.copy()
        try:
            chapters = await self.get(data['url'], cs=True)
            if not chapters:
                return results
                
            bs = BeautifulSoup(chapters, "html.parser")
            if not bs:
                return results
                
            tags_section = bs.find(class_="flex flex-col gap-4")
            msg = f"<b>{data.get('title', '')}</b>\n\n"
            
            if tags_section:
                tags = tags_section.find_all("li")
                for tag in tags:
                    if not isinstance(tag, Tag):
                        continue
                        
                    tag_front = tag.find("strong")
                    tag_back_spans = tag.find_all("span")
                    
                    if tag_front and tag_back_spans:
                        front_text = tag_front.get_text(strip=True)
                        back_text = ' '.join(span.get_text(strip=True) for span in tag_back_spans)
                        msg += f"<b>{front_text}</b> <code>{back_text}</code>\n"
            
            desc_section = bs.find("section", class_="md:w-8/12 flex flex-col gap-4")
            des = None
            if desc_section:
                des_div = desc_section.find(class_="flex flex-col gap-4")
                if des_div:
                    des_li = des_div.find("li")
                    if des_li:
                        des = des_li.get_text(strip=True)
            
            msg += f"<b>Description:</b> <code>{des or 'N/A'}</code>\n"
            results['msg'] = msg
            
            # Get full chapter list
            link_parts = data['url'].split("/")
            new_link = "/".join(link_parts[:-1]) + "/full-chapter-list"
            
            try:
                chapters = await self.get(new_link, cs=True)
                if chapters:
                    bs_chapters = BeautifulSoup(chapters, "html.parser")
                    results['chapters'] = bs_chapters.find_all(
                        "a", 
                        class_="hover:bg-base-300 flex-1 flex items-center p-2"
                    )
            except Exception as e:
                logger.debug(f"Error getting full chapter list: {e}")
                
        except Exception as e:
            logger.error(f"Error in get_chapters: {e}")
            
        return results

    def iter_chapters(self, data: Dict[str, Any], page: int = 1) -> List[Dict[str, str]]:
        chapters_list = []
        
        if not data or 'chapters' not in data:
            return chapters_list
            
        params = {
            'is_prev': 'False',
            'current_page': '1',
            'reading_style': 'long_strip'
        }
        
        for card in data['chapters']:
            if not isinstance(card, Tag):
                continue
                
            try:
                title_span = card.find('span', string=lambda text: text and (
                    "Ch" in text or "Ep" in text or "Vol" in text or "#" in text or "Mi" in text
                ))
                
                if not title_span or not card.get('href'):
                    continue
                    
                chapters_list.append({
                    "title": title_span.get_text(strip=True),
                    "url": f"{card['href']}/images?{urlencode(params)}",
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
        return chapters_list

    async def get_pictures(self, url: str, data: Optional[Dict] = None) -> List[str]:
        image_links = []
        if not url:
            return image_links
            
        try:
            url = url.replace("%C2%", "&")
            response = await self.get(url, cs=True)
            if not response:
                return image_links
                
            bs = BeautifulSoup(response, "html.parser")
            for img_tag in bs.find_all("img"):
                img_src = img_tag.get('src')
                if img_src and ("manga" in img_src or img_src != '/static/images/brand.png'):
                    image_links.append(img_src)
        except Exception as e:
            logger.error(f"Error getting pictures: {e}")
            
        return image_links

    async def get_updates(self, page: int = 1) -> List[Dict[str, str]]:
        output = []
        max_pages = 3
        
        while page <= max_pages:
            url = f"https://weebcentral.com/latest-updates/{page}"
            try:
                content = await self.get(url, cs=True)
                if not content:
                    page += 1
                    continue
                    
                bs = BeautifulSoup(content, "html.parser")
                cards = bs.find_all("article")
                
                for card in cards:
                    if not isinstance(card, Tag):
                        continue
                        
                    try:
                        data = {
                            'manga_title': card.get("data-tip", ""),
                            'url': "",
                            'chapter_url': "",
                            'title': "",
                        }
                        
                        first_link = card.find("a")
                        if first_link:
                            data['url'] = first_link.get('href', '')
                            
                            second_link = first_link.find_next("a")
                            if second_link:
                                data['chapter_url'] = second_link.get('href', '')
                        
                        title_span = card.find("span")
                        if title_span:
                            data['title'] = title_span.get_text(strip=True)
                            
                        if data['url'] or data['chapter_url']:
                            output.append(data)
                    except Exception as e:
                        logger.debug(f"Error processing update card: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error getting updates page {page}: {e}")
                
            page += 1
            
        return output
