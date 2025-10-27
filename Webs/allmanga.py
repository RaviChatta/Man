from .scraper import Scraper
import json
import re
import requests
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup
from loguru import logger

class AllMangaWebs(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://allmanga.to/"
        self.sf = "allmanga"
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }
        self.api_url = "https://api.allanime.day/api"
        self.api_headers = {
            'authority': 'api.allanime.day',
            'scheme': 'https',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'access-control-allow-origin': '*',
            'Origin': 'https://allanime.to',
            'Referer': 'https://allanime.to/',
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Mobile Safari/537.36'
        }
        self.SEARCH_HASH = "a27e57ef5de5bae714db701fb7b5cf57e13d57938fc6256f7d5c70a975d11f3d"
        self.INFO_HASH = "529b0770601c7e04c98566c7b7bb3f75178930ae18b3084592d8af2b591a009f"
        self.CHAPTER_HASH = "121996b57011b69386b65ca8fc9e202046fc20bf68b8c8128de0d0e92a681195"

    def determine_type(self, country):
        if country == 'JP':
            return 'Manga'
        if country == 'KR':
            return 'Manhwa'
        if country == 'CN':
            return 'Manhua'
        return 'Comic'

    async def search(self, query: str = ""):
        payload = {
            "search": {
                "query": query,
                "isManga": True
            },
            "limit": 24,
            "page": 1,
            "translationType": "sub",
            "countryOrigin": "ALL"
        }
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": self.SEARCH_HASH
            }
        }
        params = {
            "variables": json.dumps(payload),
            "extensions": json.dumps(extensions)
        }
        
        content = await self.get(self.api_url, params=params, headers=self.api_headers, rjson=True)
        results = []
        
        if content:
            edges = content.get("data", {}).get("mangas", {}).get("edges", [])
            for result in edges:
                title = result.get("englishName") or result.get("name") or ""
                manga_id = result.get("_id")
                url = f"https://allmanga.to/manga/{manga_id}"
                thumbnail = result.get("thumbnail", "")
                if thumbnail and not thumbnail.startswith("http"):
                    thumbnail = "https://wp.youtube-anime.com/aln.youtube-anime.com/" + thumbnail
                results.append({
                    "title": title,
                    "url": url,
                    "poster": thumbnail
                })
        return results

    async def get_chapters(self, data, page: int = 1):
        results = data
        manga_url = results['url']
        manga_id = manga_url.rstrip('/').split('/')[-1]
        
        variables = {
            "_id": manga_id,
            "search": {
                "allowAdult": False,
                "allowUnknown": False
            }
        }
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": self.INFO_HASH
            }
        }
        params = {
            "variables": json.dumps(variables),
            "extensions": json.dumps(extensions)
        }
        
        content = await self.get(self.api_url, params=params, headers=self.api_headers, rjson=True)
        
        if not content:
            return results

        data_info = content.get("data", {}).get("manga", {})
        title = data_info.get("englishName") or data_info.get("name") or "Title not found"
        description = data_info.get("description") or "No Description Available."
        description = re.sub(r'<.*?>', '', description)
        status = data_info.get("status") or "Unknown"
        
        raw_genres = data_info.get("genres", [])
        demographic_types = {
            "Manga", "Manhwa", "Manhua", "Webtoon", "Comic",
            "Shounen", "Shoujo", "Seinen", "Josei",
            "Isekai", "Reincarnation", "Transmigration", "Regression",
            "Villainess", "Otome Game", "School Life", "Office Life", "Survival",
            "Post-Apocalyptic", "Tragedy", "Philosophical", "Supernatural", "Magic", "Martial Arts",
            "Historical", "Military", "Sports", "Music", "Cooking",
            "Medical", "Detective", "Crime", "Dystopian", "Gore",
            "Thriller", "Mature", "Adult", "Cyberpunk", "Steampunk", "Vampires", "Zombies",
            "Idol", "Mecha", "Demons", "Angels", "Ghosts",
            "Villain Protagonist", "Anti-Hero", "Revenge",
            "Time Travel", "Parallel World", "Cultivation",
            "Family", "Friendship", "Adventure", "Magic School",
            "Royalty", "Political", "Slice of Life Comedy", "Comedy Drama"
        }
        genres = [g for g in raw_genres if g not in demographic_types]
        genres = ", ".join(genres) if genres else "N/A"
        
        authors = ", ".join(data_info.get("authors", [])[:3]) if data_info.get("authors") else "Unknown"
        
        msg = f"<b>{title}</b>\n"
        msg += f"<b>Url</b>: {manga_url}\n"
        msg += f"<b>Status</b>: <code>{status}</code>\n"
        msg += f"<b>Genres</b>: <code>{genres}</code>\n"
        msg += f"<b>Authors</b>: <code>{authors}</code>\n\n"
        msg += f"<b>Description</b>: <code>{description[:300]}...</code>\n"

        results['msg'] = msg
        
        # Get chapters
        chapters_detail = data_info.get("availableChaptersDetail", {}).get("sub", [])
        chapters = []
        for number in chapters_detail:
            chapters.append({
                "title": f"Chapter {number}",
                "url": f"https://allmanga.to/read/{manga_id}/chapter-{number}-sub"
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
        try:
            parts = url.rstrip("/").split("/")
            manga_id = parts[4]
            chapter_str = parts[5].split("-")[1]
        except Exception:
            return []

        variables = {
            "mangaId": manga_id,
            "translationType": "sub",
            "chapterString": chapter_str,
            "limit": 999999,
            "offset": 0
        }
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": self.CHAPTER_HASH
            }
        }
        params = {
            "variables": json.dumps(variables),
            "extensions": json.dumps(extensions)
        }
        
        content = await self.get(self.api_url, params=params, headers=self.api_headers, rjson=True)
        
        if not content:
            return []

        edges = content.get("data", {}).get("chapterPages", {}).get("edges", [])
        if not edges:
            return []
            
        source = edges[0]
        pic_head = source.get("pictureUrlHead")
        pic_urls = source.get("pictureUrls", [])
        images = []
        for img in pic_urls:
            images.append(f"{pic_head}{img['url']}")
            
        return images

    async def get_updates(self, page: int = 1):
        # AllManga doesn't have a straightforward updates page, return empty for now
        return []
