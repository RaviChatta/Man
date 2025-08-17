from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from .storage import *
from bot import Bot, Vars, logger
import random
from Tools.db import *
from pyrogram.errors import FloodWait
import asyncio
from typing import Dict, List, Optional, Tuple, Union

# Helper function to handle flood waits
async def retry_on_flood(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await func(*args, **kwargs)

# ========================
# BASIC HANDLERS
# ========================

@Bot.on_callback_query(filters.regex("close"))
async def close_handler(_, query):
    """Elegantly close the message with proper cleanup"""
    try:
        await query.message.delete()
        if query.message.reply_to_message:
            await query.message.reply_to_message.delete()
    except Exception:
        pass
    
    try:
        await query.answer("Closed ✅")
    except Exception:
        pass

@Bot.on_callback_query(filters.regex("premuim"))
async def premuim_handler(_, query):
    """Premium subscription information"""
    premium_text = """
<b>🎖 <u>Premium Subscription Plans</u></b>

<blockquote>
<b>📅 7 Days</b> 
  - ₹30 / $0.35 / NRS 40

<b>📅 1 Month</b> 
  - ₹90 / $1.05 / NRS 140

<b>📅 3 Months</b> 
  - ₹260 / $2.94 / NRS 350

<b>📅 6 Months</b> 
  - ₹500 / $6.33 / NRS 700

<b>📅 9 Months</b> 
  - ₹780 / $9.14 / NRS 1100

<b>📅 12 Months</b> 
  - ₹1000 / $11.8 / NRS 1400
</blockquote>

<b>💎 Premium Benefits:</b>
<blockquote>
• Priority access to new features
• Faster download speeds
• Exclusive content
• Ad-free experience
</blockquote>

<b>🔹 Contact Admin:</b> @Shanks_Kun
<blockquote><i>Limited seats available for premium users</i></blockquote>
"""
    
    # Keep the existing buttons except the premium one
    buttons = query.message.reply_markup.inline_keyboard
    new_buttons = [row for row in buttons if not any("premuim" in btn.callback_data for btn in row)]
    
    await retry_on_flood(
        query.edit_message_text,
        premium_text,
        reply_markup=InlineKeyboardMarkup(new_buttons)
    )

# ========================
# MANGA/CHAPTER HANDLERS
# ========================

@Bot.on_callback_query(filters.regex("^chs"))
async def ch_handler(client, query):
    """Handle chapter selection"""
    reply = query.message.reply_to_message
    if not reply:
        return await query.answer("This command needs to be used in reply to a message", show_alert=True)

    # Verify user ownership
    if reply.from_user.id != query.from_user.id:
        return await query.answer("❌ This action is not for you", show_alert=True)

    try:
        webs, data = searchs[query.data]
    except KeyError:
        return await query.answer("⌛ This button has expired, please search again", show_alert=True)

    try:
        bio_list = await webs.get_chapters(data)
        if not bio_list:
            return await query.answer("❌ No chapters found", show_alert=True)
    except Exception as e:
        logger.error(f"Error getting chapters: {e}")
        return await query.answer("⚠️ Error fetching chapters", show_alert=True)

    # Update media if poster available
    if "poster" in bio_list:
        try:
            await query.edit_message_media(InputMediaPhoto(bio_list['poster']))
        except Exception:
            pass

    # Store chapter data
    c = query.data.replace("chs", "ch")
    chaptersList[c] = (webs, bio_list, data)
    sf = webs.sf

    # Prepare response text
    message_text = bio_list['msg'][:1022] if "msg" in bio_list else f"<b>{bio_list['title']}</b>"

    buttons = [
        [
            InlineKeyboardButton("📚 Chapters", callback_data=c),
            InlineKeyboardButton("🔙 Back", callback_data=f"bk.s.{sf}")
        ]
    ]
    
    await retry_on_flood(
        query.edit_message_text,
        message_text,
        reply_markup=InlineKeyboardMarkup(buttons))

# ========================
# PAGINATION HANDLERS
# ========================

@Bot.on_callback_query(filters.regex("^pg"))
async def pg_handler(client, query):
    """Handle pagination for chapter lists"""
    reply = query.message.reply_to_message
    if not reply:
        return await query.answer("This command needs to be used in reply to a message", show_alert=True)

    # Verify user ownership
    if reply.from_user.id != query.from_user.id:
        return await query.answer("❌ This action is not for you", show_alert=True)

    data_parts = query.data.split(":")
    if len(data_parts) < 4:
        return await query.answer("Invalid pagination data", show_alert=True)

    page = data_parts[-1]
    base_data = ":".join(data_parts[:-1]) + ":"
    
    if base_data not in pagination:
        return await query.answer("⌛ This button has expired, please search again", show_alert=True)

    webs, data, rdata = pagination[base_data]
    sf = webs.sf
    
    # Check subscription status
    subs_bool = get_subs(str(query.from_user.id), rdata['url'])

    # Get chapters based on page
    try:
        if sf == "ck":
            chapters = await webs.get_chapters(rdata, int(page))
            if not chapters:
                return await query.answer("❌ No chapters found", show_alert=True)
            chapters = webs.iter_chapters(chapters)
        else:
            try:
                chapters = await webs.iter_chapters(data, int(page))
            except TypeError:
                chapters = webs.iter_chapters(data, int(page))
    except Exception as e:
        logger.error(f"Error getting paginated chapters: {e}")
        return await query.answer("⚠️ Error loading chapters", show_alert=True)

    if not chapters:
        return await query.answer("❌ No chapters found", show_alert=True)

    # Build chapter buttons
    buttons = []
    for chapter in chapters:
        c = f"pic|{hash(chapter['url'])}"
        chaptersList[c] = (webs, chapter)
        btn_text = f"Ch. {chapter['title']}" if chapter['title'].isdigit() else chapter['title']
        buttons.append(InlineKeyboardButton(btn_text, callback_data=c))

    # Split buttons into rows
    buttons = split_list(buttons[:60])
    
    # Add pagination controls
    c = f"pg:{sf}:{hash(chapters[-1]['url'])}:"
    pagination[c] = (webs, data, rdata)
    
    nav_buttons = []
    current_page = int(page)
    
    # Previous page buttons
    if current_page > 1:
        nav_buttons.extend([
            InlineKeyboardButton("⏮", callback_data=f"{c}1"),
            InlineKeyboardButton("◀", callback_data=f"{c}{current_page - 1}")
        ])
    
    # Next page buttons
    nav_buttons.extend([
        InlineKeyboardButton("▶", callback_data=f"{c}{current_page + 1}"),
        InlineKeyboardButton("⏭", callback_data=f"{c}{current_page + 10}")
    ])
    
    buttons.append(nav_buttons)

    # Add subscription button
    sub_callback = f"subs:{hash(rdata['url'])}"
    subscribes[sub_callback] = (webs, rdata)
    sub_button = [InlineKeyboardButton(
        "🔔 Subscribed" if subs_bool else "📯 Subscribe", 
        callback_data=sub_callback)
    ]
    buttons.insert(0, sub_button)

    # Add special buttons based on source
    if sf == "ck":
        scan_callback = f"sgh:{sf}:{hash(chapters[0]['url'])}"
        pagination[scan_callback] = (chapters, webs, rdata, page)
        buttons.append([InlineKeyboardButton("👥 Scanlation Groups", callback_data=scan_callback)])
    else:
        full_callback = f"full:{sf}:{hash(chapters[0]['url'])}"
        if int(page) == 1:
            pagination[full_callback] = (chapters[:60], webs)
        else:
            pagination[full_callback] = (chapters, webs)
        buttons.append([InlineKeyboardButton("📖 All Chapters", callback_data=full_callback)])

    # Add back button
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"bk.s.{sf}")])

    await retry_on_flood(
        query.edit_message_reply_markup,
        reply_markup=InlineKeyboardMarkup(buttons))

