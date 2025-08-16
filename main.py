import os
import shutil
import asyncio
from TG.wks import Bot, worker, Vars
from TG.auto import main_updates

# Clean old processing folder
folder_path = "Process"
if os.path.exists(folder_path) and os.path.isdir(folder_path):
    shutil.rmtree(folder_path)

async def main():
    # Start workers
    for i in range(15):
        asyncio.create_task(worker(i))

    # Start manga updates polling
    asyncio.create_task(main_updates())

    # Run the bot
    await Bot.start()
    print(f"{Vars.BOT_NAME} is running...")
    await Bot.idle()  # Keep the bot alive until interrupted

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped manually.")
