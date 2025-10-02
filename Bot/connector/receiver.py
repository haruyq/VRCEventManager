import asyncio
import json
from contextlib import suppress
from typing import Optional
from discord.ext import commands

from connector.handler import RequestHandler
from connector.responses import Responses
from utils.logger import Logger

Log = Logger(__name__)

class Receiver:
	def __init__(self, ip: str, port: int, bot: commands.Bot):
		self.ip = ip
		self.port = port
		self.server: Optional[asyncio.AbstractServer] = None
		self._serve_task: Optional[asyncio.Task] = None
		self.handler = RequestHandler(bot)

	async def start(self):
		if self.server is not None:
			return
		self.server = await asyncio.start_server(self._handle_client, self.ip, self.port)
		Log.info(f"receiver listening on {self.ip}:{self.port}")
		self._serve_task = asyncio.create_task(self.server.serve_forever())

	async def stop(self):
		if self.server is None:
			return
		self.server.close()
		await self.server.wait_closed()
		self.server = None
		if self._serve_task:
			self._serve_task.cancel()
			with suppress(asyncio.CancelledError):
				await self._serve_task
			self._serve_task = None
		Log.info("receiver stopped")

	async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
		address = writer.get_extra_info("peername")
		Log.info(f"receiver: {address}")
		while True:
			data = await reader.read(4096)
			if not data:
				response = Responses.error("No data received")
				payload = json.dumps(response).encode("utf-8")
				writer.write(payload)
				await writer.drain()
				Log.debug(f"sent -> response: {response}")

			try:
				message = data.decode()
				Log.debug(f"received -> message: {message}")
				if not message or message is None:
					response = Responses.error("Empty message received")
				else:
					response = await self.handler.handle(message)
     
			except Exception as exc:
				Log.error(f"error handling message: {exc}")
				response = Responses.error(f"Error: {exc}")
			
			if response is None:
				Log.warning("handler returned no response")
				response = Responses.error("No response from handler")

			payload = json.dumps(response).encode("utf-8")
			writer.write(payload)
			await writer.drain()
			Log.debug(f"sent -> response: {response}")