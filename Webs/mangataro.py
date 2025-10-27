from .scraper import Scraper
import json
import re
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup
from loguru import logger

class MangaTaroWebs(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://mangataro.org/"
        self.sf = "mangataro"
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

    async def search(self, query: str = ""):
        search_url = f"{self.url}search"
        params = {
            'word': query,
            'type': 'comic'
        }
        
        content = await self.get(search_url, params=params)
        results = []
        
        if content:
            bs = BeautifulSoup(content, "html.parser")
            
            # Look for manga entries in search results
            manga_items = bs.find_all('a', href=re.compile(r'/detail/'))
            
            for item in manga_items:
                try:
                    title = item.get('title', '') or (item.find('img') and item.find('img').get('alt', ''))
                    url = urljoin(self.url, item.get('href'))
                    poster = item.find('img')
                    poster_url = poster.get('src') if poster else None
                    
                    if poster_url and not poster_url.startswith('http'):
                        if poster_url.startswith('//'):
                            poster_url = 'https:' + poster_url
                        else:
                            poster_url = urljoin(self.url, poster_url)
                    
                    if title and url:
                        results.append({
                            "title": title.strip(),
                            "url": url,
                            "poster": poster_url
                        })
                except Exception as e:
                    logger.warning(f"Error parsing search result: {e}")
                    continue
        
        return results

    async def get_chapters(self, data, page: int = 1):
        results = data
        content = await self.get(results['url'])
        
        if not content:
            return results

        bs = BeautifulSoup(content, "html.parser")
        
        # Extract title
        title_elem = bs.find('h1')
        title = title_elem.text.strip() if title_elem else results['title']
        
        # Extract description/summary
        summary_elem = bs.find('div', class_=re.compile(r'summary'))
        description = summary_elem.text.strip() if summary_elem else "No Description Available."
        
        # Extract metadata
        status = "Unknown"
        genres = []
        authors = "Unknown"
        
        info_items = bs.find_all('div', class_=re.compile(r'info-item'))
        for item in info_items:
            label = item.find('span')
            value = label.find_next_sibling('span') if label else None
            if label and value:
                label_text = label.text.strip().lower()
                value_text = value.text.strip()
                
                if 'status' in label_text:
                    status = value_text
                elif 'author' in label_text:
                    authors = value_text
                elif 'genres' in label_text:
                    genres = [genre.strip() for genre in value_text.split(',')]
        
        # Extract genres from dedicated genres section
        genres_elem = bs.find('div', class_=re.compile(r'genres'))
        if genres_elem:
            genre_links = genres_elem.find_all('a')
            genres = [link.text.strip() for link in genre_links]
        
        msg = f"<b>{title}</b>\n"
        msg += f"<b>Url</b>: {results['url']}\n"
        msg += f"<b>Status</b>: <code>{status}</code>\n"
        msg += f"<b>Genres</b>: <code>{', '.join(genres) if genres else 'N/A'}</code>\n"
        msg += f"<b>Authors</b>: <code>{authors}</code>\n\n"
        msg += f"<b>Description</b>: <code>{description[:300]}...</code>\n"

        results['msg'] = msg
        
        # Extract chapters
        chapters = []
        chapter_links = bs.find_all('a', href=re.compile(r'/read/'))
        
        for link in chapter_links:
            chapter_url = urljoin(self.url, link.get('href'))
            chapter_title_elem = link.find('span') or link
            chapter_title = chapter_title_elem.text.strip()
            
            chapters.append({
                "title": chapter_title,
                "url": chapter_url
            })
        
        results['chapters'] = chapters[::-1]  # Reverse to show latest first
        return results

    def iter_chapters(self, data, page: int = 1):
        chapters_list = []

        if 'chapters' in data:
            for chapter in data['chapters']:
                chapters_list.append({
                    "title": chapter["title"],
                    "url": chapter["url"],
                    "manga_title": data['title'],
                    "poster": data.get('poster')
                })
        
        return chapters_list[(page - 1) * 60:page * 60] if page != 1 else chapters_list

    async def get_pictures(self, url, data=None):
        content = await self.get(url)
        
        if not content:
            return []

        bs = BeautifulSoup(content, "html.parser")
        images = []
        
        # Method 1: Look for images in reading area
        chapter_imgs = bs.find_all('img', class_=re.compile(r'chapter-img'))
        if not chapter_imgs:
            chapter_imgs = bs.find_all('img', class_=re.compile(r'wp-manga-chapter-img'))
        if not chapter_imgs:
            chapter_imgs = bs.find_all('div', class_=re.compile(r'page-break'))
            for div in chapter_imgs:
                img = div.find('img')
                if img:
                    chapter_imgs = [img]
                    break
        
        for img in chapter_imgs:
            img_src = img.get('src') or img.get('data-src')
            if img_src and not img_src.startswith('data:'):
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif not img_src.startswith('http'):
                    img_src = urljoin(self.url, img_src)
                images.append(img_src)
        
        # Method 2: Look for JavaScript data containing image URLs
        if not images:
            scripts = bs.find_all('script')
            for script in scripts:
                script_content = script.string
                if script_content and 'var images' in script_content:
                    match = re.search(r'var\s+images\s*=\s*(\[.*?\]);', script_content, re.DOTALL)
                    if match:
                        try:
                            images_data = json.loads(match.group(1))
                            for img_data in images_data:
                                if isinstance(img_data, str):
                                    img_src = img_data
                                elif isinstance(img_data, dict) and 'url' in img_data:
                                    img_src = img_data['url']
                                else:
                                    continue
                                    
                                if img_src and not img_src.startswith('data:'):
                                    if img_src.startswith('//'):
                                        img_src = 'https:' + img_src
                                    elif not img_src.startswith('http'):
                                        img_src = urljoin(self.url, img_src)
                                    images.append(img_src)
                        except json.JSONDecodeError:
                            pass
        
        return images

    async def get_updates(self, page: int = 1):
        # MangaTaro updates page
        url = f"{self.url}latest-release" if page == 1 else f"{self.url}latest-release/page/{page}/"
        
        content = await self.get(url)
        output = []
        
        if content:
            bs = BeautifulSoup(content, "html.parser")
            
            # Look for update items
            update_items = bs.find_all('div', class_=re.compile(r'page-item-detail|manga-item'))
            
            for item in update_items:
                try:
                    data = {}
                    
                    # Find manga link
                    manga_link = item.find('a', href=re.compile(r'/detail/'))
                    if manga_link:
                        data['url'] = urljoin(self.url, manga_link.get('href'))
                        data['manga_title'] = manga_link.get('title', '') or (manga_link.find('img') and manga_link.find('img').get('alt', ''))
                    
                    # Find poster
                    img = item.find('img')
                    if img:
                        data['poster'] = img.get('src')
                        if data['poster'] and not data['poster'].startswith('http'):
                            if data['poster'].startswith('//'):
                                data['poster'] = 'https:' + data['poster']
                            else:
                                data['poster'] = urljoin(self.url, data['poster'])
                    
                    # Find latest chapter
                    chapter_link = item.find('a', href=re.compile(r'/read/'))
                    if chapter_link:
                        data['title'] = chapter_link.text.strip()
                        data['chapter_url'] = urljoin(self.url, chapter_link.get('href'))
                    
                    if all(key in data for key in ['url', 'manga_title', 'chapter_url']):
                        output.append(data)
                        
                except Exception as e:
                    logger.warning(f"Error parsing update item: {e}")
                    continue

        return output
