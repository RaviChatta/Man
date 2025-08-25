from TG.wks import Bot, worker, asyncio, Vars
from TG.auto import main_updates
import os, shutil, time


folder_path = "Process"
if os.path.exists(folder_path) and os.path.isdir(folder_path):
    shutil.rmtree(folder_path)


async def restart_timer():
    """Restart every 12 hours"""
    await asyncio.sleep(43200)  # 12 hours
    try:
        await Bot.stop()
    except Exception as e:
        print(f"⚠️ Restart timer stop failed: {e}")


async def runner():
    # spawn workers
    for i in range(15):
        asyncio.create_task(worker(i))
    # main updates
    asyncio.create_task(main_updates())
    # restart timer
    asyncio.create_task(restart_timer())


if __name__ == "__main__":
    while True:
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(runner())
            Bot.run()
        except Exception as e:
            print(f"❌ Bot crashed: {e}; restarting in 10s…")
            time.sleep(10)
