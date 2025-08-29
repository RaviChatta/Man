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
                    logger.warning(f"Non-200 status code {response.status_code} for {url}")
                    return None
                    
            except HTTPError as e:
                logger.warning(f"HTTP error {e.response.status_code} for {url} (attempt {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Failed after {retries} attempts for {url}")
                return None  # Return None instead of raising exception
                
            except RequestException as e:
                logger.warning(f"Request exception for {url}: {e} (attempt {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Failed after {retries} attempts for {url}")
                return None  # Return None instead of raising exception
                
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}")
                return None  # Return None for any other unexpected errors
    
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
                    logger.warning(f"Non-200 status code {response.status_code} for {url}")
                    return None
                    
            except HTTPError as e:
                logger.warning(f"HTTP error {e.response.status_code} for {url} (attempt {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Failed after {retries} attempts for {url}")
                return None  # Return None instead of raising exception
                
            except RequestException as e:
                logger.warning(f"Request exception for {url}: {e} (attempt {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Failed after {retries} attempts for {url}")
                return None  # Return None instead of raising exception
                
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}")
                return None  # Return None for any other unexpected errors
