from TG.wks import Bot, worker, asyncio, Vars
from TG.auto import main_updates

import os, shutil

folder_path = "Process"
if os.path.exists(folder_path) and os.path.isdir(folder_path):
  shutil.rmtree(folder_path)
  
if __name__ == "__main__":
  loop = asyncio.get_event_loop()
  for i in range(15):
    loop.create_task(worker(i))
  for i in range(1):
    loop.create_task(main_updates())
  
  Bot.run()
