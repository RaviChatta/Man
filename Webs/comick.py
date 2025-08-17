from .scraper import Scraper
import json 
from bs4 import BeautifulSoup
from loguru import logger
from typing import Dict, List, Optional, Union


class ComickWebs(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://comick.app"
        self.bg = None
        self.sf = "ck"
        self.headers = {
            "Accept": "application/json",
            "Referer": "https://comick.cc",
            "User-Agent": "Tachiyomi Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Mobile Safari/537.36",
        }
        self.search_query: Dict[str, List[Dict]] = {}
    
    async def get_information(self, slug: str, data: Dict) -> None:
        url = f"https://api.comick.fun/comic/{slug}/?t=0"
        series = await self.get(url, cs=True, rjson=True, headers=self.headers)
        
        if not series or "comic" not in series:
            logger.error(f"Failed to get information for slug: {slug}")
            return

        comic = series["comic"]
        title = comic.get("title", "N/A")
        status = comic.get("status", 0)
        status_map = {1: "Ongoing", 2: "Completed", 3: "Cancelled", 4: "On Hiatus"}
        status = status_map.get(status, "N/A")
        rating = comic.get("bayesian_rating", "N/A")
        
        cover_key = comic.get("md_covers", [{}])[0].get("b2key", "")
        cover = f"https://meo.comick.pictures/{cover_key}" if cover_key else "N/A"
        url = f"https://comick.io/comic/{slug}"
        data['url'] = url
        
        genres_list = [
            genre["md_genres"]["name"] 
            for genre in comic.get("md_comic_md_genres", [])
            if "md_genres" in genre
        ] if "md_comic_md_genres" in comic else []
        genres = ", ".join(genres_list) if genres_list else "N/A"
        
        desc = comic.get("desc", "N/A")
        desc = desc if desc else "N/A"

        last_chap = comic.get("last_chapter", "N/A")
        content_rating = comic.get("content_rating", "").capitalize() or "N/A"
        year = comic.get("year", "N/A")
        
        authors_list = [a.get("name", "") for a in series.get("authors", [])]
        authors = ", ".join(filter(None, authors_list)) or "N/A"
        artist_list = [a.get("name", "") for a in series.get("artists", [])]
        artists = ", ".join(filter(None, artist_list)) or "N/A"

        msg = f"<b>{title} (<code>{year}</code>)</b>\n\n"
        msg += f"<b>Rating:</b> <code>{rating}</code>\n"
        msg += f"<b>Genres:</b> <code>{genres}</code>\n"
        msg += f"<b>Last Chapter:</b> <code>{last_chap}</code>\n"
        msg += f"<b>Status:</b> <code>{status}</code>\n"
        msg += f"<b>Authors:</b> <code>{authors}</code>\n"
        if authors != artists:
            msg += f"<b>Artists:</b> <code>{artists}</code>\n"

        su = len(desc) + len(msg)
        if su < 1024:
            msg += f"\n<i>{desc}</i>"
            if len(msg) > 1024:
                msg = msg[:1023]
        else:
            msg += f"\n<b><a href='{url}'>..</a></b></i>"

        if len(msg) > 1024:
            msg = msg[:1023]
        
        data['msg'] = msg
        data['poster'] = cover
      
    async def search(self, query: str = "") -> List[Dict]:
        query_lower = query.lower()
        if query_lower in self.search_query:
            return self.search_query[query_lower]
    
        url = f"https://api.comick.fun/v1.0/search/?type=comic&page=1&limit=8&q={query}&t=false"
        mangas = await self.get(url, cs=True, rjson=True, headers=self.headers)
        if not isinstance(mangas, list):
            return []

        results = []
        for manga in mangas:
            if not isinstance(manga, dict):
                continue
                
            slug = manga.get("slug", "")
            if not slug:
                continue
                
            url = f"https://comick.io/comic/{slug}"
            file_key = manga.get("md_covers", [{}])[0].get("b2key", "")
            images = f"https://meo.comick.pictures/{file_key}" if file_key else ""
            
            manga_info = {
                'url': url,
                'poster': images,
                'title': manga.get("title", ""),
                'slug': slug,
                'hid': manga.get("hid", ""),
            }
            results.append(manga_info)
    
        self.search_query[query_lower] = results
        return results
    
    async def get_chapters(self, data: Dict, page: int = 1) -> Dict:
        results = {}
        if not data or 'hid' not in data:
            return results
            
        url = f"https://api.comick.fun/comic/{data['hid']}/chapters?lang=en&page={str(page)}"
        results = await self.get(url, cs=True, rjson=True, headers=self.headers)
        
        if results and isinstance(results, dict):
            await self.get_information(data.get('slug', ''), results)
            results['title'] = data.get('title', '')
        
        return results
  
    def iter_chapters(self, data: Dict) -> List[Dict]:
        if not data or not isinstance(data, dict) or 'chapters' not in data:
            return []
    
        chapters_list = []
        for chapter in data['chapters']:
            if not isinstance(chapter, dict):
                continue
                
            chap_num = chapter.get("chap", "")
            title = chapter.get("title", "")
            title = f"{chap_num} - {title}" if title else f"Chapter {chap_num}"
            
            md_group = None
            if "group_name" in chapter:
                if isinstance(chapter["group_name"], list) and chapter["group_name"]:
                    md_group = chapter["group_name"][0]
                elif isinstance(chapter["group_name"], str):
                    md_group = chapter["group_name"]
                    
            title = f"{title} ({md_group})" if md_group else title
            
            chapter_info = {
                "title": title,
                "url": f"{data.get('url', '')}/{chapter.get('hid', '')}-chapter-{chap_num}-en",
                "slug": chapter.get('hid', ''),
                "manga_title": data.get('title', ''),
                "group_name": md_group,
                "poster": data.get('poster'),
            }
            chapters_list.append(chapter_info)
    
        return chapters_list
    
    async def get_pictures(self, url: str, data: Optional[Dict] = None) -> List[str]:
        response = await self.get(url, cs=True, headers=self.headers)
        if not response:
            return []
            
        bs = BeautifulSoup(response, "html.parser")
        container = bs.find("script", {"id": "__NEXT_DATA__"})
        if not container:
            return []

        try:
            con = json.loads(container.text.strip())
            chapter_data = con.get("props", {}).get("pageProps", {}).get("chapter", {})
            images = chapter_data.get("md_images", [])
            return [f"https://meo.comick.pictures/{image.get('b2key', '')}" for image in images if image.get("b2key")]
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON data")
            return []

    async def get_updates(self, page: int = 1) -> List[Dict]:
        output = []
        max_pages = 5
        
        while page <= max_pages:
            url = f"https://api.comick.fun/chapter?page={page}&device-memory=8&order=new"
            results = await self.get(url, cs=True, rjson=True, headers=self.headers)
            
            if not isinstance(results, list):
                break
                
            for data in results:
                if not isinstance(data, dict) or "md_comics" not in data:
                    continue
                    
                comic = data["md_comics"]
                slug = comic.get("slug", "")
                if not slug:
                    continue
                    
                url = f"https://comick.io/comic/{slug}"
                cover = comic.get('md_covers', [{}])[0].get('b2key', '')
                images = f"https://meo.comick.pictures/{cover}" if cover else ""
                chapter_url = f"{url}/{data.get('hid', '')}-chapter-{data.get('chap', '')}-en"
                
                update_data = {
                    'poster': images,
                    'chapter_url': chapter_url,
                    'url': url,
                    'manga_title': comic.get('title', ''),
                    'title': f"Chapter {data.get('chap', '')}",
                    'hid': data.get('hid', ''),
                    'slug': slug,
                }
                output.append(update_data)
            
            page += 1
            
        return output
