from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .storage import web_data, split_list, plugins_list, users_txt, retry_on_flood, queue, asyncio

from pyrogram.errors import FloodWait
import pyrogram.errors

from bot import Bot, Vars, logger

import random
from Tools.db import *
from Tools.my_token import *

from pyrogram.handlers import MessageHandler
import time

from asyncio import create_subprocess_exec
from os import execl
from sys import executable

import shutil, psutil, time, os, platform
import asyncio

STICKER_ID = "CAACAgUAAxkBAAJFeWd037UWP-vgb_dWo55DCPZS9zJzAAJpEgACqXaJVxBrhzahNnwSHgQ"

HELPs_MSG = """
<b>📚 Manga Downloader Bot Help Guide</b>

<blockquote>
Welcome to the ultimate manga downloading experience! Here's how to use me:
</blockquote>

<b>🔍 Basic Commands:</b>
<blockquote expandable>
• /start - Initialize the bot and check status
• /help - Display this help message
• /search [manga] - Search for manga across sites
• /updates - Check latest manga updates
• /queue - View your download queue
• /stats - View bot system statistics</blockquote>

<b>📥 Downloading Manga:</b>
<blockquote expandable>
1. Simply type the manga name (e.g., <code>One Piece</code>)
2. Select your preferred website
3. Choose language and chapter
4. The bot will process your request
</blockquote>

<b>⚙️ User Settings:</b>
<blockquote expandable>
• /us - Configure your download preferences
• Set custom file names, thumbnails, captions
• Configure automatic merging and passwords
</blockquote>

<b>🔄 Subscription System:</b>
<blockquote expandable>
• Automatically get new chapter updates
• Manage with /subs and /unsubs commands
• Receive notifications for new releases
</blockquote>

<b>📌 Important Notes:</b>
<blockquote expandable>
• Large files may take time to process
• Check /queue for download status
• Use /clean to clear temporary files
• Join @Wizard_bots for updates
</blockquote>

<blockquote>
<i>Need more help? Contact @WizardBotHelper</i>
</blockquote>
"""

# Modified HELP_MSG to be shorter
HELP_MSG = """
<b>📚 Manga Downloader Bot Help</b>
<u>Basic Commands:</u>
<blockquote>• /start - Initialize bot
• /help - Show this message
• /search - Find manga
• /updates - Latest releases
• /queue - Your downloads
• /stats - System info
<u>Quick Guide:</u>
1. Type manga name
2. Select website
3. Choose chapter
4. Download!
<u>Settings:</u>
• /us - Configure preferences</blockquote>
<b>🔄 Subscription System:</b>
<blockquote expandable>
• Automatically get new chapter updates
• Manage with /subs and /unsubs commands
• Receive notifications for new releases</blockquote>
"""

# Modified ADMIN_HELP_MSG to be shorter
ADMIN_HELP_MSG = """
<b>👑 Admin Commands</b>

<blockquote>
<u>System:</u>
• /restart - Reboot bot
• /clean - Clear temp files
• /shell - Execute commands
• /broadcast - Send message to all users
• /pbroadcast - Broadcast and pin message
<u>Users:</u>
• /add_premium - Grant access
• /del_premium - Revoke access

Use with caution!
</blockquote>
"""

