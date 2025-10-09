import os
import json

from authlib.jose import jwt
from jwcrypto import jwk

KEYFILE = "/Secrets/key.pem"

class AuthUtil:
    @staticmethod
    def generate_key():
        with open(KEYFILE, "w", encoding="utf-8") as f:
            f.write(jwk.JWK.generate(kty='RSA', size=2048).export_to_pem(private_key=True, password=os.environ.get("JWT_SECRET")))

    @staticmethod
    def decode(token: str):
        with open(KEYFILE, "r", encoding="utf-8") as f:
            key = f.read()
        return jwt.decode(token, key)
    
    @staticmethod
    def encode(payload: dict):
        with open(KEYFILE, "r", encoding="utf-8") as f:
            key = f.read()
        return jwt.encode({"alg": "RS256"}, payload, key).decode('utf-8')

    @staticmethod
    def verify(token: str):
        with open(KEYFILE, "r", encoding="utf-8") as f:
            key = f.read()
        try:
            jwt.decode(token, key).validate()
            return True
        except:
            return False