from .scraper import Scraper
import json

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote_plus

import re
from loguru import logger


class NHentaiWebs(Scraper):
    def __init__(self):
        super().__init__()
        self.url = "https://nhentai.net/"
        self.bg = None
        self.sf = "nhentai"
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

    async def search(self, query: str = ""):
        url = f"{self.url}search/?q={quote_plus(query)}"
        content = await self.get(url)
        bs = BeautifulSoup(content, "html.parser") if content else None

        container = bs.find("div", {"id": "gallery-container"}) if bs else None
        cards = container.find_all("div", class_="gallery") if container else []

        results = []
        for card in cards:
            try:
                a_tag = card.find("a", class_="cover")
                img_tag = card.find("img")

                data = {
                    "url": urljoin(self.url, a_tag.get("href")),
                    "title": img_tag.get("alt") if img_tag else "N/A",
                    "poster": img_tag.get("data-src") if img_tag else None,
                }
                results.append(data)
            except:
                continue
        return results

    async def get_chapters(self, data, page: int = 1):
        # nhentai has no chapters, only "one-shot" galleries
        results = data
        content = await self.get(results["url"])
        bs = BeautifulSoup(content, "html.parser") if content else None

        title_tag = bs.find("h1", class_="title") if bs else None
        title = title_tag.text.strip() if title_tag else results["title"]

        tags_div = bs.find("section", id="tags") if bs else None
        genres = []
        if tags_div:
            for tag in tags_div.find_all("a", class_="tag"):
                genres.append(tag.text.strip())

        msg = f"<b>{title}</b>\n"
        msg += f"<b>Url</b>: {results['url']}\n"
        msg += f"<b>Tags</b>: <code>{', '.join(genres) if genres else 'N/A'}</code>\n"

        results["msg"] = msg
        results["chapters"] = [results["url"]]  # one gallery acts as "chapter"

        return results

    def iter_chapters(self, data, page: int = 1):
        # only one "chapter" (gallery)
        chapters_list = []
        if "chapters" in data:
            for chapter_url in data["chapters"]:
                chapters_list.append({
                    "title": data["title"],
                    "url": chapter_url,
                    "manga_title": data["title"],
                    "poster": data["poster"] if "poster" in data else None,
                })
        return chapters_list

    async def get_pictures(self, url, data=None):
        content = await self.get(url)
        bs = BeautifulSoup(content, "html.parser") if content else None

        container = bs.find("div", id="thumbnail-container") if bs else None
        thumbs = container.find_all("img") if container else []

        images_url = []
        for img in thumbs:
            src = img.get("data-src")
            if src:
                # thumbnails are .../t/... replace with /g/ to get full image
                full = src.replace("//t.", "//i.").replace("t.jpg", ".jpg").replace("t.png", ".png")
                images_url.append(full)

        return images_url

    async def get_updates(self, page: int = 1):
        output = []
        url = f"{self.url}latest/?page={page}"
        try:
            content = await self.get(url)
        except:
            content = None

        if content:
            bs = BeautifulSoup(content, "html.parser")
            cards = bs.find_all("div", class_="gallery")
            for card in cards:
                try:
                    a_tag = card.find("a", class_="cover")
                    img_tag = card.find("img")

                    data = {
                        "url": urljoin(self.url, a_tag.get("href")),
                        "manga_title": img_tag.get("alt") if img_tag else "N/A",
                        "poster": img_tag.get("data-src") if img_tag else None,
                        "title": img_tag.get("alt") if img_tag else "N/A",
                        "chapter_url": urljoin(self.url, a_tag.get("href")),
                    }
                    output.append(data)
                except:
                    continue
        return output
