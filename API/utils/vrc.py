import vrchatapi
from vrchatapi.api import authentication_api
from vrchatapi.exceptions import UnauthorizedException
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode
from vrchatapi.api_client import ApiClient

import os
import json
import asyncio

from cryptography.fernet import Fernet, InvalidToken
from http.cookiejar import Cookie

from utils.logger import Logger

Log = Logger(__name__)
CREDENTIAL_PATH = "/Secrets/vrc/credential.json"

class Credentials: # TODO: セキュリティ実装しようね
    @staticmethod
    def save_cookie(email: str, password: str, cookie_jar):
        data = {
            "email": email,
            "password": password,
            "auth": cookie_jar["auth"].value,
            "twoFactorAuth": cookie_jar["twoFactorAuth"].value,
        }
        
        os.makedirs("/Secrets/vrc", exist_ok=True)
        with open(CREDENTIAL_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_cookie():
        if not os.path.exists(CREDENTIAL_PATH):
            return None

        try:
            with open(CREDENTIAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            Log.error("Failed to load VRChat credentials: %s", exc)
            return None

    @staticmethod
    def remove_credential():
        if os.path.exists(CREDENTIAL_PATH):
            os.remove(CREDENTIAL_PATH)
            return True
        return False

    @staticmethod
    def logged_in():
        return os.path.exists(CREDENTIAL_PATH)

class VRChatLogin:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password

    @staticmethod
    def _make_cookie(name, value):
        return Cookie(0, name, value,
                    None, False,
                    "api.vrchat.cloud", True, False,
                    "/", False,
                    False,
                    173106866300,
                    False,
                    None,
                    None, {})

    @staticmethod
    def login_using_cookie():
        if Credentials.logged_in():
            data = Credentials.load_cookie()

        else:
            Log.error("No saved VRChat credentials found.")
            return None, None
        
        try:
            configuration = vrchatapi.Configuration(
                username=data["email"],
                password=data["password"],
            )
            with vrchatapi.ApiClient(configuration) as api_client:
                api_client.user_agent = "VRChatEventManager/0.1.0 haruyq@users.noreply.github.com"
                api_client.rest_client.cookie_jar.set_cookie(
                    VRChatLogin._make_cookie("auth", data["auth"]))
                api_client.rest_client.cookie_jar.set_cookie(
                    VRChatLogin._make_cookie("twoFactorAuth", data["twoFactorAuth"]))

                auth_api = authentication_api.AuthenticationApi(api_client)
                current_user = auth_api.get_current_user()
                
                return api_client, current_user
            
        except vrchatapi.ApiException as e:
            Log.error("Exception when calling API: %s\n", e)
            return None, None

    def login(self):
        """VRChatにログインするためのメソッド

        Args:
            email (str): VRChatアカウントのメールアドレス
            password (str): VRChatアカウントのパスワード

        Returns:
            tuple:
                成功した場合はApiClientインスタンスと現在のユーザー情報を返す。
                twoFAが必要な場合はApiClientインスタンスと2FAの種類("Email"または"TOTP")を返す。
                失敗した場合は(None, None)を返す。
        """
        configuration = vrchatapi.Configuration(
            username = self.email,
            password = self.password,
        )
        with vrchatapi.ApiClient(configuration) as api_client:
            api_client.user_agent = "VRChatEventManager/0.1.0 haruyq@users.noreply.github.com"

            auth_api = authentication_api.AuthenticationApi(api_client)

            try:
                current_user = auth_api.get_current_user()
            except UnauthorizedException as e:
                if e.status == 200:
                    if "Email 2 Factor Authentication" in e.reason:
                        return api_client, "Email"
                    elif "2 Factor Authentication" in e.reason:
                        return api_client, "TOTP"
                else:
                    Log.error("Exception when calling API: %s\n", e)
                    return None, None
                    
            except vrchatapi.ApiException as e:
                Log.error("Exception when calling API: %s\n", e)
                return None, None

            cookie_jar = api_client.rest_client.cookie_jar._cookies["api.vrchat.cloud"]["/"]

            Credentials.save_cookie(self.email, self.password, cookie_jar)

            return api_client, current_user

    def twofa(self, api_client: ApiClient, code: str, type: str):
        auth_api = authentication_api.AuthenticationApi(api_client)
        
        try:
            if type == "Email":
                auth_api.verify2_fa_email_code(two_factor_email_code=TwoFactorEmailCode(code))
            
            elif type == "TOTP":
                auth_api.verify2_fa(two_factor_auth_code=TwoFactorAuthCode(code))
            
            current_user = auth_api.get_current_user()
            cookie_jar = api_client.rest_client.cookie_jar._cookies["api.vrchat.cloud"]["/"]

            Credentials.save_cookie(self.email, self.password, cookie_jar)

            return api_client, current_user
        
        except vrchatapi.ApiException as e:
            Log.error("Exception when calling API: %s\n", e)
    
    def logout(self):
        return Credentials.remove_credential()

    @staticmethod
    async def login_using_cookie_async():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, VRChatLogin.login_using_cookie)

    async def login_async(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.login)

    async def twofa_async(self, api_client: ApiClient, code: str, type: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.twofa, api_client, code, type)
    
    async def logout_async(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.logout)