@Bot.on_message(filters.command("start"))
async def start(client, message):
    if Vars.IS_PRIVATE:
        if message.chat.id not in Vars.ADMINS:
            return await message.reply_photo(
                random.choice(Vars.PICS),
                caption="<blockquote>🚫 <b>Access Denied</b>\n\nThis is a private bot. Contact admin for access.</blockquote>"
            )

    if len(message.command) > 1:
        if message.command[1] != "start":
            user_id = message.from_user.id
            token = message.command[1]
            if verify_token_memory(user_id, token):
                sts = await message.reply_photo(
                    random.choice(Vars.PICS),
                    caption="<blockquote>🔐 <b>Token Verified!</b>\n\nYou can now use the bot.</blockquote>"
                )
                save_token(user_id, token)
                global_tokens.pop(user_id, None)
                await asyncio.sleep(8)
                await sts.delete()
            else:
                sts = await message.reply_photo(
                    random.choice(Vars.PICS),
                    caption="<blockquote>⚠️ <b>Invalid Token</b>\n\nRequesting a new one...</blockquote>"
                )
                await get_token(message, user_id)
                await sts.delete()
            return

    # Animated startup sequence
    m = await message.reply_photo(
        random.choice(Vars.PICS),
        caption="<blockquote>🌀 <b>Initializing System...</b></blockquote>"
    )
    await asyncio.sleep(0.4)
    await m.edit_caption("<blockquote>🔍 <b>Checking Resources...</b></blockquote>")
    await asyncio.sleep(0.5)
    await m.edit_caption("<blockquote>⚡ <b>Powering Up...</b></blockquote>")
    await asyncio.sleep(0.5)
    await m.edit_caption("<blockquote>🚀 <b>Almost There...</b></blockquote>")
    await asyncio.sleep(0.5)
    await m.edit_caption("<blockquote>✅ <b>Ready to Serve!</b></blockquote>")
    await asyncio.sleep(0.4)
    await m.delete()

    # Send sticker if available
    if STICKER_ID:
        m = await message.reply_sticker(STICKER_ID)
        await asyncio.sleep(1)
        await m.delete()

    # Send main welcome photo + caption
    await message.reply_photo(
        random.choice(Vars.PICS),
        caption=(
            "<b>🌟 Welcome to Manga Downloader Pro!</b>\n"
            "<blockquote>"
            "The most advanced manga downloader on Telegram\n"
            "Download entire series or single chapters with ease"
            "</blockquote>"
            "🔹 <b>Quick Start:</b>\n"
            "<blockquote>Just type the name of any manga to begin</blockquote>\n\n"
            "📌 <b>Example:</b>\n"
            "<blockquote><code>One Piece</code></blockquote>"
         #   f"⚡ <b>Bot Status:</b> <code>{time.strftime('%Hh%Mm%Ss', time.gmtime(time.time() - Vars.PING))}</code>\n\n"
    
        ),
        reply_markup=InlineKeyboardMarkup([
            [        
                InlineKeyboardButton('📺 Anime Bot', url="https://t.me/Violetanimebot"),
                InlineKeyboardButton("🆘 Support", url="https://t.me/TFIBOTS_SUPPORT")
            ],
            [
                InlineKeyboardButton("📚 Help Guide", callback_data="help_guide")
            ]
        ])
    )

@Bot.on_message(filters.command("help"))
async def help(client, message):
    if Vars.IS_PRIVATE and message.chat.id not in Vars.ADMINS:
        m = await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<blockquote>🚫 Access Denied</blockquote>"
        )
        await asyncio.sleep(180)  # Auto-delete after 3 minutes
        await m.delete()
        return

    if message.from_user.id in Vars.ADMINS:
        # For admins, show both help messages in separate messages
        m1 = await message.reply_photo(
            random.choice(Vars.PICS),
            caption=HELP_MSG
        )
        await asyncio.sleep(1)
        m2 = await message.reply_photo(
            random.choice(Vars.PICS),
            caption=ADMIN_HELP_MSG
        )

        # Schedule auto-delete for both messages
        await asyncio.sleep(180)
        await m1.delete()
        await m2.delete()
    else:
        m = await message.reply_photo(
            random.choice(Vars.PICS),
            caption=HELP_MSG
        )
        await asyncio.sleep(180)  # Auto-delete after 3 minutes
        await m.delete()

