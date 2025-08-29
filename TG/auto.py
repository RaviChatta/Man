from bot import Bot, Vars, logger
from Tools.db import *
from .storage import web_data, clean, retry_on_flood, get_episode_number, queue
from .wks import send_manga_chapter

import asyncio
import os
import shutil


async def get_updates_manga():
    updates = []
    for i in web_data.keys():
        try:
            raw_data = await web_data[i].get_updates()
            if raw_data is None:  # Handle case where get_updates returns None due to errors
                continue
                
            for data in raw_data:
                if data['url'] in dts:
                    episode_number = str(get_episode_number(data['title']))
                    
                    if 'Lastest' in dts[data['url']]:
                        try: 
                            data_ep_num = int(dts[data['url']]['Lastest'])
                        except: 
                            data_ep_num = float(dts[data['url']]['Lastest'])
                        
                        try: 
                            ep_num = int(episode_number)
                        except: 
                            ep_num = float(episode_number)
                            
                        if data_ep_num < ep_num:
                            if "Lastest" in dts[data['url']]:
                                chapters = await web_data[i].get_chapters(data)
                                if chapters:  # Check if chapters is not None
                                    chapters = web_data[i].iter_chapters(chapters)
                                    if chapters:
                                        for chapter in chapters:
                                            try: 
                                                chapter_ep = int(get_episode_number(chapter['title']))
                                            except: 
                                                chapter_ep = float(get_episode_number(chapter['title']))
                                            
                                            try: 
                                                lastest_ep = int(dts[data['url']]['Lastest'])
                                            except: 
                                                lastest_ep = float(dts[data['url']]['Lastest'])
                                                
                                            if lastest_ep < chapter_ep:
                                                pictures = await web_data[i].get_pictures(url=data['chapter_url'], data=data)
                                                if pictures:
                                                    data['pictures_list'] = pictures
                                                    updates.append(data)
                    else:
                        pictures = await web_data[i].get_pictures(url=data['chapter_url'], data=data)
                        if pictures:
                            data['pictures_list'] = pictures
                            updates.append({'data': data, 'webs': web_data[i]})
        except Exception as e:
            logger.error(f"Error processing {i} updates: {e}")
            continue

    return updates


async def send_updates(data, webs):
    e = True
    try:
        await Bot.send_message(
            Vars.UPDATE_CHANNEL,
            f"<b><i>Updates: {data['manga_title']} - {data['title']}\n\nUrl: {data['url']}</i></b>"
        )
    except Exception as e:
        logger.error(f"Error sending update message: {e}")

    episode_number = str(get_episode_number(data['title']))
    user_ids = dts[data['url']]['users']
    
    for user_id in user_ids:
        try:
            e = await send_manga_chapter(data, picturesList=data['pictures_list'], user=None, sts=None, user_id=user_id, webs=webs, worker_id=123)
        except Exception as e:
            logger.error(f"Error sending chapter to user {user_id}: {e}")
            continue

    if not e:
        # Saving Database
        dts[data['url']]["Lastest"] = str(episode_number)
        sync()


async def main_updates():
    while True:
        min = 20
        try:
            updates = await get_updates_manga()
            for data in updates:
                try:
                    await send_updates(data['data'], data['webs'])
                except Exception as e:
                    logger.error(f"Error in send_updates: {e}")
                    continue
        except Exception as e:
            logger.error(f"Critical error in main_updates: {e}")
        finally:
            await asyncio.sleep(min * 60)


# Alternative: More robust version with retry logic
async def get_updates_with_retry():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            updates = await get_updates_manga()
            return updates
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to get updates after {max_retries} attempts: {e}")
                return []
            wait_time = (2 ** attempt) * 60  # Exponential backoff in minutes
            logger.warning(f"Retry {attempt + 1} for updates after {wait_time}s")
            await asyncio.sleep(wait_time)


async def main_updates():
    while True:
        min = 20
        try:
            updates = await get_updates_with_retry()
            for data in updates:
                try:
                    await send_updates(data['data'], data['webs'])
                except Exception as e:
                    logger.error(f"Error processing update: {e}")
                    continue
        except Exception as e:
            logger.critical(f"Unexpected error in main loop: {e}")
        finally:
            await asyncio.sleep(min * 60)