# ========================
# SCANLATION GROUP HANDLERS
# ========================

@Bot.on_callback_query(filters.regex("^sgh"))
async def cgk_handler(client, query):
    """Handle scanlation group selection"""
    if query.data not in pagination:
        return await query.answer("⌛ This button has expired, please search again", show_alert=True)

    reply = query.message.reply_to_message
    if reply and reply.from_user.id != query.from_user.id:
        return await query.answer("❌ This action is not for you", show_alert=True)

    chapters, webs, rdata, page = pagination[query.data]
    
    # Organize chapters by group
    groups: Dict[str, List[Dict]] = {}
    for chapter in chapters:
        group_name = chapter.get('group_name', 'Unknown')
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(chapter)

    # Build group buttons
    buttons = []
    for group_name, group_chapters in groups.items():
        group_len = len(group_chapters)
        c = f"sgk|{hash(group_name)}"
        pagination[c] = (group_chapters, webs, page, f"pg:{webs.sf}:{hash(chapters[-1]['url'])}:{page}", query.data)
        
        group_display = group_name if group_name != 'Unknown' else 'No Group'
        buttons.append([
            InlineKeyboardButton(f"{group_display} ({group_len})", callback_data=c)
        ])
    
    # Add back button
    back_callback = f"pg:{webs.sf}:{hash(chapters[-1]['url'])}:{page}"
    buttons.append([InlineKeyboardButton("🔙 Back to Chapters", callback_data=back_callback)])
    
    await retry_on_flood(
        query.edit_message_reply_markup,
        reply_markup=InlineKeyboardMarkup(buttons))
    
    await query.answer()

# ========================
# DOWNLOAD HANDLERS
# ========================

@Bot.on_callback_query(filters.regex("^full"))
async def full_handler(client, query):
    """Handle full chapter downloads"""
    if query.data not in pagination:
        return await query.answer("⌛ This button has expired, please search again", show_alert=True)

    reply = query.message.reply_to_message
    if not reply:
        return await query.answer("This command needs to be used in reply to a message", show_alert=True)

    # Verify user ownership
    if reply.from_user.id != query.from_user.id:
        return await query.answer("❌ This action is not for you", show_alert=True)

    chapters, webs = pagination[query.data]
    added_item = []

    # Get user settings
    user_settings = uts.get(str(query.from_user.id), {}).get('setting', {})
    merge_size = user_settings.get('megre')
    if merge_size:
        merge_size = int(merge_size)

    # Reverse chapters for proper ordering
    chapters = list(reversed(chapters)) 

    # Process chapters based on merge settings
    if merge_size:
        for i in range(0, len(chapters), merge_size):
            batch = chapters[i:i + merge_size]
            raw_data = []
            pictures = []
            
            for chapter in batch:
                episode_num = get_episode_number(chapter['title'])
                if episode_num not in added_item:
                    try:
                        pictures_ex = await webs.get_pictures(url=chapter['url'], data=chapter)
                        if pictures_ex:
                            if webs.bg:
                                pictures_ex.pop(0)  # Remove background if exists
                            pictures.extend(pictures_ex)
                            added_item.append(episode_num)
                            raw_data.append(chapter)
                    except Exception as e:
                        logger.error(f"Error getting pictures: {e}")
                        continue
            
            if pictures:
                task_id = await queue.put((raw_data, pictures, query, None, webs), query.from_user.id)
    else:
        for chapter in chapters:
            episode_num = get_episode_number(chapter['title'])
            if episode_num not in added_item:
                try:
                    pictures = await webs.get_pictures(url=chapter['url'], data=chapter)
                    if not pictures:
                        continue
                    
                    task_id = await queue.put((chapter, pictures, query, None, webs), query.from_user.id)
                    added_item.append(episode_num)
                except Exception as e:
                    logger.error(f"Error processing chapter: {e}")
                    continue
    
    await query.answer("✅ Added to download queue", show_alert=True)