@Bot.on_message(filters.command("stats"))
async def show_ping(_, message):
    if Vars.IS_PRIVATE and message.chat.id not in Vars.ADMINS:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<blockquote>🚫 Access Denied</blockquote>"
        )
    
    # First send the "Gathering metrics" message
    st = await message.reply_photo(
        random.choice(Vars.PICS),
        caption='<blockquote>📊 <b>Gathering System Metrics...</b></blockquote>'
    )
    
    # Get all system metrics
    total, used, free = shutil.disk_usage(".")
    total = humanbytes(total)
    used = humanbytes(used)
    free = humanbytes(free)
    net_start = psutil.net_io_counters()

    await asyncio.sleep(2)  # Wait to calculate network speed
    net_end = psutil.net_io_counters()

    bytes_sent = net_end.bytes_sent - net_start.bytes_sent
    bytes_recv = net_end.bytes_recv - net_start.bytes_recv
    
    cpu_cores = os.cpu_count()
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    try: 
        uptime = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - _.PING))
    except: 
        uptime = "N/A"

    # Edit the original message with the stats
    await st.edit_caption(
        caption=(
            "<b>🖥 SYSTEM STATISTICS</b>\n\n"
            "<blockquote>"
            f"<b>Storage:</b> {used} / {total} ({disk_usage}% used)\n"
            f"<b>Free Space:</b> {free}\n"
            f"<b>CPU:</b> {cpu_cores} cores @ {cpu_usage}%\n"
            f"<b>RAM:</b> {ram_usage}% utilized\n"
            f"<b>Uptime:</b> {uptime}\n"
            f"<b>Provider:</b> {GET_PROVIDER()}\n"
            f"<b>OS:</b> {platform.system()} {platform.release()}\n"
            f"<b>Python:</b> {platform.python_version()}\n"
            f"<b>Pyrogram:</b> {_.__version__}\n"
            f"<b>Network:</b> {humanbytes(net_end.bytes_sent + net_end.bytes_recv)} total\n"
            f"<b>Speed:</b> ▲{humanbytes(bytes_sent/2)}/s ▼{humanbytes(bytes_recv/2)}/s\n"
            f"<b>Queue:</b> {queue.qsize()} pending"
            "</blockquote>"
        ),
    )
    
    # Auto-delete after 1 minute
    await asyncio.sleep(60)
    try:
        await st.delete()
    except:
        pass
  
@Bot.on_message(filters.command("restart") & filters.user(Bot.ADMINS))
async def restart_(client, message):
    msg = await message.reply_photo(
        random.choice(Vars.PICS),
        caption="<blockquote>🔄 <b>Initiating Restart Sequence...</b></blockquote>", 
        quote=True
    )
    with open("restart_msg.txt", "w") as file:
        file.write(f"{msg.chat.id}:{msg.id}")
    
    await (await create_subprocess_exec("python3", "update.py")).wait()
    execl(executable, executable, "-B", "main.py")

@Bot.on_message(filters.command(["clean", "c"]) & filters.user(Bot.ADMINS))
async def clean(_, message):
    directory = '/app'
    ex = (".mkv", ".mp4", ".zip", ".pdf", ".png", ".epub", ".temp")
    protected_dirs = (".git", "venv", "env", "__pycache__")
    sts = await message.reply_photo(
        random.choice(Vars.PICS),
        caption="<blockquote>🧹 <b>Cleaning System...</b></blockquote>"
    )
    deleted_files = []
    removed_dirs = []
    
    if os.path.exists("Process"):
        shutil.rmtree("Process")
    elif os.path.exists("./Process"):
        shutil.rmtree("./Process")
        
    try:
        for root, dirs, files in os.walk(directory, topdown=False):
            dirs[:] = [d for d in dirs if d not in protected_dirs]
            for file in files:
                if file.lower().endswith(ex):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        deleted_files.append(file_path)
                    except:
                        pass

                elif file.lower().startswith("vol"):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        deleted_files.append(file_path)
                    except:
                        pass

            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        removed_dirs.append(dir_path)
                    elif dir_path in ["/app/Downloads", "/app/downloads"]:
                        shutil.rmtree(dir_path)
                        removed_dirs.append(dir_path)
                    try:
                        dir_path = int(dir_path)
                        os.rmdir(dir_path)
                        removed_dirs.append(dir_path)
                    except:
                        pass
                except:
                    pass

        msg = "<b>🧹 CLEANUP REPORT</b>\n\n"
        if deleted_files:
            msg += f"🗑 <b>Deleted {len(deleted_files)} files</b>\n"
            msg += "<blockquote>" + "\n".join(deleted_files[:5]) + "</blockquote>"
            if len(deleted_files) > 5:
                msg += f"<blockquote>...and {len(deleted_files) - 5} more</blockquote>"
        else:
            msg += "✅ <b>No files deleted</b>\n"

        if removed_dirs:
            msg += f"\n📁 <b>Removed {len(removed_dirs)} directories</b>\n"
            msg += "<blockquote>" + "\n".join(removed_dirs[:3]) + "</blockquote>"
            if len(removed_dirs) > 3:
                msg += f"<blockquote>...and {len(removed_dirs) - 3} more</blockquote>"
        else:
            msg += "\n✅ <b>No directories removed</b>"

        await sts.edit_caption(msg)
    except Exception as err:
        await sts.edit_caption(f"<blockquote>❌ <b>Error:</b>\n<code>{err}</code></blockquote>")


