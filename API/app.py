import os
import json
import aiohttp

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from payloads import *

from connector.sender import Sender
from utils.logger import Logger
from utils.database import UsersDB
from utils.auth import AuthUtil

Log = Logger(__name__)
DISCORD_API_BASE = "https://discord.com/api/v10"

class VRCEvMngrAPI(FastAPI):
	def __init__(self):
		self.sender = Sender(
			ip=os.environ.get("BOT_SOCK_ADDRESS"),
			port=int(os.environ.get("BOT_SOCK_PORT"))
			)
		super().__init__(
			title="VRChatEventManager-API"
		)

		@self.on_event("startup")
		async def startup_event():
			await UsersDB.init_db()
			if not os.path.isfile("/Secrets/key.pem"):
				AuthUtil.generate_key()
			try:
				await self.sender.connect_async()
			except OSError as e:
				Log.warning(f"initial connection to bot failed: {e}")

		@self.get("/api/login/callback")
		async def callback(code: str):
			if not code:
				raise HTTPException(status_code=400, detail="Missing Arguments")

			async with aiohttp.ClientSession() as session:
				headers = { "Content-Type": "application/x-www-form-urlencoded" }
				data = {
					"client_id": os.environ.get("CLIENT_ID"),
					"client_secret": os.environ.get("CLIENT_SECRET"),
					"grant_type": "authorization_code",
					"code": code,
					"redirect_uri": os.environ.get("REDIRECT_URI")
				}
				async with session.post(f"{DISCORD_API_BASE}/oauth2/token", headers=headers, data=data) as resp:
					if resp.status != 200:
						raise HTTPException(status_code=503, detail="Failed to fetch token from Discord")
					token_data = await resp.json()

				headers = { "Authorization": f"Bearer {token_data['access_token']}" }
				async with aiohttp.ClientSession() as session:
					async with session.get(f"{DISCORD_API_BASE}/users/@me", headers=headers) as resp:
						user_data = await resp.json()

			if not await UsersDB.is_user_allowed(int(user_data["id"])):
				raise HTTPException(status_code=403, detail="Access Denied")

			jwt_payload = {
				"user_id": user_data["id"]
			}
			jwt_token = AuthUtil.encode(jwt_payload)
			response = RedirectResponse(url=os.environ.get("FRONTEND_URL").rstrip("/") + "/dash")
			response.set_cookie(key="Authorization", value=jwt_token, httponly=True, secure=True, samesite="lax")
			return response

		@self.post("/api/dsc/create_announcement")
		async def send_announcement(payload: AnnouncementPayload):
			try:
				message_payload = json.dumps({
					"action": "send_announcement",
					"channel_id": payload.channel_id,
					"everyone": payload.everyone,
					"message": payload.message
				})
				response = await self.sender.send_async(message_payload)
    
			except OSError as e:
				Log.error(f"failed to send announcement: {e}")
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
				Log.error(f"failed to create event: {e}")
				raise HTTPException(status_code=503, detail="Bot connection unavailable") from e
			except Exception as exc:
				Log.error(f"unexpected error creating event: {exc}")
				raise HTTPException(status_code=500, detail="Failed to create event") from exc

			return JSONResponse(content=response)