# ========================
# SUBSCRIPTION HANDLERS
# ========================

@Bot.on_callback_query(filters.regex("^subs"))
async def subs_handler(client, query):
    """Handle manga subscriptions"""
    if query.data not in subscribes:
        return await query.answer("⌛ This button has expired, please search again", show_alert=True)

    webs, data = subscribes[query.data]

    reply = query.message.reply_to_message
    if not reply:
        return await query.answer("This command needs to be used in reply to a message", show_alert=True)

    # Verify user ownership
    if reply.from_user.id != query.from_user.id:
        return await query.answer("❌ This action is not for you", show_alert=True)

    # Get current buttons
    buttons = query.message.reply_markup.inline_keyboard

    # Toggle subscription status
    if get_subs(str(query.from_user.id), data['url']):
        delete_sub(str(query.from_user.id), data['url'])
        buttons[0] = [InlineKeyboardButton("📯 Subscribe", callback_data=query.data)]
        await query.answer("❌ Unsubscribed")
    else:
        add_sub(str(query.from_user.id), data['url'])
        buttons[0] = [InlineKeyboardButton("🔔 Subscribed", callback_data=query.data)]
        await query.answer("✅ Subscribed")

    await retry_on_flood(
        query.edit_message_reply_markup,
        reply_markup=InlineKeyboardMarkup(buttons))

# ========================
# PICTURE DOWNLOAD HANDLERS
# ========================

@Bot.on_callback_query(filters.regex("^pic"))
async def pic_handler(client, query):
    """Handle individual chapter downloads"""
    if query.data not in chaptersList:
        return await query.answer("⌛ This button has expired, please search again", show_alert=True)

    webs, data = chaptersList[query.data]
    
    reply = query.message.reply_to_message
    if not reply:
        return await query.answer("This command needs to be used in reply to a message", show_alert=True)

    # Verify user ownership
    if reply.from_user.id != query.from_user.id:
        return await query.answer("❌ This action is not for you", show_alert=True)

    try:
        pictures = await webs.get_pictures(url=data['url'], data=data)
        if not pictures:
            return await query.answer("❌ No pictures found", show_alert=True)
    except Exception as e:
        logger.error(f"Error getting pictures: {e}")
        return await query.answer("⚠️ Error loading chapter", show_alert=True)

    # Send initial status message
    status_msg = await retry_on_flood(
        query.message.reply_text,
        "<i>⏳ Adding to download queue...</i>")

    # Prepare caption
    caption = f"""
<b>📖 Manga:</b> {data.get('manga_title', 'N/A')}
<b>📚 Chapter:</b> {data.get('title', 'N/A')}
"""
    if 'group_name' in data and data['group_name']:
        caption += f"<b>👥 Group:</b> {data['group_name']}\n"

    # Add to queue and get task ID
    task_id = await queue.put((data, pictures, query, status_msg, webs), query.from_user.id)

    # Add cancel button
    buttons = [[
        InlineKeyboardButton("❌ Cancel Download", callback_data=f"cl:{task_id}")
    ]]
    
    await retry_on_flood(
        status_msg.edit,
        caption,
        reply_markup=InlineKeyboardMarkup(buttons))

# ========================
# TASK MANAGEMENT HANDLERS
# ========================

@Bot.on_callback_query(filters.regex("^cl"))
async def cl_handler(client, query):
    """Handle task cancellation"""
    task_id = query.data.split(":")[-1]
    
    if await queue.delete_task(task_id):
        await retry_on_flood(
            query.message.edit_text,
            "<b>❌ Download Cancelled</b>")
        await query.answer("Download cancelled", show_alert=True)
    else:
        await retry_on_flood(
            query.answer,
            "Task not found or already completed",
            show_alert=True)

# ========================
# NAVIGATION HANDLERS
# ========================

@Bot.on_callback_query(filters.regex("^bk"))
async def bk_handler(client, query):
    """Handle back navigation"""
    reply = query.message.reply_to_message
    if reply:
        try:
            if reply.from_user.id != query.from_user.id:
                return await query.answer("❌ This action is not for you", show_alert=True)
        except Exception:
            pass
    
    if query.data == "bk.p":
        # Return to main menu
        try:
            await query.edit_message_media(InputMediaPhoto(random.choice(Vars.PICS)))
        except Exception:
            pass
        
        if reply and reply.text == "/updates":
            await query.edit_message_reply_markup(plugins_list("updates"))
        else:
            await query.edit_message_reply_markup(plugins_list())
    
    elif query.data.startswith("bk.s"):
        # Return to search results
        sf = query.data.split(".")[-1]
        
        search_text = reply.text if reply else ""
        if search_text.startswith("/search"):
            search = search_text.split(" ", 1)[-1]
        else:
            search = search_text

        webs = get_webs(sf)
        if not webs:
            return await query.answer("❌ Source not available", show_alert=True)

        # Update UI
        try:
            await query.edit_message_media(InputMediaPhoto(random.choice(Vars.PICS)))
        except Exception:
            pass

        # Show loading state
        try:
            await query.message.edit_text("<i>🔍 Searching...</i>")
        except Exception:
            pass

        # Get results
        try:
            if reply and reply.text.startswith("/updates"):
                results = await webs.get_updates()
                for result in results:
                    result['title'] = result.pop('manga_title')
            else:
                results = await webs.search(search)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return await query.message.edit_text(
                "<b>❌ Error fetching results</b>",
                reply_markup=query.message.reply_markup)

        if not results:
            return await query.message.edit_text(
                "<b>❌ No results found</b>",
                reply_markup=query.message.reply_markup)

        # Build results buttons
        buttons = []
        for result in results:
            callback_data = f"chs|{query.data}{result['id']}" if "id" in result else f"chs|{query.data}{hash(result['url'])}"
            searchs[callback_data] = (webs, result)
            
            title = result['title'][:50] + "..." if len(result['title']) > 50 else result['title']
            buttons.append([InlineKeyboardButton(title, callback_data=callback_data)])

        # Add back button
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="bk.p")])
        
        await retry_on_flood(
            query.edit_message_text,
            "<b>📚 Select Manga</b>",
            reply_markup=InlineKeyboardMarkup(buttons))

