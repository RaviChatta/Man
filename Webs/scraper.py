import requests
from cloudscraper import create_scraper
from asyncio import to_thread
from requests.exceptions import HTTPError, RequestException
import asyncio
from loguru import logger


class Scraper:
    def __init__(self):
        self.scraper = create_scraper()
        
    async def get(self, url, rjson=None, cs=False, retries=3, *args, **kwargs):
        for attempt in range(retries):
            try:
                if cs:
                    response = await to_thread(self.scraper.get, url, *args, **kwargs)
                else:
                    response = await to_thread(requests.get, url, *args, **kwargs)
                
                response.raise_for_status()
                
                if response.status_code == 200:
                    return response.json() if rjson else response.text
                else:
                    return None
                    
            except HTTPError as e:
                if response.status_code == 403 and attempt < retries - 1:
                    logger.warning(f"403 Forbidden on attempt {attempt + 1}, retrying in {2 ** attempt} seconds...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise e
                
            except RequestException as e:
                if attempt < retries - 1:
                    logger.warning(f"Request failed on attempt {attempt + 1}, retrying in {2 ** attempt} seconds...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise e
    
    async def post(self, url, rjson=None, cs=False, retries=3, *args, **kwargs):
        for attempt in range(retries):
            try:
                if cs:
                    response = await to_thread(self.scraper.post, url, *args, **kwargs)
                else:
                    response = await to_thread(requests.post, url, *args, **kwargs)
                
                response.raise_for_status()
                
                if response.status_code == 200:
                    return response.json() if rjson else response.text
                else:
                    return None
                    
            except HTTPError as e:
                if response.status_code == 403 and attempt < retries - 1:
                    logger.warning(f"403 Forbidden on attempt {attempt + 1}, retrying in {2 ** attempt} seconds...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise e
                
            except RequestException as e:
                if attempt < retries - 1:
                    logger.warning(f"Request failed on attempt {attempt + 1}, retrying in {2 ** attempt} seconds...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise e
