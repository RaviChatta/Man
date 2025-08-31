from TG.wks import Bot, worker, asyncio, Vars, logger
from TG.auto import main_updates
import os
import shutil
import time

class BotManager:
    def __init__(self):
        self.is_running = True
        self.restart_count = 0
        self.max_restarts = 10

    async def cleanup(self):
        """Cleanup resources"""
        folder_path = "Process"
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            try:
                shutil.rmtree(folder_path)
                logger.info("Cleaned up Process folder")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def start_background_tasks(self):
        """Start all background tasks"""
        # Start workers
        for i in range(15):
            asyncio.create_task(worker(i))
        
        # Start update checker
        asyncio.create_task(main_updates())
        
        logger.info("Background tasks started: 15 workers + update checker")

    def run_bot(self):
        """Run the Pyrogram bot (blocking call)"""
        try:
            Bot.run()
            return True
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            return False
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            return False

    async def monitor_bot(self):
        """Monitor and restart bot if needed"""
        while self.is_running and self.restart_count < self.max_restarts:
            # Start background tasks
            await self.cleanup()
            await self.start_background_tasks()
            
            # Run bot in a thread (since Bot.run() is blocking)
            import threading
            bot_thread = threading.Thread(target=self.run_bot)
            bot_thread.daemon = True
            bot_thread.start()
            
            # Wait for bot thread to finish or crash
            while bot_thread.is_alive() and self.is_running:
                await asyncio.sleep(1)
            
            if not self.is_running:
                break
                
            self.restart_count += 1
            if self.restart_count < self.max_restarts:
                wait_time = min(2 ** self.restart_count, 60)  # Exponential backoff, max 60s
                logger.warning(f"Bot crashed, restarting in {wait_time}s... (Attempt {self.restart_count}/{self.max_restarts})")
                await asyncio.sleep(wait_time)
            else:
                logger.error("Max restarts reached. Bot will not restart.")

    async def run(self):
        """Main execution"""
        try:
            await self.monitor_bot()
        except Exception as e:
            logger.critical(f"Fatal error: {e}")
        finally:
            logger.info("Bot manager stopped")

async def main():
    """Async main function"""
    manager = BotManager()
    await manager.run()

if __name__ == "__main__":
    # Simple version - use this one first
    try:
        # Cleanup
        folder_path = "Process"
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
        
        # Start background tasks
        loop = asyncio.get_event_loop()
        for i in range(15):
            loop.create_task(worker(i))
        loop.create_task(main_updates())
        
        logger.info("Background tasks started")
        
        # Start the bot (this will handle commands)
        Bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