# ========================
# UPDATES HANDLER
# ========================

@Bot.on_callback_query(filters.regex("^udat"))
async def updates_handler(_, query):
    """Handle manga updates"""
    sf = query.data.split("_")[-1]
    webs = get_webs(sf)
    
    if not webs:
        return await query.answer("❌ Source not available", show_alert=True)

    await retry_on_flood(
        query.edit_message_text,
        "<i>🔄 Fetching latest updates...</i>")

    try:
        results = await webs.get_updates()
        if not results:
            return await query.answer("⚠️ No updates available", show_alert=True)
        
        # Prepare buttons
        buttons = []
        for result in results[:60]:  # Limit to 60 results
            result['title'] = result.pop('manga_title', 'Untitled')
            callback_data = f"chs|{sf}{result['id']}" if "id" in result else f"chs|{sf}{hash(result['url'])}"
            searchs[callback_data] = (webs, result)
            
            title = result['title'][:50] + "..." if len(result['title']) > 50 else result['title']
            buttons.append([InlineKeyboardButton(title, callback_data=callback_data)])

        # Add back button
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="bk.p")])
        
        # Update UI
        try:
            await query.edit_message_media(InputMediaPhoto(random.choice(Vars.PICS)))
        except Exception:
            pass
        
        await retry_on_flood(
            query.edit_message_text,
            "<b>🆕 Latest Updates</b>",
            reply_markup=InlineKeyboardMarkup(buttons))
        
        await query.answer()
    except Exception as e:
        logger.error(f"Updates error: {e}")
        await query.answer("⚠️ Error fetching updates", show_alert=True)

# ========================
# PLUGIN HANDLER
# ========================

@Bot.on_callback_query(filters.regex("^plugin_"))
async def cb_handler(client, query):
    """Handle plugin selection"""
    data = query.data.split("_")[-1]
    
    reply = query.message.reply_to_message
    if not reply:
        return await query.answer("This command needs to be used in reply to a message", show_alert=True)

    # Verify user ownership
    if reply.from_user.id != query.from_user.id:
        return await query.answer("❌ This action is not for you", show_alert=True)

    # Get search query
    if reply.text.startswith("/search"):
        search = reply.text.split(" ", 1)[-1]
    else:
        search = reply.text

    # Find matching web source
    for key in web_data:
        if data == web_data[key].sf:
            webs = web_data[key]
            
            # Update UI
            try:
                await query.edit_message_media(InputMediaPhoto(random.choice(Vars.PICS)))
            except Exception:
                pass

            await retry_on_flood(
                query.edit_message_text,
                "<i>🔍 Searching...</i>")

            try:
                results = await webs.search(search)
                if not results:
                    return await query.message.edit_text(
                        "<b>❌ No results found</b>",
                        reply_markup=query.message.reply_markup)

                # Prepare buttons
                buttons = []
                for result in results:
                    callback_data = f"chs|{data}{result['id']}" if "id" in result else f"chs|{data}{hash(result['url'])}"
                    searchs[callback_data] = (webs, result)
                    
                    title = result['title'][:50] + "..." if len(result['title']) > 50 else result['title']
                    buttons.append([InlineKeyboardButton(title, callback_data=callback_data)])

                # Add back button
                buttons.append([InlineKeyboardButton("🔙 Back", callback_data="bk.p")])
                
                await retry_on_flood(
                    query.edit_message_text,
                    "<b>📚 Select Manga</b>",
                    reply_markup=InlineKeyboardMarkup(buttons))
                
                await query.answer()
                return
            except Exception as e:
                logger.error(f"Search error: {e}")
                return await query.message.edit_text(
                    "<b>❌ Error fetching results</b>",
                    reply_markup=query.message.reply_markup)

    await query.answer('⌛ This button has expired, please search again', show_alert=True)

# ========================
# USER SETTINGS HANDLERS
# ========================

# User settings template
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
<b>🔐 Password:</b> <code>{password}</code>
</blockquote>

