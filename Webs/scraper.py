import requests
from cloudscraper import create_scraper
from asyncio import to_thread

class Scraper:
    def __init__(self):
        self.scraper = create_scraper()
        # Default headers for non-cloudscraper requests
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/116.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }

    async def get(self, url, rjson=False, cs=False, headers=None, *args, **kwargs):
        # Merge headers with defaults
        final_headers = self.default_headers.copy()
        if headers:
            final_headers.update(headers)

        try:
            if cs:
                # Use cloudscraper
                response = await to_thread(self.scraper.get, url, headers=final_headers, *args, **kwargs)
            else:
                # Normal requests
                response = await to_thread(requests.get, url, headers=final_headers, *args, **kwargs)
                response.raise_for_status()

            if response.status_code == 200:
                return response.json() if rjson else response.text
            else:
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] GET request failed: {e}")
            return None

    async def post(self, url, rjson=False, cs=False, headers=None, *args, **kwargs):
        final_headers = self.default_headers.copy()
        if headers:
            final_headers.update(headers)

        try:
            if cs:
                response = await to_thread(self.scraper.post, url, headers=final_headers, *args, **kwargs)
            else:
                response = await to_thread(requests.post, url, headers=final_headers, *args, **kwargs)
                response.raise_for_status()

            if response.status_code == 200:
                return response.json() if rjson else response.text
            else:
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] POST request failed: {e}")
            return None