@Bot.on_message(filters.command("queue"))
async def queue_msg_handler(client, message):
    if Vars.IS_PRIVATE and message.chat.id not in Vars.ADMINS:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<blockquote>🚫 Access Denied</blockquote>"
        )

    user_count = queue.get_count_(message.from_user.id)
    total_count = int(queue.qsize()) + 1
    
    progress = "🟢" * min(user_count, 5) + "⚪" * (5 - min(user_count, 5))
    if user_count > 5:
        progress += f" (+{user_count - 5})"
    
    msg = await message.reply_photo(
        random.choice(Vars.PICS),
        caption=(
            f"<b>📊 Download Queue</b>\n\n"
            f"<blockquote>"
            f"<b>Your Tasks:</b> {user_count}\n"
            f"<b>System Total:</b> {total_count}\n\n"
            f"{progress}"
            f"</blockquote>"
        )
    )
    
    # Auto-delete after 1 minute
    await asyncio.sleep(60)
    try:
        await msg.delete()
    except:
        pass

@Bot.on_message(filters.private)
async def on_private_message(client, message):
    if client.SHORTENER:
        if not await premium_user(message.from_user.id):
            if not verify_token(message.from_user.id):
                if not message.from_user.id in client.ADMINS:
                    return await get_token(message, message.from_user.id)
    
    channel = client.FORCE_SUB_CHANNEL
    if not channel:
        return message.continue_propagation()

    try:
        if await client.get_chat_member(channel, message.from_user.id):
            return message.continue_propagation()

    except pyrogram.errors.UsernameNotOccupied:
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="Channel does not exist, therefore bot will continue to operate normally"
        )
        return message.continue_propagation()

    except pyrogram.errors.ChatAdminRequired:
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="Bot is not admin of the channel, therefore bot will continue to operate normally"
        )
        return message.continue_propagation()

    except pyrogram.errors.UserNotParticipant:
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<b>In order to use the bot you must join it's channel.</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(' Join Channel ! ', url=f't.me/{channel}')]
            ])
        )

    except pyrogram.ContinuePropagation:
        raise
    except pyrogram.StopPropagation:
        raise
    except BaseException as e:
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption=f"Error: {e}"
        )
        return message.continue_propagation()

@Bot.on_message(filters.command(["add", "add_premium"]) & filters.user(Bot.ADMINS))
async def add_handler(_, msg):
    sts = await msg.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Processing...</code>"
    )
    try:
        user_id = int(msg.text.split(" ")[1])
        time_limit_days = int(msg.text.split(" ")[2])
        await add_premium(user_id, time_limit_days)
        await retry_on_flood(
            sts.edit_caption
        )("<code>User added to premium successfully.</code>")
    except Exception as err:
        await retry_on_flood(
            sts.edit_caption
        )(f"<code>Error: {err}</code>")

@Bot.on_message(filters.command(["del", "del_premium"]) & filters.user(Bot.ADMINS))
async def del_handler(_, msg):
    sts = await msg.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Processing...</code>"
    )
    try:
        user_id = int(msg.text.split(" ")[1])
        await remove_premium(user_id)
        await retry_on_flood(
            sts.edit_caption
        )("<code>User removed from premium successfully.</code>")
    except Exception as err:
        await retry_on_flood(
            sts.edit_caption
        )(f"<code>Error: {err}</code>")

@Bot.on_message(filters.command(["del_expired", "del_expired_premium"]) & filters.user(Bot.ADMINS))
async def del_expired_handler(_, msg):
    sts = await msg.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Processing...</code>"
    )
    try:
        await remove_expired_users()
        await retry_on_flood(
            sts.edit_caption
        )("<code>Expired users removed successfully.</code>")
    except Exception as err:
        await retry_on_flood(
            sts.edit_caption
        )(f"<code>Error: {err}</code>")