<b>📌 Banners:</b>
<blockquote>
<b>1:</b> <code>{banner1}</code>
<b>2:</b> <code>{banner2}</code>
</blockquote>
"""

@Bot.on_callback_query(filters.regex("mus"))
async def main_user_panel(_, query):
    """Main user settings panel"""
    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    settings = uts[user_id].get('setting', {})
    
    # Get thumbnail
    thumb = settings.get("thumb")
    if thumb and not thumb.startswith("http"):
        thumb = "Custom" if thumb != "constant" else "Manga Poster"
    
    # Prepare settings text
    txt = users_txt.format(
        id=user_id,
        file_name=settings.get("file_name", "Default"),
        caption=settings.get("caption", "Default"),
        thumb=thumb or "Random",
        banner1=settings.get("banner1", "Not Set"),
        banner2=settings.get("banner2", "Not Set"),
        dump=settings.get("dump", "Not Set"),
        type=", ".join(settings.get("type", [])) or "Not Set",
        megre=settings.get("megre", "Not Set"),
        regex=settings.get("regex", "Not Set"),
        len=settings.get("file_name_len", "Not Set"),
        password=settings.get("password", "Not Set"),
    )

    # Prepare buttons
    buttons = [
        [
            InlineKeyboardButton("📝 File Name", callback_data="ufn"),
            InlineKeyboardButton("📋 Caption", callback_data="ucp")
        ],
        [
            InlineKeyboardButton("🖼 Thumbnail", callback_data="uth"),
            InlineKeyboardButton("🔍 Regex", callback_data="uregex")
        ],
        [
            InlineKeyboardButton("📡 Dump Channel", callback_data="udc"),
            InlineKeyboardButton("📦 File Type", callback_data="u_file_type")
        ],
        [
            InlineKeyboardButton("🔢 Merge Size", callback_data="umegre"),
            InlineKeyboardButton("🔐 Password", callback_data="upass")
        ],
        [
            InlineKeyboardButton("📌 Banners", callback_data="ubn"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ]
    ]

    # Set thumbnail for display
    display_thumb = settings.get("thumb") or random.choice(Vars.PICS)
    if isinstance(display_thumb, str) and display_thumb.startswith("http"):
        display_thumb = display_thumb
    elif display_thumb == "constant":
        display_thumb = random.choice(Vars.PICS)
    
    try:
        await query.edit_message_media(InputMediaPhoto(display_thumb))
    except Exception:
        pass

    try:
        await query.edit_message_caption(
            txt,
            reply_markup=InlineKeyboardMarkup(buttons))
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await query.edit_message_caption(
            txt,
            reply_markup=InlineKeyboardMarkup(buttons))
    
    await query.answer()

# ========================
# FILE NAME SETTINGS
# ========================

@Bot.on_callback_query(filters.regex("^ufn"))
async def file_name_handler(_, query):
    """Handle file name settings"""
    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    settings = uts[user_id].get('setting', {})
    
    # Prepare buttons
    buttons = [
        [
            InlineKeyboardButton("✏️ Set/Change", callback_data="ufn_change"),
            InlineKeyboardButton("🗑️ Delete", callback_data="ufn_delete")
        ],
        [
            InlineKeyboardButton("📏 Set Length", callback_data="ufn_len_change"),
            InlineKeyboardButton("🗑️ Del Length", callback_data="ufn_len_delete")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="mus")
        ]
    ]

    if query.data == "ufn":
        # Show current settings
        await retry_on_flood(
            query.edit_message_reply_markup,
            reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data == "ufn_change":
        # Change file name pattern
        await retry_on_flood(
            query.edit_message_caption,
            """<b>📝 Set File Name Pattern</b>

<blockquote>
<b>Available variables:</b>
• <code>{manga_title}</code> - Manga name
• <code>{chapter_num}</code> - Chapter number
• <code>{group_name}</code> - Scanlation group

<b>Example:</b>
<code>{manga_title} - {chapter_num}</code>
</blockquote>

<i>Send your new file name pattern:</i>"""
        )
        
        try:
            response = await _.listen(user_id=int(user_id), timeout=60)
            new_pattern = response.text
            
            uts[user_id]['setting']["file_name"] = new_pattern
            sync(Vars.DB_NAME, "uts")
            
            await response.delete()
            await query.answer("✅ File name pattern updated")
            
            # Update display
            await main_user_panel(_, query)
        except asyncio.TimeoutError:
            await query.answer("⌛ Timed out waiting for response")
    
    elif query.data == "ufn_delete":
        # Reset file name pattern
        if "file_name" in uts[user_id]['setting']:
            del uts[user_id]['setting']["file_name"]
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ File name pattern reset to default")
        else:
            await query.answer("ℹ️ No custom file name pattern set")
        
        # Update display
        await main_user_panel(_, query)
    
    elif query.data == "ufn_len_change":
        # Change file name length limit
        await retry_on_flood(
            query.edit_message_caption,
            """<b>📏 Set File Name Length Limit</b>

<blockquote>
Enter the maximum number of characters for file names
(Recommended: between 20-100)

<b>Example:</b> <code>50</code>
</blockquote>

<i>Send the new length limit:</i>"""
        )
        
        try:
            response = await _.listen(user_id=int(user_id), timeout=60)
            try:
                length = int(response.text)
                uts[user_id]['setting']["file_name_len"] = length
                sync(Vars.DB_NAME, "uts")
                
                await response.delete()
                await query.answer(f"✅ Length limit set to {length}")
            except ValueError:
                await query.answer("❌ Please enter a valid number", show_alert=True)
            
            # Update display
            await main_user_panel(_, query)
        except asyncio.TimeoutError:
            await query.answer("⌛ Timed out waiting for response")
    
    elif query.data == "ufn_len_delete":
        # Reset file name length limit
        if "file_name_len" in uts[user_id]['setting']:
            del uts[user_id]['setting']["file_name_len"]
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ Length limit removed")
        else:
            await query.answer("ℹ️ No length limit set")
        
        # Update display
        await main_user_panel(_, query)

# ========================
# CAPTION SETTINGS
# ========================

@Bot.on_callback_query(filters.regex("^ucp"))
async def caption_handler(_, query):
    """Handle caption settings"""
    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    settings = uts[user_id].get('setting', {})
    
    # Prepare buttons
    buttons = [
        [
            InlineKeyboardButton("✏️ Set/Change", callback_data="ucp_change"),
            InlineKeyboardButton("🗑️ Delete", callback_data="ucp_delete")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="mus")
        ]
    ]

    if query.data == "ucp":
        # Show current settings
        await retry_on_flood(
            query.edit_message_reply_markup,
            reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data == "ucp_change":
        # Change caption pattern
        await retry_on_flood(
            query.edit_message_caption,
            """<b>📋 Set Caption Pattern</b>

