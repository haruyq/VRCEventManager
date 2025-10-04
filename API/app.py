import os
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from payloads import *

from connector.sender import Sender
from utils.logger import Logger

class VRCEvMngrAPI(FastAPI):
	def __init__(self):
		self.log = Logger(__name__)
		self.sender = Sender(
			ip=os.environ.get("BOT_SOCK_ADDRESS"),
			port=int(os.environ.get("BOT_SOCK_PORT"))
			)
		super().__init__(
			title="VRChatEventManager-API"
		)

		@self.on_event("startup")
		async def startup_event():
			try:
				await self.sender.connect_async()
    
			except OSError as e:
				self.log.warning(f"initial connection to bot failed: {e}")

		@self.post("/api/dsc/create_announcement")
		async def send_announcement(payload: AnnouncementPayload):
			try:
				message_payload = json.dumps({
					"action": "send_announcement",
					"channel_id": payload.channel_id,
					"message": payload.message
				})
				response = await self.sender.send_async(message_payload)
    
			except OSError as e:
				self.log.error(f"failed to send announcement: {e}")
				raise HTTPException(status_code=503, detail="Bot connection unavailable") from e

			return JSONResponse(content=response)

		@self.post("/api/dsc/create_event")
		async def create_event(payload: CreateEventPayload):
			try:
				message_payload = json.dumps({
					"action": "create_event",
					"guild_id": payload.guild_id,
					"channel_id": payload.channel_id,
					"name": payload.name,
					"description": payload.description,
					"start_time": payload.start_time,
					"end_time": payload.end_time,
					"entity_type": payload.entity_type,
					"location": payload.location,
					"image_uri": payload.image_uri
				})
				response = await self.sender.send_async(message_payload)

			except HTTPException:
				raise
			except OSError as e:
				self.log.error(f"failed to create event: {e}")
				raise HTTPException(status_code=503, detail="Bot connection unavailable") from e
			except Exception as exc:
				self.log.error(f"unexpected error creating event: {exc}")
				raise HTTPException(status_code=500, detail="Failed to create event") from exc

			return JSONResponse(content=response)

		@self.post("/api/dsc/check_admin")
		async def check_admin(payload: CheckAdminPayload):
			try:
				message_payload = json.dumps({
					"action": "check_admin",
					"guild_id": payload.guild_id,
					"user_id": payload.user_id
				})
				response = await self.sender.send_async(message_payload)
	
			except OSError as e:
				self.log.error(f"failed to check admin: {e}")
				raise HTTPException(status_code=503, detail="Bot connection unavailable") from e

			return JSONResponse(content=response)