@Bot.on_message(filters.command(["premium", "premium_users"]) & filters.user(Bot.ADMINS))
async def premium_handler(_, msg):
    sts = await msg.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Processing...</code>"
    )
    try:
        premium_users = acollection.find()
        txt = "<b>Premium Users:-</b>\n"
        for user in premium_users:
            user_ids = user["user_id"]
            user_info = await _.get_users(user_ids)
            username = user_info.username
            first_name = user_info.first_name
            expiration_timestamp = user["expiration_timestamp"]
            xt = (expiration_timestamp-(time.time()))
            x = round(xt/(24*60*60))
            txt += f"User id: <code>{user_ids}</code>\nUsername: @{username}\nName: <code>{first_name}</code>\nExpiration Timestamp: {x} days\n"

        await retry_on_flood(
            sts.edit_caption
        )(txt[:1024])
    except Exception as err:
        await retry_on_flood(
            sts.edit_caption
        )(f"<code>Error: {err}</code>")
  
@Bot.on_message(filters.command(["broadcast", "b"]) & filters.user(Bot.ADMINS))
async def b_handler(_, msg):
    return await borad_cast_(_, msg)

@Bot.on_message(filters.command(["pbroadcast", "pb"]) & filters.user(Bot.ADMINS))
async def pb_handler(_, msg):
    return await borad_cast_(_, msg, True)

async def borad_cast_(_, message, pin=None):
    def del_users(user_id):
        try:
            user_id = str(user_id)
            del uts[user_id]
            sync(_.DB_NAME, 'uts')
        except:
            pass
        
    sts = await message.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Processing...</code>"
    )
    if message.reply_to_message:
        user_ids = get_users()
        msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        await retry_on_flood(
            sts.edit_caption
        )("<code>Broadcasting...</code>")
        for user_id in user_ids:
            try:
                docs = await msg.copy(int(user_id))
                if pin:
                    await docs.pin(both_sides=True)
                
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                
                docs = await msg.copy(int(user_id))
                if pin:
                    await docs.pin(both_sides=True)
                
                successful += 1
            except pyrogram.errors.UserIsBlocked:
                del_users(user_id)
                blocked += 1
            except pyrogram.errors.PeerIdInvalid:
                del_users(user_id)
                unsuccessful += 1
            except pyrogram.errors.InputUserDeactivated:
                del_users(user_id)
                deleted += 1
            except pyrogram.errors.UserNotParticipant:
                del_users(user_id)
                blocked += 1
            except:
                unsuccessful += 1
        
        status = f"""<b><u>Broadcast Completed</u>

        Total Users: <code>{total}</code>
        Successful: <code>{successful}</code>
        Blocked Users: <code>{blocked}</code>
        Deleted Accounts: <code>{deleted}</code>
        Unsuccessful: <code>{unsuccessful}</code></b>"""
        
        await retry_on_flood(
            sts.edit_caption
        )(status)
    else:
        await retry_on_flood(
            sts.edit_caption
        )("<code>Reply to a message to broadcast it.</code>")

@Bot.on_message(filters.command("shell") & filters.user(Bot.ADMINS))
async def shell(_, message):
    cmd = message.text.split(maxsplit=1)
    if len(cmd) == 1:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<code>No command to execute was given.</code>"
        )

    cmd = cmd[1]
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()
    reply = ""
    if len(stdout) != 0:
        reply += f"<b>Stdout</b>\n<blockquote>{stdout}</blockquote>\n"
    if len(stderr) != 0:
        reply += f"<b>Stderr</b>\n<blockquote>{stderr}</blockquote>"

    if len(reply) > 3000:
        file_name = "shell_output.txt"
        with open(file_name, "w") as out_file:
            out_file.write(reply)
        await message.reply_document(file_name)
        os.remove(file_name)
    elif len(reply) != 0:
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption=reply
        )
    else:
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="No Reply"
        )
  