<blockquote>
<b>HTML Formatting Supported:</b>
&lt;b&gt;Bold&lt;/b&gt;, &lt;i&gt;Italic&lt;/i&gt;, etc.

<b>Available variables:</b>
• <code>{manga_title}</code> - Manga name
• <code>{chapter_num}</code> - Chapter number
• <code>{group_name}</code> - Scanlation group
• <code{file_name}</code> - File name

<b>Example:</b>
<code>&lt;b&gt;{manga_title}&lt;/b&gt;\nChapter {chapter_num}</code>
</blockquote>

<i>Send your new caption pattern:</i>"""
        )
        
        try:
            response = await _.listen(user_id=int(user_id), timeout=60)
            new_caption = response.text
            
            uts[user_id]['setting']["caption"] = new_caption
            sync(Vars.DB_NAME, "uts")
            
            await response.delete()
            await query.answer("✅ Caption pattern updated")
            
            # Update display
            await main_user_panel(_, query)
        except asyncio.TimeoutError:
            await query.answer("⌛ Timed out waiting for response")
    
    elif query.data == "ucp_delete":
        # Reset caption pattern
        if "caption" in uts[user_id]['setting']:
            del uts[user_id]['setting']["caption"]
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ Caption pattern reset to default")
        else:
            await query.answer("ℹ️ No custom caption pattern set")
        
        # Update display
        await main_user_panel(_, query)

# ========================
# THUMBNAIL SETTINGS
# ========================

@Bot.on_callback_query(filters.regex("^uth"))
async def thumb_handler(_, query):
    """Handle thumbnail settings"""
    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    settings = uts[user_id].get('setting', {})
    
    # Prepare buttons
    buttons = [
        [
            InlineKeyboardButton("🖼 Custom", callback_data="uth_change"),
            InlineKeyboardButton("📚 Manga Poster", callback_data="uth_constant")
        ],
        [
            InlineKeyboardButton("🗑️ Delete", callback_data="uth_delete"),
            InlineKeyboardButton("🔙 Back", callback_data="mus"),
        ]
    ]
    
    if query.data == "uth":
        # Show current settings
        thumb_status = settings.get("thumb")
        info_text = ""
        
        if thumb_status:
            if thumb_status == "constant":
                info_text = "<blockquote>Currently using manga posters as thumbnails</blockquote>"
            elif thumb_status.startswith("http"):
                info_text = "<blockquote>Custom thumbnail URL set</blockquote>"
            else:
                info_text = "<blockquote>Custom thumbnail image set</blockquote>"
        
        await retry_on_flood(
            query.edit_message_caption,
            f"""<b>🖼 Thumbnail Settings</b>

{info_text}
<i>Select an option below:</i>""",
            reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data == "uth_constant":
        # Set to use manga posters
        uts[user_id]['setting']["thumb"] = "constant"
        sync(Vars.DB_NAME, "uts")
        
        await query.answer("✅ Will use manga posters as thumbnails")
        await main_user_panel(_, query)
    
    elif query.data == "uth_change":
        # Set custom thumbnail
        await retry_on_flood(
            query.edit_message_caption,
            """<b>🖼 Set Custom Thumbnail</b>

<blockquote>
You can send:
• A photo (as document or image)
• A direct URL to an image
</blockquote>

<i>Send your new thumbnail:</i>"""
        )
        
        try:
            response = await _.listen(user_id=int(user_id), timeout=60)
            
            if response.photo:
                thumb = response.photo.file_id
            elif response.document and response.document.mime_type.startswith('image/'):
                thumb = response.document.file_id
            elif response.text and response.text.startswith(('http://', 'https://')):
                thumb = response.text
            else:
                await query.answer("❌ Invalid thumbnail format", show_alert=True)
                return
            
            uts[user_id]['setting']["thumb"] = thumb
            sync(Vars.DB_NAME, "uts")
            
            await response.delete()
            await query.answer("✅ Thumbnail updated")
            
            # Update display
            await main_user_panel(_, query)
        except asyncio.TimeoutError:
            await query.answer("⌛ Timed out waiting for response")
    
    elif query.data == "uth_delete":
        # Reset thumbnail
        if "thumb" in uts[user_id]['setting']:
            del uts[user_id]['setting']["thumb"]
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ Thumbnail reset to default")
        else:
            await query.answer("ℹ️ No custom thumbnail set")
        
        # Update display
        await main_user_panel(_, query)

# ========================
# BANNER SETTINGS
# ========================

@Bot.on_callback_query(filters.regex("^ubn"))
async def banner_handler(_, query):
    """Handle banner settings"""
    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    settings = uts[user_id].get('setting', {})
    
    # Prepare buttons
    buttons = [
        [
            InlineKeyboardButton("🖼 Banner 1", callback_data="ubn_set1"),
            InlineKeyboardButton("🗑️ Delete 1", callback_data="ubn_delete1")
        ],
        [
            InlineKeyboardButton("🖼 Banner 2", callback_data="ubn_set2"),
            InlineKeyboardButton("🗑️ Delete 2", callback_data="ubn_delete2")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="mus")
        ]
    ]

    if query.data == "ubn":
        # Show current settings
        await retry_on_flood(
            query.edit_message_reply_markup,
            reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data.startswith("ubn_set"):
        # Set banner image
        banner_num = query.data[-1]
        
        await retry_on_flood(
            query.edit_message_caption,
            f"""<b>🖼 Set Banner {banner_num}</b>

