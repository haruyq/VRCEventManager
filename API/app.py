import os
import json
import aiohttp
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from payloads import *

from connector.sender import Sender
from utils.logger import Logger
from utils.database import UsersDB
from utils.auth import AuthUtil

Log = Logger(__name__)
DISCORD_API_BASE = "https://discord.com/api"

class VRCEvMngrAPI(FastAPI):
    def __init__(self):
        self.sender = Sender(
            ip=os.environ.get("BOT_SOCK_ADDRESS"),
            port=int(os.environ.get("BOT_SOCK_PORT"))
            )
        super().__init__(
            title="VRChatEventManager-API"
        )

        self.add_middleware(
            CORSMiddleware,
            allow_origins=["https://main.example.com"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.on_event("startup")
        async def startup_event():
            await UsersDB.init_db()
            AuthUtil.generate_key()
            
            # allowed_users = await UsersDB.get_allowed_users()
            # Log.info(f"Allowed users: {allowed_users}")

            try:
                await self.sender.connect_async()
            except OSError as e:
                Log.warning(f"initial connection to bot failed: {e}")

        @self.get("/api/login")
        async def login(request: Request):
            auth = request.cookies.get("Authorization", None)
            if auth and await AuthUtil.verify_user(str(auth), self.sender):
                raise HTTPException(status_code=403, detail="Already Logged In")
            
            params = {
                "client_id": os.environ.get("CLIENT_ID"),
                "redirect_uri": os.environ.get("REDIRECT_URL"),
                "response_type": "code",
                "scope": "identify email"
            }
            redirect_url = f"{DISCORD_API_BASE}/oauth2/authorize?{urlencode(params)}"
            return RedirectResponse(redirect_url)

        @self.get("/api/login/callback")
        async def callback(request: Request, code: str):
            auth = request.cookies.get("Authorization", None)
            if auth and await AuthUtil.verify_user(str(auth), self.sender):
                raise HTTPException(status_code=403, detail="Already Logged In")

            if not code:
                raise HTTPException(status_code=400, detail="Missing Arguments")

            async with aiohttp.ClientSession() as session:
                headers = { "Content-Type": "application/x-www-form-urlencoded" }
                data = {
                    "client_id": os.environ.get("CLIENT_ID"),
                    "client_secret": os.environ.get("CLIENT_SECRET"),
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": os.environ.get("REDIRECT_URL")
                }
                async with session.post(f"{DISCORD_API_BASE}/oauth2/token", headers=headers, data=data) as resp:
                    if resp.status != 200:
                        Log.error(f"Failed to fetch token from Discord: {resp.status} | {await resp.text()}")
                        raise HTTPException(status_code=503, detail="Failed to fetch token from Discord")
                    token_data = await resp.json()

                headers = { "Authorization": f"Bearer {token_data['access_token']}" }
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{DISCORD_API_BASE}/users/@me", headers=headers) as resp:
                        user_data = await resp.json()

            # GuildIDはいつか可変にするかも
            allowed = await UsersDB.is_user_allowed(int(user_data["id"]), self.sender)
            if not allowed:
                raise HTTPException(status_code=403, detail="Access Denied")

            jwt_payload = {
                "user_id": user_data["id"],
                "email": user_data["email"],
            }
            jwt_token = AuthUtil.encode(jwt_payload)
            response = RedirectResponse(url=os.environ.get("FRONTEND_URL").rstrip("/") + "/dash")
            response.set_cookie(key="Authorization", value=jwt_token, httponly=True, secure=True, samesite="none", domain="." + os.environ.get("DOMAIN"))
   
            Log.debug(f"User {user_data['id']} logged in successfully")
            return response

        @self.post("/api/dsc/create_announcement")
        async def send_announcement(payload: AnnouncementPayload, Authorization: str = Header()):
            if not await AuthUtil.verify_user(Authorization, self.sender):
                raise HTTPException(status_code=403, detail="Invalid or Expired Token")
            
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
        async def create_event(payload: CreateEventPayload, Authorization: str = Header()):
            if not await AuthUtil.verify_user(Authorization, self.sender):
                raise HTTPException(status_code=403, detail="Invalid or Expired Token")
            
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