@Bot.on_message(filters.command("export") & filters.user(Bot.ADMINS))
async def export_(_, message):
    cmd = message.text.split(maxsplit=1)
    if len(cmd) == 1:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<code>File Name Not given.</code>"
        )
    
    sts = await message.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Processing...</code>"
    )
    try:
        file_name = cmd[1]
        if "*2" in file_name:
            file_name = file_name.replace("*2", "")
            file_name = f"__{file_name}__"
        
        if os.path.exists(file_name):
            await message.reply_document(file_name)
        else:
            await sts.edit_caption("<code>File Not Found</code>")
    except Exception as err:
        await sts.edit_caption(f"<code>Error: {err}</code>")

@Bot.on_message(filters.command("import") & filters.user(Bot.ADMINS))
async def import_(_, message):
    cmd = message.text.split(maxsplit=1)
    if len(cmd) == 1:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<code>File Name Not given.</code>"
        )

    sts = await message.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Processing...</code>"
    )
    try:
        file_name = cmd[1]
        if "*2" in file_name:
            file_name = file_name.replace("*2", "")
            file_name = f"__{file_name}__"

        if not os.path.exists(file_name):
            await message.download(file_name, file_name=file_name)
        else:
            await sts.edit_caption("<code>File Path Found</code>")
    except Exception as err:
        await sts.edit_caption(f"<code>Error: {err}</code>")

@Bot.on_message(filters.command(["deltask", "cleantasks", "del_tasks", "clean_tasks"]) & filters.user(Bot.ADMINS))
async def deltask(client, message):
    if Vars.IS_PRIVATE and message.chat.id not in Vars.ADMINS:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<blockquote>🚫 <b>Access Denied</b></blockquote>"
        )

    user_id = message.from_user.id
    numb = 0
    if user_id in queue._user_data:
        for task_id in queue._user_data[user_id]:
            await queue.delete_task(task_id)
            numb += 1
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption=f"All tasks deleted:- {numb}"
        )
    else:
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="No tasks found"
        )

@Bot.on_message(filters.command("updates"))
async def updates_(_, message):
    if Vars.IS_PRIVATE:
        if message.chat.id not in Vars.ADMINS:
            return await message.reply_photo(
                random.choice(Vars.PICS),
                caption="<code>You cannot use me baby </code>"
            )
    try:
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<b>Choose Sites</b>",
            reply_markup=plugins_list("updates"),
            quote=True,
        )
    except FloodWait as err:
        await asyncio.sleep(err.value)
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<b>Choose Sites</b>",
            reply_markup=plugins_list("updates"),
            quote=True,
        )
    except:
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<b>Choose Sites</b>",
            reply_markup=plugins_list("updates"),
            quote=True,
        )
  