<blockquote>
You can send:
• A photo (as document or image)
• A direct URL to an image
</blockquote>

<i>Send your new banner:</i>"""
        )
        
        try:
            response = await _.listen(user_id=int(user_id), timeout=60)
            
            if response.photo:
                banner = response.photo.file_id
            elif response.document and response.document.mime_type.startswith('image/'):
                banner = response.document.file_id
            elif response.text and response.text.startswith(('http://', 'https://')):
                banner = response.text
            else:
                await query.answer("❌ Invalid banner format", show_alert=True)
                return
            
            uts[user_id]['setting'][f"banner{banner_num}"] = banner
            sync(Vars.DB_NAME, "uts")
            
            await response.delete()
            await query.answer(f"✅ Banner {banner_num} updated")
            
            # Update display
            await main_user_panel(_, query)
        except asyncio.TimeoutError:
            await query.answer("⌛ Timed out waiting for response")
    
    elif query.data.startswith("ubn_delete"):
        # Delete banner
        banner_num = query.data[-1]
        banner_key = f"banner{banner_num}"
        
        if banner_key in uts[user_id]['setting']:
            del uts[user_id]['setting'][banner_key]
            sync(Vars.DB_NAME, "uts")
            await query.answer(f"✅ Banner {banner_num} removed")
        else:
            await query.answer(f"ℹ️ Banner {banner_num} not set")
        
        # Update display
        await main_user_panel(_, query)

# ========================
# DUMP CHANNEL SETTINGS
# ========================

@Bot.on_callback_query(filters.regex("^udc"))
async def dump_handler(_, query):
    """Handle dump channel settings"""
    if Vars.CONSTANT_DUMP_CHANNEL:
        return await query.answer("❌ Dump channel is fixed by admin", show_alert=True)

    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    settings = uts[user_id].get('setting', {})
    
    # Prepare buttons
    buttons = [
        [
            InlineKeyboardButton("✏️ Set/Change", callback_data="udc_change"),
            InlineKeyboardButton("🗑️ Delete", callback_data="udc_delete")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="mus")
        ]
    ]

    if query.data == "udc":
        # Show current settings
        await retry_on_flood(
            query.edit_message_reply_markup,
            reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data == "udc_change":
        # Change dump channel
        await retry_on_flood(
            query.edit_message_caption,
            """<b>📡 Set Dump Channel</b>

<blockquote>
You can send:
• Channel username (without @)
• Channel ID
• Forward a message from the channel
</blockquote>

<i>Send your dump channel:</i>"""
        )
        
        try:
            response = await _.listen(user_id=int(user_id), timeout=60)
            
            if response.text:
                dump = response.text
            elif response.forward_from_chat:
                dump = response.forward_from_chat.id
            else:
                await query.answer("❌ Invalid channel format", show_alert=True)
                return
            
            uts[user_id]['setting']["dump"] = dump
            sync(Vars.DB_NAME, "uts")
            
            await response.delete()
            await query.answer("✅ Dump channel updated")
            
            # Update display
            await main_user_panel(_, query)
        except asyncio.TimeoutError:
            await query.answer("⌛ Timed out waiting for response")
    
    elif query.data == "udc_delete":
        # Reset dump channel
        if "dump" in uts[user_id]['setting']:
            del uts[user_id]['setting']["dump"]
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ Dump channel removed")
        else:
            await query.answer("ℹ️ No dump channel set")
        
        # Update display
        await main_user_panel(_, query)

# ========================
# FILE TYPE SETTINGS
# ========================

@Bot.on_callback_query(filters.regex("^u_file_type"))
async def type_handler(_, query):
    """Handle file type settings"""
    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    # Ensure type list exists
    if "type" not in uts[user_id]['setting']:
        uts[user_id]['setting']["type"] = []
        sync(Vars.DB_NAME, "uts")

    current_types = uts[user_id]['setting'].get("type", [])
    
    # Prepare buttons
    buttons = [[]]
    
    # PDF button
    if "PDF" in current_types:
        buttons[0].append(InlineKeyboardButton("✅ PDF", callback_data="u_file_type_pdf"))
    else:
        buttons[0].append(InlineKeyboardButton("❌ PDF", callback_data="u_file_type_pdf"))
    
    # CBZ button
    if "CBZ" in current_types:
        buttons[0].append(InlineKeyboardButton("✅ CBZ", callback_data="u_file_type_cbz"))
    else:
        buttons[0].append(InlineKeyboardButton("❌ CBZ", callback_data="u_file_type_cbz"))
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="mus")])

    if query.data == "u_file_type":
        # Show current settings
        await retry_on_flood(
            query.edit_message_reply_markup,
            reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data.endswith("_pdf"):
        # Toggle PDF
        if "PDF" in current_types:
            uts[user_id]['setting']["type"].remove("PDF")
            sync(Vars.DB_NAME, "uts")
            await query.answer("❌ PDF disabled")
        else:
            uts[user_id]['setting']["type"].append("PDF")
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ PDF enabled")
        
        # Update display
        await main_user_panel(_, query)
    
    elif query.data.endswith("_cbz"):
        # Toggle CBZ
        if "CBZ" in current_types:
            uts[user_id]['setting']["type"].remove("CBZ")
            sync(Vars.DB_NAME, "uts")
            await query.answer("❌ CBZ disabled")
        else:
            uts[user_id]['setting']["type"].append("CBZ")
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ CBZ enabled")
        
        # Update display
        await main_user_panel(_, query)

# ========================
# MERGE SIZE SETTINGS
# ========================

@Bot.on_callback_query(filters.regex("^umegre"))
async def megre_handler(_, query):
    """Handle merge size settings"""
    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    settings = uts[user_id].get('setting', {})
    
    # Prepare buttons
    buttons = [
        [
            InlineKeyboardButton("✏️ Set/Change", callback_data="umegre_change"),
            InlineKeyboardButton("🗑️ Delete", callback_data="umegre_delete")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="mus")
        ]
    ]

    if query.data == "umegre":
        # Show current settings
        await retry_on_flood(
            query.edit_message_reply_markup,
            reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data == "umegre_change":
        # Change merge size
        await retry_on_flood(
            query.edit_message_caption,
            """<b>🔢 Set Merge Size</b>

