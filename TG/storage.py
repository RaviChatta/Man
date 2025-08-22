from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from Webs import *

import asyncio
import random
import string
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Awaitable, Union, Hashable

from loguru import logger

import pyrogram.errors
from pyrogram.errors import PeerIdInvalid
from pyrogram.errors import FloodWait

import re

searchs = dict()
backs = dict()
chaptersList = dict()
queueList = dict()
pagination = dict()
subscribes = dict()


users_txt = """
<b>⚙️ <u>User Settings Panel</u></b>
<blockquote>
<b>🆔 User ID:</b> <code>{id}</code>
<b>📝 File Name:</b> <code>{file_name}</code>
<b>📝 File Name Length:</b> <code>{len}</code>
<b>📋 Caption:</b> <code>{caption}</code>
<b>🖼 Thumbnail:</b> <code>{thumb}</code>
<b>📡 Dump Channel:</b> <code>{dump}</code>
<b>📦 File Type:</b> <code>{type}</code>
<b>🔢 Merge Size:</b> <code>{megre}</code>
<b>🔍 Regex:</b> <code>{regex}</code>
<b>🔐 Password:</b> <code>{password}</code></blockquote>
<b>📌 Banners:</b>
<blockquote>
<b>1:</b> <code>{banner1}</code>
<b>2:</b> <code>{banner2}</code>
</blockquote>
"""
web_data = {
    " Comick ": ComickWebs(),
    #" MangaMob ": MangaMobWebs(),
    " Asura Scans ": AsuraScansWebs(),
    #" Flame Comics": FlameComicsWebs(),
    #" Demonic Scans ": DemonicScansWebs(),
    " Manhua Fast ": ManhuaFastWebs(),
    " Weeb Central ": WeebCentralWebs(),
    " ManhwaClan ": ManhwaClanWebs(),
    " TempleToons ":TempleToonsWebs(),
    " Manhuaplus ": ManhuaplusWebs(),
    " Mgeko ": MgekoWebs(),
    " Manga18fx ": Manga18fxWebs(),
    " Manhwa18 ":  Manhwa18Webs(),
    "NHentai": NHentaiWebs(),  # This should have bg=False in its class
#    "Bato.to": BatoWebs(),  # ← Add this line for Bato
    "Toonily": ToonilyScraper(),  # Add Toonily here


}

plugins_name = " ".join(web_data[i].sf for i in web_data.keys())


def split_list(li):
    return [li[x:x + 2] for x in range(0, len(li), 2)]


def plugins_list(type=None):
    button = []
    if type and type == "updates":
        for i in web_data.keys():
            c = web_data[i].sf
            c = f"udat_{c}"
            button.append(InlineKeyboardButton(i, callback_data=c))
    elif type and type == "gens":
        for i in web_data.keys():
            c = web_data[i].sf
            c = f"gens_{c}"
            button.append(InlineKeyboardButton(i, callback_data=c))
    else:
        for i in web_data.keys():
            c = web_data[i].sf
            c = f"plugin_{c}"
            button.append(InlineKeyboardButton(i, callback_data=c))
    
    # Split into rows of 2 buttons each
    button_rows = split_list(button)
    
    # Add close button as a separate row at the bottom
    close_button = [InlineKeyboardButton("❌ Close", callback_data="close")]
    button_rows.append(close_button)
    
    return InlineKeyboardMarkup(button_rows)

def get_webs(sf):
    for i in web_data.keys():
        if web_data[i].sf == sf:
            return web_data[i]


