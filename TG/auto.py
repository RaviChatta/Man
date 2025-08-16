from bot import Bot, Vars, logger
from Tools.db import *
from .storage import web_data, clean, retry_on_flood, get_episode_number, queue
from .wks import send_manga_chapter

import asyncio
import os


async def get_updates_manga():
    updates = []

    for i in web_data.keys():
        try:
            # Force Cloudscraper for sites like Asura
            raw_data = await web_data[i].get_updates(cs=True)
            for data in raw_data:
                if data['url'] in dts:
                    episode_number = str(get_episode_number(data['title']))

                    if 'Lastest' in dts[data['url']]:
                        try:
                            data_ep_num = float(dts[data['url']]['Lastest'])
                        except:
                            data_ep_num = 0.0

                        try:
                            ep_num = float(episode_number)
                        except:
                            ep_num = 0.0

                        if data_ep_num < ep_num:
                            chapters = await web_data[i].get_chapters(data)
                            chapters = web_data[i].iter_chapters(chapters)
                            if chapters:
                                for chapter in chapters:
                                    try:
                                        chapter_ep = float(get_episode_number(chapter['title']))
                                    except:
                                        chapter_ep = 0.0

                                    lastest_ep = data_ep_num
                                    if lastest_ep < chapter_ep:
                                        # Force Cloudscraper for pictures
                                        pictures = await web_data[i].get_pictures(url=data['chapter_url'], data=data, cs=True)
                                        if pictures:
                                            # Filter out broken images
                                            valid_pictures = []
                                            for pic in pictures:
                                                try:
                                                    resp = await web_data[i].get(pic, cs=True)
                                                    if resp:
                                                        valid_pictures.append(pic)
                                                except:
                                                    continue
                                            if not valid_pictures:
                                                continue
                                            data['pictures_list'] = valid_pictures
                                            updates.append(data)
                    else:
                        pictures = await web_data[i].get_pictures(url=data['chapter_url'], data=data, cs=True)
                        if pictures:
                            valid_pictures = []
                            for pic in pictures:
                                try:
                                    resp = await web_data[i].get(pic, cs=True)
                                    if resp:
                                        valid_pictures.append(pic)
                                except:
                                    continue
                            if not valid_pictures:
                                continue
                            data['pictures_list'] = valid_pictures
                            updates.append({'data': data, 'webs': web_data[i]})

        except Exception as e:
            logger.exception(e)
            continue

    return updates


async def send_updates(data, webs):
    episode_number = str(get_episode_number(data['title']))
    user_ids = dts[data['url']]['users']
    success = True

    for user_id in user_ids:
        try:
            # Always send fresh files to avoid FileReferenceExpired
            result = await send_manga_chapter(
                data,
                picturesList=data['pictures_list'],
                user=None,
                sts=None,
                user_id=user_id,
                webs=webs,
                worker_id=123
            )
            if not result:
                success = False
        except Exception as e:
            logger.exception(e)
            success = False

    if success:
        # Update database only if all sends succeeded
        dts[data['url']]["Lastest"] = episode_number
        sync()


async def main_updates():
    while True:
        interval_minutes = 20
        try:
            updates = await get_updates_manga()
            for data in updates:
                try:
                    await send_updates(data['data'], data['webs'])
                except Exception as e:
                    logger.exception(e)
                    continue
        finally:
            await asyncio.sleep(interval_minutes * 60)