<blockquote>
Number of chapters to merge into one file
(Recommended: between 2-10)

<b>Example:</b> <code>5</code> (will merge 5 chapters per file)
</blockquote>

<i>Send the new merge size:</i>"""
        )
        
        try:
            response = await _.listen(user_id=int(user_id), timeout=60)
            try:
                size = int(response.text)
                if size <= 0:
                    raise ValueError
                
                uts[user_id]['setting']["megre"] = size
                sync(Vars.DB_NAME, "uts")
                
                await response.delete()
                await query.answer(f"✅ Merge size set to {size}")
            except ValueError:
                await query.answer("❌ Please enter a positive number", show_alert=True)
            
            # Update display
            await main_user_panel(_, query)
        except asyncio.TimeoutError:
            await query.answer("⌛ Timed out waiting for response")
    
    elif query.data == "umegre_delete":
        # Reset merge size
        if "megre" in uts[user_id]['setting']:
            del uts[user_id]['setting']["megre"]
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ Merge size reset")
        else:
            await query.answer("ℹ️ No merge size set")
        
        # Update display
        await main_user_panel(_, query)

# ========================
# PASSWORD SETTINGS
# ========================

@Bot.on_callback_query(filters.regex("^upass"))
async def password_handler(_, query):
    """Handle PDF password settings"""
    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    settings = uts[user_id].get('setting', {})
    
    # Prepare buttons
    buttons = [
        [
            InlineKeyboardButton("✏️ Set/Change", callback_data="upass_change"),
            InlineKeyboardButton("🗑️ Delete", callback_data="upass_delete")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="mus")
        ]
    ]

    if query.data == "upass":
        # Show current settings
        await retry_on_flood(
            query.edit_message_reply_markup,
            reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data == "upass_change":
        # Change password
        await retry_on_flood(
            query.edit_message_caption,
            """<b>🔐 Set PDF Password</b>

<blockquote>
Password to protect generated PDF files
(Leave empty to disable password protection)

<b>Note:</b> Passwords cannot contain spaces
</blockquote>

<i>Send the new password:</i>"""
        )
        
        try:
            response = await _.listen(user_id=int(user_id), timeout=60)
            password = response.text.strip()
            
            if " " in password:
                await query.answer("❌ Password cannot contain spaces", show_alert=True)
            else:
                uts[user_id]['setting']["password"] = password or None
                sync(Vars.DB_NAME, "uts")
                
                await response.delete()
                if password:
                    await query.answer("✅ Password set")
                else:
                    await query.answer("✅ Password removed")
            
            # Update display
            await main_user_panel(_, query)
        except asyncio.TimeoutError:
            await query.answer("⌛ Timed out waiting for response")
    
    elif query.data == "upass_delete":
        # Reset password
        if "password" in uts[user_id]['setting']:
            del uts[user_id]['setting']["password"]
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ Password removed")
        else:
            await query.answer("ℹ️ No password set")
        
        # Update display
        await main_user_panel(_, query)

# ========================
# REGEX SETTINGS
# ========================

@Bot.on_callback_query(filters.regex("^uregex"))
async def regex_handler(_, query):
    """Handle regex settings"""
    user_id = str(query.from_user.id)
    
    # Initialize user settings if not exists
    if user_id not in uts:
        uts[user_id] = {'setting': {}}
        sync(Vars.DB_NAME, "uts")

    settings = uts[user_id].get('setting', {})
    
    # Prepare buttons
    buttons = [
        [InlineKeyboardButton(f"{'✅' if settings.get('regex') == str(i) else '❌'} {i}", 
         callback_data=f"uregex_set_{i}") for i in range(1, 5)],
        [
            InlineKeyboardButton("🗑️ Delete", callback_data="uregex_delete"),
            InlineKeyboardButton("🔙 Back", callback_data="mus")
        ]
    ]

    if query.data == "uregex":
        # Show current settings
        await retry_on_flood(
            query.edit_message_reply_markup,
            reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data.startswith("uregex_set"):
        # Set regex pattern
        pattern_num = query.data.split("_")[-1]
        uts[user_id]['setting']["regex"] = pattern_num
        sync(Vars.DB_NAME, "uts")
        
        await query.answer(f"✅ Regex pattern {pattern_num} selected")
        await main_user_panel(_, query)
    
    elif query.data == "uregex_delete":
        # Reset regex
        if "regex" in uts[user_id]['setting']:
            del uts[user_id]['setting']["regex"]
            sync(Vars.DB_NAME, "uts")
            await query.answer("✅ Regex pattern removed")
        else:
            await query.answer("ℹ️ No regex pattern set")
        
        # Update display
        await main_user_panel(_, query)

# ========================
# FALLBACK HANDLER
# ========================

@Bot.on_callback_query()
async def extra_handler(client, query):
    """Handle unknown callback queries"""
    try:
        await query.answer(
            "⌛ This button has expired, please try your search again",
            show_alert=True)
    except Exception:
        pass
