import os
import json
import asyncio

from authlib.jose import jwt
from jwcrypto import jwk

from utils.database import UsersDB

KEYFILE = "/Secrets/key.pem"

class AuthUtil:
    @staticmethod
    def generate_key():
        if not os.path.isfile(KEYFILE):
            with open(KEYFILE, "wb") as f:
                f.write(
                    jwk.JWK.generate(
                        kty='RSA', 
                        size=2048
                    )
                    .export_to_pem(
                            private_key=True, 
                            password=os.environ.get("JWT_SECRET")
                    )
                )
                
    @staticmethod
    def read_key():
        global key
        if key is None:
            with open(KEYFILE, "rb") as f:
                key = f.read()
        return key

    @staticmethod
    def decode(token: str):
        return jwt.decode(token, AuthUtil.read_key())

    @staticmethod
    def encode(payload: dict):
        return jwt.encode({"alg": "RS256"}, payload, AuthUtil.read_key()).decode('utf-8')

    @staticmethod
    def verify(token: str):
        try:
            jwt.decode(token, AuthUtil.read_key()).validate()
            return True
        except:
            return False
    
    @staticmethod
    def verify_user(token: str):
        try:
            decoded = jwt.decode(token, AuthUtil.read_key())
            decoded.validate()
            user_id = int(decoded.get("user_id"))
            loop = asyncio.get_event_loop()
            is_allowed = loop.run_until_complete(UsersDB.is_user_allowed_async(user_id))
            return is_allowed
        except:
            return False