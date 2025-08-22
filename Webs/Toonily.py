from .scraper import Scraper
import json 
from bs4 import BeautifulSoup
from loguru import logger


class ToonilyScraper(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://toonily.com"
        self.bg = None
        self.sf = "tn"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        self.search_query = dict()
    
    async def get_information(self, slug, data):
        url = f"{self.url}/webtoon/{slug}/"
        response = await self.get(url, cs=True, headers=self.headers)
        soup = BeautifulSoup(response, "html.parser")
        
        # Extract title
        title_element = soup.find("h1", class_="entry-title")
        title = title_element.text.strip() if title_element else "N/A"
        
        # Extract cover image
        cover_element = soup.find("div", class_="summary_image").find("img")
        cover = cover_element["src"] if cover_element else "N/A"
        
        # Extract description
        desc_element = soup.find("div", class_="summary__content")
        desc = desc_element.text.strip() if desc_element else "N/A"
        
        # Extract genres
        genres_elements = soup.find("div", class_="genres-content").find_all("a")
        genres_list = [genre.text.strip() for genre in genres_elements]
        genres = ", ".join(genres_list) or "N/A"
        
        # Extract status
        status_element = soup.find("div", class_="summary-content", text="Status")
        if status_element:
            status = status_element.find_next_sibling("div").text.strip()
        else:
            status = "N/A"
            
        # Extract authors
        author_element = soup.find("div", class_="author-content")
        authors = author_element.text.strip() if author_element else "N/A"
        
        # Extract rating
        rating_element = soup.find("span", class_="score")
        rating = rating_element.text.strip() if rating_element else "N/A"
        
        # Extract last chapter
        last_chap_element = soup.find("li", class_="wp-manga-chapter").find("a")
        last_chap = last_chap_element.text.strip() if last_chap_element else "N/A"
        
        # Construct message
        msg = f"<b>{title}</b>\n\n"
        msg += f"<b>Rating:</b> <code>{rating}</code>\n"
        msg += f"<b>Genres:</b> <code>{genres}</code>\n"
        msg += f"<b>Last Chapter:</b> <code>{last_chap}</code>\n"
        msg += f"<b>Status:</b> <code>{status}</code>\n"
        msg += f"<b>Authors:</b> <code>{authors}</code>\n"

        su = len(desc) + len(msg)
        if su < 1024:
            msg += f"\n<i>{desc}</i>"
            if len(msg) > 1024:
                msg = msg[:1023]
        else:
            msg += f"\n<b><a href='{url}'>Read more...</a></b>"

        if len(msg) > 1024:
            msg = msg[:1023]
        
        data['msg'] = msg
        data['poster'] = cover
        data['url'] = url
      
    async def search(self, query: str = ""):
        if query.lower() in self.search_query:
            return self.search_query[query.lower()]
        
        url = f"{self.url}/?s={query}&post_type=wp-manga"
        response = await self.get(url, cs=True, headers=self.headers)
        soup = BeautifulSoup(response, "html.parser")
        
        mangas = []
        results = soup.find_all("div", class_="row c-tabs-item__content")
        
        for result in results:
            title_element = result.find("h3").find("a")
            title = title_element.text.strip()
            url = title_element["href"]
            slug = url.split("/")[-2]
            
            image_element = result.find("img")
            poster = image_element["src"] if image_element else "N/A"
            
            mangas.append({
                "title": title,
                "slug": slug,
                "url": url,
                "poster": poster
            })
        
        self.search_query[query.lower()] = mangas
        return mangas
    
    async def get_chapters(self, data, page: int = 1):
        url = f"{self.url}/webtoon/{data['slug']}/ajax/chapters/"
        payload = {
            "action": "manga_get_chapters",
            "manga": data.get("id", data["slug"])
        }
        
        response = await self.post(url, data=payload, headers=self.headers)
        soup = BeautifulSoup(response, "html.parser")
        
        chapters = soup.find_all("li", class_="wp-manga-chapter")
        
        results = {
            "chapters": [],
            "title": data["title"],
            "slug": data["slug"]
        }
        
        for chapter in chapters:
            chapter_link = chapter.find("a")
            chapter_title = chapter_link.text.strip()
            chapter_url = chapter_link["href"]
            chapter_slug = chapter_url.split("/")[-2]
            
            results["chapters"].append({
                "title": chapter_title,
                "url": chapter_url,
                "slug": chapter_slug
            })
        
        await self.get_information(data['slug'], results)
        return results
  
    def iter_chapters(self, data):
        if not data or 'chapters' not in data:
            return []
        
        chapters_list = []
        for chapter in data['chapters']:
            chapters_list.append({
                "title": chapter["title"],
                "url": chapter["url"],
                "slug": chapter["slug"],
                "manga_title": data['title'],
                "poster": data.get('poster', None),
            })
        
        return chapters_list
    
    async def get_pictures(self, url, data=None):
        response = await self.get(url, cs=True, headers=self.headers)
        soup = BeautifulSoup(response, "html.parser")
        
        images = []
        reading_content = soup.find("div", class_="reading-content")
        
        if reading_content:
            img_elements = reading_content.find_all("img")
            images = [img["src"].strip() for img in img_elements if img.get("src")]
        
        return images
    
    async def get_updates(self, page: int = 1):
        output = []
        url = f"{self.url}/page/{page}/"
        
        response = await self.get(url, cs=True, headers=self.headers)
        soup = BeautifulSoup(response, "html.parser")
        
        updates = soup.find_all("div", class_="page-item-detail")
        
        for item in updates:
            title_element = item.find("h3").find("a")
            title = title_element.text.strip()
            manga_url = title_element["href"]
            slug = manga_url.split("/")[-2]
            
            chapter_element = item.find("span", class_="chapter")
            if chapter_element:
                chapter_link = chapter_element.find("a")
                chapter_title = chapter_link.text.strip()
                chapter_url = chapter_link["href"]
                chapter_slug = chapter_url.split("/")[-2]
            else:
                chapter_title = "N/A"
                chapter_url = "N/A"
                chapter_slug = "N/A"
                
            image_element = item.find("img")
            poster = image_element["src"] if image_element else "N/A"
            
            output.append({
                "manga_title": title,
                "url": manga_url,
                "slug": slug,
                "title": chapter_title,
                "chapter_url": chapter_url,
                "poster": poster
            })
        
        return output
