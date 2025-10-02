import asyncio
import socket
import time
import json
from typing import Optional

from utils.logger import Logger

Log = Logger(__name__)

class Sender:
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.s: Optional[socket.socket] = None

    def connect(self, retries: int = 5, delay: float = 5.0):
        if self.s is not None:
            return

        last_exc: Optional[OSError] = None
        for attempt in range(1, retries + 1):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect((self.ip, self.port))
            except OSError as e:
                last_exc = e
                s.close()
                Log.warning(f"connection attempt {attempt}/{retries} failed: {e}")
                if attempt < retries:
                    time.sleep(delay)
                continue

            self.s = s
            Log.info(f"connected to {self.ip}:{self.port}")
            return

        Log.error(f"failed to connect to {self.ip}:{self.port} after {retries} attempts")
        if last_exc is not None:
            raise last_exc
        raise OSError(f"Could not connect to {self.ip}:{self.port}")

    def close(self):
        if self.s is None:
            return
        try:
            self.s.close()
        except OSError as e:
            Log.warning(f"error while closing socket: {e}")
        finally:
            self.s = None

    def ensure_connection(self):
        if self.s is None:
            self.connect()

    def send(self, message: str):
        self.ensure_connection()
        assert self.s is not None
        try:
            Log.debug(f"send -> message: {message}")
            self.s.sendall(message.encode("utf-8"))
            
            decoded = self.s.recv(4096).decode()
            Log.debug(f"recv -> response: {decoded}")
            return json.loads(decoded)
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            Log.warning(f"socket error while sending, will retry once: {e}")
            self.close()
            self.ensure_connection()
            assert self.s is not None
            Log.debug(f"send -> message: {message}")
            self.s.sendall(message.encode("utf-8"))

            decoded = self.s.recv(4096).decode("utf-8")
            Log.debug(f"recv -> response: {decoded}")
            return json.loads(decoded)

    async def connect_async(self):
        return await asyncio.to_thread(self.connect)

    async def send_async(self, message: str):
        return await asyncio.to_thread(self.send, message)