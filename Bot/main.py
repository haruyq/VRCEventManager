import discord
from discord.ext import commands

import os

from utils.logger import Logger
from utils.loader import Loader
from connector.receiver import Receiver

Log = Logger(__name__)

class VRCEvMngrBot(commands.Bot):
	def __init__(self):
		super().__init__(command_prefix="!", help_command=None, intents=discord.Intents.default())
		address = os.environ.get("RECEIVER_ADDRESS")
		port = os.environ.get("RECEIVER_PORT")
		self.receiver = Receiver(ip=address, port=int(port), bot=self)

	async def setup_hook(self):
		try:
			await self.receiver.start()
		except OSError as exc:
			Log.error(f"failed to start receiver: {exc}")
		else:
			Log.info("receiver startup complete")

		await Loader(self).load()

	async def close(self):
		if self.receiver is not None:
			await self.receiver.stop()
		await super().close()

if __name__ == "__main__":
	bot = VRCEvMngrBot()
	bot.run(os.environ.get("BOT_TOKEN"))