@Bot.on_message(filters.command(["us", "user_setting", "user_panel"]))
async def userxsettings(client, message):
    if Vars.IS_PRIVATE:
        if message.chat.id not in Vars.ADMINS:
            return await message.reply_photo(
                random.choice(Vars.PICS),
                caption="<code>You cannot use me baby </code>"
            )
    
    sts = await message.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Processing...</code>"
    )
    try:
        db_type = "uts"
        name = Vars.DB_NAME
        user_id = str(message.from_user.id)
        if not user_id in uts:
            uts[user_id] = {}
            sync(name, db_type)

        if not "setting" in uts[user_id]:
            uts[user_id]['setting'] = {}
            sync(name, db_type)

        thumbnali = uts[user_id]['setting'].get("thumb", None)
        if thumbnali:
            thumb = "True" if not thumbnali.startswith("http") else thumbnali
        else:
            thumb = thumbnali

        banner1 = uts[user_id]['setting'].get("banner1", None)
        banner2 = uts[user_id]['setting'].get("banner2", None)
        if banner1:
            banner1 = "True" if not banner1.startswith("http") else banner1

        if banner2:
            banner2 = "True" if not banner2.startswith("http") else banner2

        txt = users_txt.format(
            id=user_id,
            file_name=uts[user_id]['setting'].get("file_name", "None"),
            caption=uts[user_id]['setting'].get("caption", "None"),
            thumb=thumb,
            banner1=banner1,
            banner2=banner2,
            dump=uts[user_id]['setting'].get("dump", "None"),
            type=uts[user_id]['setting'].get("type", "None"),
            megre=uts[user_id]['setting'].get("megre", "None"),
            regex=uts[user_id]['setting'].get("regex", "None"),
            len=uts[user_id]['setting'].get("file_name_len", "None"),
            password=uts[user_id]['setting'].get("password", "None"),
        )

        button = [
            [
                InlineKeyboardButton("🪦 File Name 🪦", callback_data="ufn"),
                InlineKeyboardButton("🪦 Caption‌ 🪦", callback_data="ucp")
            ],
            [
                InlineKeyboardButton("🪦 Thumbnali 🪦", callback_data="uth"),
                InlineKeyboardButton("🪦 Regex 🪦", callback_data="uregex")
            ],
            [
                InlineKeyboardButton("⚒ Banner ⚒", callback_data="ubn"),
            ],
            [
                InlineKeyboardButton("⚙️ Password ⚙️", callback_data="upass"),
                InlineKeyboardButton("⚙️ Megre Size ⚙️", callback_data="umegre")
            ],
            [
                InlineKeyboardButton("⚒ File Type ⚒", callback_data="u_file_type"),
            ],
        ]
        if not Vars.CONSTANT_DUMP_CHANNEL:
            button[-1].append(InlineKeyboardButton("⚒ Dump Channel ⚒", callback_data="udc"))
        
        button.append([InlineKeyboardButton("❄️ Close ❄️", callback_data="close")])
        if not thumbnali:
            thumbnali = random.choice(Vars.PICS)
        try:
            await message.reply_photo(
                thumbnali,
                caption=txt,
                reply_markup=InlineKeyboardMarkup(button)
            )
        except FloodWait as err:
            await asyncio.sleep(err.value)
            await message.reply_photo(
                thumbnali,
                caption=txt,
                reply_markup=InlineKeyboardMarkup(button)
            )
        except:
            await message.reply_photo(
                random.choice(Vars.PICS),
                caption=txt,
                reply_markup=InlineKeyboardMarkup(button)
            )

        await sts.delete()
    except Exception as err:
        logger.exception(err)
        await sts.edit_caption(f"<code>Error: {err}</code>")

@Bot.on_message(filters.command("subs"))
async def subs(_, message):
    if _.IS_PRIVATE and message.chat.id not in _.ADMINS:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<code>You cannot use me baby </code>"
        )
    
    sts = await message.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Getting Subs...</code>"
    )
    txt = "<b>Subs List:-</b>\n"
    try:
        subs_list = get_subs(message.from_user.id)
        for sub in subs_list:
            txt += f"<blockquote>=> <code>{sub}</code></blockquote>\n"
        
        txt += f"<blockquote>=> <code>Total Subs:- {len(subs_list)}</code></blockquote>"
        txt += f"\n\n<b>To Unsubs:-</b>\n<blockquote><code>/unsubs url</code></blockquote>"
        await retry_on_flood(
            sts.edit_caption
        )(txt[:1024])
    except Exception as err:
        await retry_on_flood(
            sts.edit_caption
        )(f"<code>Error: {err}</code>")

@Bot.on_message(filters.command("unsubs"))
async def unsubs(_, message):
    if _.IS_PRIVATE and message.chat.id not in _.ADMINS:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<code>You cannot use me baby </code>"
        )
    
    sts = await message.reply_photo(
        random.choice(Vars.PICS),
        caption="<code>Processing to Unsubs...</code>"
    )
    try:
        txt = message.text.split(" ")[1]
        if txt in dts:
            if message.from_user.id in dts[txt]['users']:
                dts[txt]['users'].remove(message.from_user.id)
                sync(_.DB_NAME, 'dts')
                await retry_on_flood(
                    sts.edit_caption
                )("<code>Sucessfully Unsubs</code>")
            else:
                await retry_on_flood(
                    sts.edit_caption
                )("<code>You are not subscribed to this manga</code>")
        else:
            await retry_on_flood(
                sts.edit_caption
            )("<code>Manga not found</code>")
    except Exception as err:
        await retry_on_flood(
            sts.edit_caption
        )(f"<code>Error: {err}</code>")