# retries an async awaitable as long as it raises FloodWait, and waits for err.x time
def retry_on_flood(function: Callable[[Any], Awaitable]):

    async def wrapper(*args, **kwargs):
        while True:
            try:
                await asyncio.sleep(1)
                return await function(*args, **kwargs)
            except pyrogram.errors.FloodWait as err:
                logger.warning(
                    f'FloodWait, waiting {err.value} seconds: {err.MESSAGE}')
                await asyncio.sleep(err.value)
                continue

            except PeerIdInvalid:
                return

            except pyrogram.errors.BadRequest as err:
                if err.MESSAGE == 'Message is not modified':
                    return
                elif err.MESSAGE == 'Message_id_invalid':
                    return
                elif err.MESSAGE == 'Message not found':
                    return

            except pyrogram.errors.Unauthorized as err:
                return

            except pyrogram.errors.RPCError as err:
                if err.MESSAGE == 'FloodWait':
                    logger.warning(
                        f'FloodWait, waiting {err.value} seconds: {err.MESSAGE}'
                    )
                    await asyncio.sleep(err.value)
                    continue
                else:
                    raise err

            except BaseException as e:
                return
            except Exception as err:
                raise err

    return wrapper


class AQueue:

    def __init__(self, maxsize: Optional[int] = None):
        self.data: Dict[str, Tuple[Any,
                                   Hashable]] = {}  # Enforce hashable locks
        self._mask: Set[Hashable] = set()  # Only hashable types allowed
        self._put_lock = asyncio.Lock()
        self._get_lock = asyncio.Lock()
        self._not_empty = asyncio.Event()
        self._user_data = {}
        self._unfinished_tasks = 0
        self.maxsize = maxsize

    async def get_random_id(self) -> str:
        while True:
            random_string = ''.join(
                random.choices(string.ascii_letters + string.digits, k=9))
            if random_string not in self.data:
                return random_string

    async def put(self, item: Any, lock: Hashable) -> str:
        """Add item to queue. Lock must be hashable (int, str, tuple, etc.)."""
        if not isinstance(lock, Hashable):
            raise TypeError(f"Lock must be hashable, got {type(lock)}")

        if self.maxsize is not None and len(self.data) >= self.maxsize:
            raise asyncio.QueueFull

        async with self._put_lock:
            task_id = await self.get_random_id()
            self.data[task_id] = (item, lock)
            self._unfinished_tasks += 1
            self._not_empty.set()
            
            if not self._user_data.get(lock):
                self._user_data[lock] = []
            
            self._user_data[lock].append(task_id)
            
            return task_id

    async def get(self, worker_id: int) -> Tuple[Any, Hashable]:
        async with self._get_lock:
            while True:
                # First check for immediately available items
                available = [(task_id, item, lock)
                             for task_id, (item, lock) in self.data.items()
                             if lock not in self._mask]

                if available:
                    task_id, item, lock = available[0]
                    del self.data[task_id]
                    self.acquire(lock)
                    return item, lock, task_id

                # If queue is completely empty, wait for new items
                if not self.data:
                    self._not_empty.clear()
                    await self._not_empty.wait()
                    continue

                # If items exist but are all locked, wait for releases
                await asyncio.sleep(0.1)  # Small delay to prevent busy-w

    async def get_test(self, worker_id: int) -> Tuple[Any, Hashable]:
        async with self._get_lock:
            await self._not_empty.wait()

            # Safe item collection with type checking
            available = []
            for task_id, (item, lock) in self.data.items():
                try:
                    if lock not in self._mask:
                        available.append((task_id, item, lock))
                except TypeError:
                    # Clean up invalid locks
                    del self.data[task_id]
                    continue

            if not available:
                self._not_empty.clear()
                raise Exception("No available items despite not_empty event")

            # Get first available item
            task_id, item, lock = available[0]
            del self.data[task_id]
            self.acquire(lock)

            # Safe availability check
            has_available = False
            for _, existing_lock in self.data.items():
                try:
                    if existing_lock not in self._mask:
                        has_available = True
                        break
                except TypeError:
                    continue

            if not has_available:
                self._not_empty.clear()

            return item, lock

    def acquire(self, lock: Hashable) -> None:
        """Acquire a lock. Lock must be hashable."""
        if not isinstance(lock, Hashable):
            raise TypeError(f"Lock must be hashable, got {type(lock)}")
        self._mask.add(lock)

    def release(self, lock: Hashable) -> None:
        """Release a lock. Lock must be hashable."""
        if not isinstance(lock, Hashable):
            raise TypeError(f"Lock must be hashable, got {type(lock)}")
        self._unfinished_tasks -= 1
        self._mask.discard(lock)
        if any(item_lock == lock for _, item_lock in self.data.items()):
            self._not_empty.set()

    async def delete_task(self, task_id: str) -> bool:
        """Delete a specific task by its ID.

        Returns:
            bool: True if task was found and deleted, False otherwise
        """
        async with self._put_lock:
            if task_id in self.data:
                _, lock = self.data[task_id]
                if lock in self._mask:
                    self._mask.discard(lock)
                self.delete_user_data_(task_id)
                del self.data[task_id]
                self._unfinished_tasks -= 1
                if not self.data:
                    self._not_empty.clear()
                return True
            return False

    async def delete_tasks(self, task_ids: List[str]) -> int:
        """Delete multiple tasks by their IDs.

        Returns:
            int: Number of tasks successfully deleted
        """
        async with self._put_lock:
            count = 0
            for task_id in task_ids:
                if task_id in self.data:
                    _, lock = self.data[task_id]
                    if lock in self._mask:
                        self._mask.discard(lock)
                    del self.data[task_id]
                    self._unfinished_tasks -= 1
                    count += 1

            if not self.data:
                self._not_empty.clear()

            return count
    
    def get_count_(self, user_id):
        return len(self._user_data.get(user_id, []))
    
    def delete_user_data_(self, task_id):
        for user_id, tasks in self._user_data.items():
            if task_id in tasks:
                self._user_data[user_id].remove(task_id)

    def task_exists(self, task_id: str) -> bool:
        """Check if a task exists in the queue."""
        return task_id in self.data

    def qsize(self) -> int:
        """Return the number of items in the queue."""
        return len(self.data)

    def empty(self) -> bool:
        """Return True if the queue is empty."""
        return not self.data

    def task_done(self, task_id) -> None:
        """Mark a task as done."""
        self._unfinished_tasks -= 1
        self.delete_user_data_(task_id)

    async def join(self) -> None:
        """Wait until all tasks are done."""
        while self._unfinished_tasks > 0:
            await asyncio.sleep(0.1)


