from pymongo import MongoClient
from bot import Vars, Bot
import time

client = MongoClient(Vars.DB_URL)
db = client[Vars.DB_NAME]

subs = db["subs"]
users = db["users"]
acollection = db['premium']
files = db["files"]  # NEW collection for Telegram files

uts = users.find_one({"_id": Vars.DB_NAME})
dts = subs.find_one({"_id": "data"})

if not dts:
    dts = {'_id': "data"}
    subs.insert_one(dts)

if not uts:
    uts = {'_id': Vars.DB_NAME}
    users.insert_one(uts)

# -------------------- PREMIUM USERS --------------------

async def add_premium(user_id, time_limit_days):
    expiration_timestamp = int(time.time()) + time_limit_days * 24 * 60 * 60
    premium_data = {
        "user_id": user_id,
        "expiration_timestamp": expiration_timestamp,
    }
    acollection.insert_one(premium_data)

async def remove_premium(user_id):
    acollection.delete_one({"user_id": user_id})

async def remove_expired_users():
    current_timestamp = int(time.time())
    expired_users = acollection.find({"expiration_timestamp": {"$lte": current_timestamp}})
    for expired_user in expired_users:
        user_id = expired_user["user_id"]
        acollection.delete_one({"user_id": user_id})

async def premium_user(user_id):
    user = acollection.find_one({"user_id": user_id})
    return user is not None

# -------------------- USERS & SUBSCRIPTIONS --------------------

def sync(name="data", type="dts"):
    if type == "dts":
        subs.replace_one({'_id': name}, dts)
    elif type == "uts":
        users.replace_one({'_id': name}, uts)

def get_users():
    users_id = []
    for i in users.find():
        for j in i:
            try:
                users_id.append(int(j))
            except:
                continue
    return users_id

def add_sub(user_id, manga_url: str, chapter=None):
    user_id = str(user_id)
    if manga_url not in dts:
        dts[manga_url] = {}
        sync()

    if "users" not in dts[manga_url]:
        dts[manga_url]["users"] = []
        sync()

    if user_id not in dts[manga_url]["users"]:
        dts[manga_url]["users"].append(user_id)
        sync()

    if user_id not in uts:
        uts[user_id] = {}
        sync(Vars.DB_NAME, 'uts')

    if "subs" not in uts[user_id]:
        uts[user_id]["subs"] = []
        sync(Vars.DB_NAME, 'uts')

    if manga_url not in uts[user_id]["subs"]:
        uts[user_id]["subs"].append(manga_url)
        sync(Vars.DB_NAME, 'uts')

    sync()
    sync(Vars.DB_NAME, 'uts')

def get_subs(user_id, manga_url: str = None):
    user_id = str(user_id)
    if user_id not in uts:
        uts[user_id] = {}
        sync(Vars.DB_NAME, 'uts')

    if "subs" not in uts[user_id]:
        uts[user_id]["subs"] = []
        sync(Vars.DB_NAME, 'uts')

    if manga_url:
        if user_id in uts:
            if manga_url in uts[user_id]["subs"]:
                return True
            else:
                return None

    if user_id in uts:
        if "subs" not in uts[user_id]:
            uts[user_id]["subs"] = []
            sync(Vars.DB_NAME, 'uts')

        return uts[user_id]["subs"]

def delete_sub(user_id, manga_url: str):
    user_id = str(user_id)
    if manga_url in dts and user_id in dts[manga_url]["users"]:
        dts[manga_url]["users"].remove(user_id)
        sync()

    if user_id in uts and manga_url in uts[user_id]["subs"]:
        uts[user_id]["subs"].remove(manga_url)
        sync(Vars.DB_NAME, 'uts')

    sync()
    sync(Vars.DB_NAME, 'uts')

# -------------------- FILE STORAGE (FIX FOR FILE_REFERENCE_EXPIRED) --------------------

async def add_file(user_id, message):
    """Save a file (doc, photo, video, etc.) with chat_id & message_id"""
    file_data = {
        "user_id": user_id,
        "chat_id": message.chat.id,
        "message_id": message.id,
        "file_id": (
            message.document.file_id if message.document else
            message.photo.file_id if message.photo else
            message.video.file_id if message.video else None
        ),
        "file_type": (
            "document" if message.document else
            "photo" if message.photo else
            "video" if message.video else "unknown"
        ),
        "timestamp": int(time.time())
    }
    files.update_one({"user_id": user_id}, {"$set": file_data}, upsert=True)

async def get_file(app, user_id):
    """Fetch file again with fresh file_reference"""
    data = files.find_one({"user_id": user_id})
    if not data:
        return None

    msg = await app.get_messages(data["chat_id"], data["message_id"])
    return msg