@Bot.on_message(filters.command("search"))
async def search_group(client, message):
    if Vars.IS_PRIVATE and message.chat.id not in Vars.ADMINS:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<code>You cannot use me baby </code>"
        )
    
    if client.SHORTENER:
        if not await premium_user(message.from_user.id):
            if not verify_token(message.from_user.id):
                if not message.from_user.id in client.ADMINS:
                    return await get_token(message, message.from_user.id)
        
    try: 
        txt = message.text.split(" ")[1]
    except: 
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<code>Format:- /search Manga </code>"
        )

    try: 
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="Select search Webs .", 
            reply_markup=plugins_list(), 
            quote=True
        )
    except ValueError: 
        await message.reply_photo(
            random.choice(Vars.PICS),
            caption="Select search Webs .", 
            reply_markup=plugins_list(), 
            quote=True
        )

@Bot.on_message(filters.text & filters.private)
async def search(client, message):
    if Vars.IS_PRIVATE and message.chat.id not in Vars.ADMINS:
        return await message.reply_photo(
            random.choice(Vars.PICS),
            caption="<code>You cannot use me baby </code>"
        )

    txt = message.text
    if not txt.startswith("/"):
        try: 
            await message.reply_photo(
                random.choice(Vars.PICS),
                caption="Select search Webs .", 
                reply_markup=plugins_list(), 
                quote=True
            )
        except ValueError: 
            await message.reply_photo(
                random.choice(Vars.PICS),
                caption="Select search Webs .", 
                reply_markup=plugins_list(), 
                quote=True
            )

@Bot.on_callback_query(filters.regex("^help_"))
async def help_callback(client, callback):
    data = callback.data.split("_")[1]
    
    try:
        if data == "guide":
            await callback.edit_message_caption(
                HELP_MSG,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="help_main")],
                    [InlineKeyboardButton("❌ Close", callback_data="close")]
                ])
            )
        elif data == "admin":
            await callback.edit_message_caption(
                ADMIN_HELP_MSG,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="help_main")],
                    [InlineKeyboardButton("❌ Close", callback_data="close")]
                ])
            )
        else:
            buttons = []
            if callback.from_user.id in Vars.ADMINS:
                buttons.append([InlineKeyboardButton("👑 Admin Help", callback_data="help_admin")])
            
            buttons.extend([
                [InlineKeyboardButton("📚 User Guide", callback_data="help_guide")],
                [InlineKeyboardButton("❌ Close", callback_data="close")]
            ])
            
            await callback.edit_message_caption(
                "<b>📚 Help Center</b>\n\n"
                "<blockquote>Select the help section you need:</blockquote>",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        logger.error(f"Error in help callback: {e}")
        await callback.answer("Error loading help, please try again", show_alert=True)


@Bot.on_callback_query(filters.regex("^refresh_"))
async def refresh_callback(client, callback):
    data = callback.data.split("_")[1]
    
    if data == "stats":
        await show_ping(client, callback.message)
    elif data == "queue":
        await queue_msg_handler(client, callback.message)
    
    await callback.answer("✅ Refreshed")

@Bot.on_callback_query(filters.regex("^close$"))
async def close_callback(client, callback):
    await callback.message.delete()
    await callback.answer("Closed")

def humanbytes(size):    
    if not size:
        return ""
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def GET_PROVIDER():
    provider = "Unknown"
    try:
        if os.path.exists('/sys/hypervisor/uuid'):
            with open('/sys/hypervisor/uuid', 'r') as f:
                uuid = f.read().lower()
                if uuid.startswith('ec2'): provider = "AWS EC2"
                elif 'azure' in uuid: provider = "Microsoft Azure"

        elif os.path.exists('/etc/google-cloud-environment'):
            provider = "Google Cloud"

        elif os.path.exists('/etc/digitalocean'):
            provider = "DigitalOcean"

        elif os.path.exists('/dev/disk/by-id/scsi-0Linode'):
            provider = "Linode"

        elif os.path.exists('/etc/vultr'):
            provider = "Vultr"

    except Exception:
        pass
    
    return provider

def remove_dir(path):
    try:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                    for dir in dirs:
                        os.rmdir(os.path.join(root, dir))
            os.rmdir(path)
    except Exception as err:
        return err
