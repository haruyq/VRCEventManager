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

class Credentials:
    def __init__(self):
        self.keyfile = "/Secrets/vrc/key.pem"
        self.credential = "/Secrets/vrc/credential.txt" # TODO: 下ではJSONになっているので、.txtにしたほうが適切かも。どうせ中身はBytesだし～
    
    def _gen_key(self):
        key = Fernet.generate_key()
        os.makedirs("/Secrets/vrc", exist_ok=True)
        with open(self.keyfile, "wb") as f:
            f.write(key)
        
        return key

    def _get_fernet(self) -> Fernet:
        try:
            with open(self.keyfile, "rb") as f:
                key = f.read().decode("utf-8")
        except Exception as e:
            Log.debug("Failed to read VRChat key: %s", e)
            key = self._gen_key()
        try:
            return Fernet(key)
        except (ValueError, TypeError) as exc:
            raise RuntimeError("cannot encrypt VRChat credentials.") from exc

    def save_cookie(self, email: str, password: str, cookie_jar):
        fernet = self._get_fernet()

        data = {
            "email": email,
            "password": password,
            "auth": cookie_jar["auth"].value,
            "twoFactorAuth": cookie_jar["twoFactorAuth"].value,
        }
        payload = json.dumps(data).encode("utf-8")
        encrypted_payload = fernet.encrypt(payload)

        with open("/Secrets/vrc/credential.json", "wb") as f:
            f.write(encrypted_payload)

    def load_cookie(self):
        credential_path = "/Secrets/vrc/credential.json"
        if not os.path.exists(credential_path):
            return None

        fernet = self._get_fernet()

        with open(credential_path, "rb") as f:
            encrypted_payload = f.read()

        try:
            decrypted = fernet.decrypt(encrypted_payload)
        except InvalidToken as exc:
            Log.error("Failed to decrypt VRChat credentials: %s", exc)
            return None

        return json.loads(decrypted.decode("utf-8"))

    def remove_credential(self):
        credential_path = "/Secrets/vrc/credential.json"
        if os.path.exists(credential_path):
            os.remove(credential_path)
            return True
        return False

    def logged_in(self):
        with open("/Secrets/vrc/credential.json", "rb") as f:
            if f.readable():
                return True
            else:
                return False

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
        credential = Credentials()
        if credential.logged_in():
            data = credential.load_cookie()
        
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
            
            credential = Credentials()
            credential.save_cookie(self.email, self.password, cookie_jar)

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
            
            credential = Credentials()
            credential.save_cookie(self.email, self.password, cookie_jar)

            return api_client, current_user
        
        except vrchatapi.ApiException as e:
            Log.error("Exception when calling API: %s\n", e)
    
    def logout(self):
        credential = Credentials()
        return credential.remove_credential()

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