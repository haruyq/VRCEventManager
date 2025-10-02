import logging
import aiofiles.os
from discord.ext import commands
from .logger import Logger

Log: logging.Logger = Logger(__name__)

class Loader:
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    async def load(self):
        for filename in await aiofiles.os.listdir('./commands'):
            if filename.endswith('.py'):
                ext = f"commands.{filename[:-3]}"
                try:
                    await self.bot.load_extension(ext)
                    Log.info(f"[{ext}] コマンドロード成功")
                except Exception as e:
                    Log.error(f"[{ext}] コマンドロード失敗: {e}")

        for filename in await aiofiles.os.listdir('./events'):
            if filename.endswith('.py'):
                ext = f"events.{filename[:-3]}"
                try:
                    await self.bot.load_extension(ext)
                    Log.info(f"[{ext}] イベントロード成功")
                except Exception as e:
                    Log.error(f"[{ext}] イベントロード失敗: {e}")