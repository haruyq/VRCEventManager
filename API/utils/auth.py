import os
from authlib.jose import jwt
from jwcrypto import jwk
from cryptography.hazmat.primitives import serialization

from utils.logger import Logger
from utils.database import UsersDB
from connector.sender import Sender

Log = Logger(__name__)

KEYFILE = "/Secrets/key.pem"

key: bytes | None = None

class AuthUtil:
    @staticmethod
    def generate_key():
        if not os.path.isfile(KEYFILE):
            password = os.environ.get("JWT_SECRET")
            if password:
                password = password.encode("utf-8")
            with open(KEYFILE, "wb") as f:
                f.write(
                    jwk.JWK.generate(
                        kty='RSA',
                        size=2048
                    ).export_to_pem(
                        private_key=True,
                        password=password
                    )
                )

    @staticmethod
    def read_key():
        global key
        if key is None:
            password = os.environ.get("JWT_SECRET")
            if password:
                password = password.encode("utf-8")
            with open(KEYFILE, "rb") as f:
                key = serialization.load_pem_private_key(
                    f.read(),
                    password=password
                )
        return key

    @staticmethod
    def encode(payload: dict) -> str:
        private_key = AuthUtil.read_key()
        header = {"alg": "RS256"}
        token = jwt.encode(header, payload, private_key)
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token

    @staticmethod
    def decode(token: str):
        public_key = AuthUtil.read_key().public_key()
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        if isinstance(token, str) and token.startswith("b'") and token.endswith("'"):
            token = token[2:-1]
        return jwt.decode(token, public_key)

    @staticmethod
    def verify(token: str):
        try:
            decoded = jwt.decode(token, AuthUtil.read_key().public_key())
            decoded.validate()
            return True
        except Exception as e:
            Log.error(f"Token verification failed: {e}")
            return False

    @staticmethod
    async def verify_user(token: str, sender: Sender) -> bool:
        try:
            decoded = AuthUtil.decode(token)
            decoded.validate()
        except Exception:
            return False

        user_id = int(decoded.get("user_id", 0))
        try:
            return await UsersDB.is_user_allowed(user_id, sender)
        except Exception as exc:
            Log.error(f"Error verifying user: {exc}", exc_info=True)
            return False