queue = AQueue()


def clean(txt, length=-1):
    txt = txt.replace("_", "").replace("&", "").replace(";", "")
    txt = txt.replace("None", "").replace(":", "").replace("'", "")
    txt = txt.replace("|", "").replace("*", "").replace("?", "")
    txt = txt.replace(">", "").replace("<", "").replace("`", "")
    txt = txt.replace("!", "").replace("@", "").replace("#", "")
    txt = txt.replace("$", "").replace("%", "").replace("^", "")
    txt = txt.replace("~", "").replace("+", "").replace("=", "")
    txt = txt.replace("/", "").replace("\\", "").replace("\n", "")
    if length != -1:
        txt = txt[:length]
    return txt


def get_episode_number(text):
    text = str(text)
    pattern1 = re.compile(r"Chapter\s+(\d+(?:\.\d+)?)")
    pattern2 = re.compile(r"Volume\s+(\d+) Chapter\s+(\d+(?:\.\d+)?)")
    pattern3 = re.compile(r"Chapter\s+(\d+)\s+-\s+(\d+(?:\.\d+)?)")
    patternX = re.compile(r"(\d+(?:\.\d+)?)")

    match1 = re.search(pattern1, text)
    if match1:
        return str(match1.group(1))

    match2 = re.search(pattern2, text)
    if match2:
        return str(match2.group(2))

    match3 = re.search(pattern3, text)
    if match3:
        return str(match3.group(1))

    matchX = re.search(patternX, text)
    if matchX:
        return str(matchX.group(1))
