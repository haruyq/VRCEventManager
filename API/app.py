import vrchatapi
import os
import json
import aiohttp
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from contextlib import asynccontextmanager

from payloads import *

from connector.sender import Sender
from utils.logger import Logger
from utils.database import UsersDB
from utils.auth import AuthUtil
from utils.vrc import VRChatLogin

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
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            try:
                await UsersDB.init_db()
                AuthUtil.generate_key()
                await self.sender.connect_async()
            except OSError as e:
                Log.warning(f"initial connection to bot failed: {e}")
            yield
        
        self.router.lifespan_context = lifespan
        
        self.vrc_api_client = None
        self.vrc_email = None
        self.vrc_password = None

        @self.get("/api/login")
        async def login(request: Request):
            auth = request.cookies.get("Authorization", None)
            if auth and await AuthUtil.verify_user(str(auth), self.sender):
                return RedirectResponse(url=os.environ.get("FRONTEND_URL").rstrip("/") + "/dash")
            
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
                        
            allowed = await UsersDB.is_user_allowed(int(user_data["id"]), self.sender)
            if not allowed:
                raise HTTPException(status_code=403, detail="Access Denied")

            jwt_payload = {
                "user_id": user_data["id"],
                "email": user_data["email"],
            }
            jwt_token = AuthUtil.encode(jwt_payload)
            response = RedirectResponse(url=os.environ.get("FRONTEND_URL").rstrip("/") + "/dash")
            response.set_cookie(
                key="Authorization",
                value=jwt_token,
                httponly=True,
                secure=True,
                samesite="none",
                domain="." + os.environ.get("DOMAIN")
            )
   
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

            except OSError as e:
                Log.error(f"failed to create event: {e}")
                raise HTTPException(status_code=503, detail="Bot connection unavailable") from e
            except Exception as exc:
                Log.error(f"unexpected error creating event: {exc}")
                raise HTTPException(status_code=500, detail="Failed to create event") from exc

            return JSONResponse(content=response)
        
        @self.post("/api/vrc/login")
        async def vrc_login(request: Request, payload: VRCLoginPayload, Authorization: str = Header()):
            if not await AuthUtil.verify_user(Authorization, self.sender):
                raise HTTPException(status_code=403, detail="Invalid or Expired Token")

            vrchat_login = VRChatLogin(payload.email, payload.password)
            try:
                api_client, current_user = await vrchat_login.login_async()
                
                self.vrc_api_client = api_client
                self.vrc_email = payload.email
                self.vrc_password = payload.password
                
                if not isinstance(current_user, vrchatapi.CurrentUser):
                    return JSONResponse(content={
                        "twofa_required": True,
                        "twofa_type": current_user  # "Email" or "TOTP"
                    })
                
                else:
                    return JSONResponse(content={
                        "twofa_required": False,
                        "user_id": current_user.id,
                        "display_name": current_user.display_name
                    })
                    
            except Exception as e:
                Log.error(f"VRChat login failed: {e}")
                self.vrc_api_client = None
                self.vrc_email = None
                self.vrc_password = None
                raise HTTPException(status_code=500, detail="VRChat login failed")
        
        @self.post("/api/vrc/twofa")
        async def vrc_twofa(request: Request, payload: VRCTwoFAPayload, Authorization: str = Header()):
            if not await AuthUtil.verify_user(Authorization, self.sender):
                raise HTTPException(status_code=403, detail="Invalid or Expired Token")
            
            if not self.vrc_email or not self.vrc_password:
                raise HTTPException(status_code=400, detail="VRChat credentials not found. Please login again.")

            vrchat_login = VRChatLogin(self.vrc_email, self.vrc_password)
            try:
                api_client, current_user = await vrchat_login.twofa_async(
                    api_client=self.vrc_api_client,
                    code=payload.code,
                    type=payload.type
                )
                
                if not isinstance(current_user, vrchatapi.CurrentUser):
                    raise HTTPException(status_code=500, detail="2FA verification failed")
                
                else:
                    return JSONResponse(content={
                        "user_id": current_user.id,
                        "display_name": current_user.display_name
                    })
                    
            except Exception as e:
                Log.error(f"VRChat 2FA verification failed: {e}")
                raise HTTPException(status_code=500, detail="VRChat 2FA verification failed")
            
            finally:
                self.vrc_api_client = None
                self.vrc_email = None
                self.vrc_password = None
        
        @self.post("/api/vrc/logout")
        async def vrc_logout(request: Request, Authorization: str = Header()):
            if not await AuthUtil.verify_user(Authorization, self.sender):
                raise HTTPException(status_code=403, detail="Invalid or Expired Token")
            
            vrchat_login = VRChatLogin(self.vrc_email, self.vrc_password)
            try:
                removed = await vrchat_login.logout_async()
                if not removed:
                    raise HTTPException(status_code=500, detail="VRChat logout failed")
                
                self.vrc_api_client = None
                self.vrc_email = None
                self.vrc_password = None
                
                return JSONResponse(content={
                    "logout": True
                })
                
            except Exception as e:
                Log.error(f"VRChat logout failed: {e}")
                raise HTTPException(status_code=500, detail="VRChat logout failed")