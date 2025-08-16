from pyrogram.errors import FloodWait
from .storage import *
from bot import Bot, Vars, logger

from Tools.img2pdf import download_and_convert_images, convert_images_to_pdf, thumbnali_images, download_through_cloudscrapper
from Tools.img2cbz import images_to_cbz

import os
import shutil

from time import time
from pyrogram.types import InputMediaDocument

from Tools.db import uts, sync

def clean(txt, length=-1):
  txt = txt.replace("_", "").replace("&", "").replace(";", "")
  txt = txt.replace("None", "").replace(":", "").replace("'", "")
  txt = txt.replace("|", "").replace("*", "").replace("?", "")
  txt = txt.replace(">", "").replace("<", "").replace("`", "")
  txt = txt.replace("!", "").replace("@", "").replace("#", "")
  txt = txt.replace("$", "").replace("%", "").replace("^", "")
  txt = txt.replace("~", "").replace("+", "").replace("=", "")
  txt = txt.replace("/", "").replace("\\", "").replace("\n", "")
  txt = txt.replace(".jpg", "")
  if length != -1:
    txt = txt[:length]
  return txt


async def send_manga_chapter(data, picturesList, user, sts, worker_id, webs, user_id=None):
    start_time = time()
    error_msg = None
    main_dir = None
    download_dir = None
    compressed_dir = None
    pdf_output_path = None
    cbz_output_path = None
    password = None
    media_docs = []
    
    if user:
        user_id = user.from_user.id
        chat_id = user.message.chat.id
    else:
        chat_id = user_id
        user_id = user_id

    if not str(user_id) in uts:
        uts[str(user_id)] = {}
        sync(Vars.DB_NAME, 'uts')

    try:
        regex = uts[str(user_id)].get('setting', {}).get('regex', None)
        picturesList = picturesList if picturesList else data['pictures_list']

        flen = int(
            uts[str(user_id)].get('setting', {}).get('file_name_len', 30)
        if isinstance(data, list):
            episode_number1 = str(get_episode_number(data[0]['title']))
            if (episode_number1 == "None") or not episode_number1:
                episode_number1 = clean(data[0]['title'])
            else:
                episode_number1 = episode_number1.zfill(int(regex)) if regex else episode_number1

            episode_number2 = str(get_episode_number(data[-1]['title']))
            if (episode_number2 == "None") or not episode_number2:
                episode_number2 = clean(data[-1]['title'])
            else:
                episode_number2 = episode_number2.zfill(int(regex)) if regex else episode_number2

            episode_number = f"{episode_number1}-{episode_number2}"
            manga_title = clean(data[0]['manga_title'], flen)

        else:
            episode_number = str(get_episode_number(data['title']))
            if (episode_number == "None") or not episode_number:
                episode_number = clean(data['title'])
            else:
                episode_number = episode_number.zfill(int(regex)) if regex else episode_number
            
            manga_title = clean(data['manga_title'], flen)

        file_name = uts[str(user_id)].get('setting', {}).get('file_name', "Chapter {episode_number} {manga_title}")
        caption = uts[str(user_id)].get('setting', {}).get('caption', "<blockquote>{file_name}</blockquote>")

        file_name = file_name.replace("{episode_number}", episode_number).replace("{manga_title}", manga_title).replace("{chapter_num}", episode_number) if file_name else f'{episode_number} - {manga_title}'
        
        caption = caption.replace("{file_name}", file_name).replace("{episode_number}", episode_number).replace("{manga_title}", manga_title).replace("{chapter_num}", episode_number) if caption else file_name

        main_dir = f"Process/{user_id}" if isinstance(user_id, int) else f"Process/Updates"
        download_dir = f"{main_dir}/pictures/{manga_title}/{episode_number}"
        if os.path.exists(download_dir):
            download_dir += f"_{os.urandom(4).hex()}"
            if os.path.exists(download_dir):
                download_dir += f"_{os.urandom(4).hex()}"
                if os.path.exists(download_dir):
                    download_dir += f"_{os.urandom(4).hex()}"

        compressed_dir = f"{main_dir}/compress/{episode_number}"

        banner1 = uts[str(user_id)].get('setting', {}).get("banner1", None)
        banner2 = uts[str(user_id)].get('setting', {}).get("banner2", None)

        if banner1:
            if banner1.startswith("http"):
                if webs.bg:
                    picturesList[0] = banner1
                else:
                    picturesList.insert(0, banner1)

        if banner2:
            if banner2.startswith("http"):
                picturesList.append(banner2)

        if webs.url == "https://weebcentral.com/" or webs.sf == "fc":
            downloads_list = await download_through_cloudscrapper(picturesList, download_dir)
        else:
            downloads_list = await asyncio.get_running_loop().run_in_executor(None, download_and_convert_images, picturesList, download_dir)

        try: await sts.edit("<code>Downloading.....</code>")
        except: pass

        if banner1:
            if not banner1.startswith("http"):
                try:
                    banner1 = await Bot.download_media(banner1)
                except pyrogram.errors.exceptions.bad_request_400.FileReferenceExpired:
                    try:
                        msg = await Bot.get_messages(banner1.chat.id, banner1.message_id)
                        banner1 = await Bot.download_media(msg)
                    except Exception as e:
                        await retry_on_flood(sts.edit)("<code>Error at Banner1</code>")
                        await asyncio.sleep(10)
                        banner1 = None
                
                if banner1:
                    if webs.bg:
                        os.remove(downloads_list[0])
                        downloads_list[0] = banner1
                    else:
                        downloads_list.insert(0, banner1)

        if banner2:
            if not banner2.startswith("http"):
                try:
                    banner2 = await Bot.download_media(banner2)
                except pyrogram.errors.exceptions.bad_request_400.FileReferenceExpired:
                    try:
                        msg = await Bot.get_messages(banner2.chat.id, banner2.message_id)
                        banner2 = await Bot.download_media(msg)
                    except:
                        await retry_on_flood(sts.edit)("<code>Error at Banner2. Change Banner</code>")
                        await asyncio.sleep(10)
                        banner2 = None
                
                if banner2:
                    downloads_list.append(banner2)

        thumb = uts[str(user_id)].get('setting', {}).get('thumb', None)
        if thumb:
            if thumb.startswith("http"):
                thumb = await asyncio.get_running_loop().run_in_executor(None, thumbnali_images, thumb, download_dir)
            elif thumb == "constant":
                thumb = data['poster'] if 'poster' in data else None
                try:
                    thumb = await asyncio.get_running_loop().run_in_executor(None, thumbnali_images, thumb, download_dir) if thumb else None
                except:
                    thumb = None
            else:
                try: 
                    thumb = await Bot.download_media(thumb)
                except pyrogram.errors.exceptions.bad_request_400.FileReferenceExpired:
                    try:
                        msg = await Bot.get_messages(thumb.chat.id, thumb.message_id)
                        thumb = await Bot.download_media(msg)
                    except:
                        thumb = None
                except:
                    thumb = None
        else:
            thumb = None

        file_type = uts[str(user_id)].get('setting', {}).get('type', ['PDF', 'CBZ'])

        if "PDF" in file_type:
            pdf_output_path = f"{main_dir}/{file_name}.pdf"
            password = uts[str(user_id)].get('setting', {}).get('password', None)

            test = await asyncio.get_running_loop().run_in_executor(None, convert_images_to_pdf, downloads_list, pdf_output_path, compressed_dir, password)
            if test:
                await retry_on_flood(Bot.send_message)(user_id, f"Error at Making Pdf:- {data['url']}: <code>{test}</code>")
            else:
                media_docs.append(
                    InputMediaDocument(pdf_output_path, caption=caption, thumb=thumb)
                )

        if "CBZ" in file_type:
            cbz_output_path = f"{main_dir}/{file_name}.cbz"
            test = await asyncio.get_running_loop().run_in_executor(None, images_to_cbz, downloads_list, cbz_output_path)
            if test:
                await retry_on_flood(Bot.send_message)(
                    user_id, f"Error at Making Cbz:- {data['url']}: <code>{test}</code>")
            else:
                media_docs.append(
                    InputMediaDocument(cbz_output_path, caption=caption, thumb=thumb)
                )

        if len(media_docs) > 0:
            doc = await retry_on_flood(Bot.send_media_group)(int(chat_id), media_docs)
            dump = uts[str(user_id)].get('setting', {}).get('dump', None)
            if Vars.CONSTANT_DUMP_CHANNEL:
                try: 
                    await retry_on_flood(Bot.send_media_group)(CONSTANT_DUMP_CHANNEL, media_docs)
                except:
                    try: await sts.edit("<code>Add Bot At Dump Channel OR Provide Vaild Dump Channel</code>")
                    except: pass
                    await asyncio.sleep(10)

            elif dump:
                try: 
                    await retry_on_flood(Bot.send_media_group)(int(dump), media_docs)
                except:
                    try: await sts.edit("<code>Add Bot At Dump Channel OR Provide Vaild Dump Channel</code>")
                    except: pass
                    await asyncio.sleep(10)

            if Vars.LOG_CHANNEL:
                if isinstance(data, list):
                    logs_msg = f"{caption}\n{data[0]['url']} : {data[-1]['url']}\n<code>User Id</code>: <code>{user_id}</code>[{user.from_user.mention() if user else 'None'}]\n<code>Time Taken: {time() - start_time}</code>\n<code>Worker: {worker_id}</code>"
                else:
                    logs_msg = f"{caption}\n{data['url']}\n<code>User Id</code>: <code>{user_id}</code>[{user.from_user.mention() if user else 'None'}]\n<code>Time Taken: {time() - start_time}</code>\n<code>Worker: {worker_id}</code>"
                if password:
                    logs_msg += f"\nPassword: <code>{password}</code>"
                media_docs[-1].caption = logs_msg[:1024]
                try: await retry_on_flood(Bot.send_media_group)(Vars.LOG_CHANNEL, media_docs)
                except: pass

    except Exception as e:
        error_msg = True
        if e == "Tasks cancelled":
            pass
        else:
            try:
                await Bot.send_message(chat_id, f"Error processing task {data['url']}: {e}")
            except FloodWait as err:
                await asyncio.sleep(err.value)
                await Bot.send_message(chat_id, f"Error processing task {data['url']}: {e}")
            except:
                await retry_on_flood(Bot.send_message)(Vars.LOG_CHANNEL, f"Error processing task {data['url']}: {e}")
            
            logger.exception(f"Error processing task {data['url']}: {e}")

    finally:
        if pdf_output_path and os.path.exists(pdf_output_path):
            os.remove(pdf_output_path)

        if cbz_output_path and os.path.exists(cbz_output_path):
            os.remove(cbz_output_path)

        if download_dir and os.path.exists(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)

        if compressed_dir and os.path.exists(compressed_dir):
            shutil.rmtree(compressed_dir, ignore_errors=True)

        if main_dir and os.path.exists(main_dir):
            shutil.rmtree(main_dir, ignore_errors=True)

        try: await sts.delete()
        except: pass
        
        if error_msg:
            return True


async def worker(worker_id: int = 1):
  while True:
    datas, user_id, task_id = await queue.get(worker_id)
    try:
      data, picturesList, user, sts, webs = datas
      if isinstance(data, list):
        logger.debug(f"Worker {worker_id} processing task {data[0]['url']} - {data[-1]['url']}")
      else:
        logger.debug(f"Worker {worker_id} processing task {data['url']}")

      try: await sts.edit("<code>Processing...</code>")
      except: pass

      await send_manga_chapter(data, picturesList, user, sts, worker_id, webs=webs)

    except Exception as err:
      logger.exception(f"Worker {worker_id} encountered an error: {err}")
    finally:
      if user_id:
        queue.release(user_id)

      logger.debug(f"Worker {worker_id} released task ")

      queue.task_done(task_id)
