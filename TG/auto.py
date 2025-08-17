from __future__ import annotations  # Better forward compatibility
from bot import Bot, Vars, logger
from Tools.db import sync, dts  # Assuming these are defined elsewhere
from .storage import web_data, get_episode_number
from .wks import send_manga_chapter
import asyncio
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

async def get_updates_manga() -> List[Dict[str, Any]]:
    """Fetch new manga updates from web sources."""
    updates: List[Dict[str, Any]] = []
    
    for source_name, source in web_data.items():
        try:
            raw_data = await source.get_updates()
            for data in raw_data:
                if data["url"] not in dts:
                    continue

                episode_str = str(get_episode_number(data["title"]))
                latest_ep = dts[data["url"]].get("Lastest")

                # Case 1: New chapter is available
                if latest_ep:
                    try:
                        latest_num = float(latest_ep)
                        current_num = float(episode_str)
                        if latest_num >= current_num:
                            continue  # No new updates
                    except ValueError:
                        logger.warning(f"Invalid episode format in {data['url']}")
                        continue

                    # Fetch missing chapters between latest and current
                    chapters = await source.get_chapters(data)
                    if not chapters:
                        continue

                    for chapter in source.iter_chapters(chapters):
                        try:
                            chap_num = float(get_episode_number(chapter["title"]))
                            if float(latest_ep) >= chap_num:
                                continue
                        except ValueError:
                            continue

                        if pics := await source.get_pictures(url=chapter["chapter_url"], data=data):
                            data["pictures_list"] = pics
                            updates.append({"data": data, "webs": source})

                # Case 2: First-time tracking (no "Lastest" entry)
                elif (pics := await source.get_pictures(url=data["chapter_url"], data=data)):
                    data["pictures_list"] = pics
                    updates.append({"data": data, "webs": source})

        except Exception as e:
            logger.exception(f"Error in {source_name}: {e}")
            continue

    return updates

async def send_updates(data: Dict[str, Any], webs: Any) -> bool:
    """Send manga updates to users and update the database."""
    success = True
    
    # Notify update channel (optional)
    try:
        await Bot.send_message(
            Vars.UPDATE_CHANNEL,
            f"<b>Update: {data['manga_title']} - {data['title']}</b>\n\nURL: {data['url']}"
        )
    except Exception as e:
        logger.warning(f"Failed to send announcement: {e}")

    # Send to subscribed users
    episode_num = str(get_episode_number(data["title"]))
    user_ids = dts[data["url"]].get("users", [])
    
    for user_id in user_ids:
        success &= await send_manga_chapter(
            data=data,
            picturesList=data["pictures_list"],
            user=None,
            sts=None,
            user_id=user_id,
            webs=webs,
            worker_id=123,
        )
        if not success:
            break

    # Update DB if all sends succeeded
    if success:
        dts[data["url"]]["Lastest"] = episode_num
        sync()
    
    return success

async def main_updates() -> None:
    """Main loop to check and distribute updates periodically."""
    while True:
        try:
            updates = await get_updates_manga()
            for update in updates:
                try:
                    await send_updates(update["data"], update["webs"])
                except Exception as e:
                    logger.error(f"Failed to process update: {e}")
        finally:
            await asyncio.sleep(20 * 60)  # 20-minute delay
