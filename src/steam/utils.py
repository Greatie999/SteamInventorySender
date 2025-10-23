import base64
import hmac
import random
import struct
import time
from hashlib import sha1

import rsa
from google.protobuf.message import Message

from .pb.steammessages_auth.steamclient_pb2 import (
    EAuthTokenPlatformType,
    k_EAuthTokenPlatformType_MobileApp,
    k_EAuthTokenPlatformType_SteamClient,
    k_EAuthTokenPlatformType_WebBrowser,
)


def pbmessage_to_request(msg: Message) -> str:
    return str(base64.b64encode(msg.SerializeToString()), "utf8")


def get_website_id_by_platform(platform: EAuthTokenPlatformType) -> str:
    if platform == k_EAuthTokenPlatformType_MobileApp:
        return "Mobile"
    elif platform == k_EAuthTokenPlatformType_SteamClient:
        return "Client"
    elif platform == k_EAuthTokenPlatformType_WebBrowser:
        return "Community"
    return "Unknown"


def sha1_hash(data: bytes) -> bytes:
    return sha1(data).digest()


def generate_sessionid() -> str:
    choices = "0123456789abcdef"
    return "".join([random.choice(choices) for _ in range(24)])


def do_no_cache():
    return int(time.time() * 1000) - (18 * 60 * 60)


def generate_code(shared_secret: str) -> str:
    timestamp = int(time.time())
    time_buffer = struct.pack(">Q", timestamp // 30)
    time_hmac = hmac.new(base64.b64decode(shared_secret), time_buffer, digestmod=sha1).digest()
    begin = ord(time_hmac[19:20]) & 0xF
    full_code = struct.unpack(">I", time_hmac[begin : begin + 4])[0] & 0x7FFFFFFF
    chars = "23456789BCDFGHJKMNPQRTVWXY"
    code = []
    for _ in range(5):
        full_code, i = divmod(full_code, len(chars))
        code.append(chars[i])
    return "".join(code)


def get_confirmation_hash(identity_secret: str, tag: str, server_time: int) -> str:
    buffer = struct.pack(">Q", server_time) + tag.encode("ascii")
    return base64.b64encode(
        hmac.new(base64.b64decode(identity_secret), buffer, digestmod=sha1).digest()
    ).decode()


def generate_device_id(steam_id64: int) -> str:
    hexed_steam_id = sha1(str(int(steam_id64)).encode("ascii")).hexdigest()
    partial_id = (
        hexed_steam_id[:8],
        hexed_steam_id[8:12],
        hexed_steam_id[12:16],
        hexed_steam_id[16:20],
        hexed_steam_id[20:32],
    )
    return f'android:{"-".join(partial_id)}'


def encrypt_password(password: str, keys) -> str:
    publickey_exp = int(keys.publickey_exp, 16)
    publickey_mod = int(keys.publickey_mod, 16)
    public_key = rsa.PublicKey(n=publickey_mod, e=publickey_exp)
    encrypted_password = rsa.encrypt(message=password.encode("ascii"), pub_key=public_key)
    return str(base64.b64encode(encrypted_password), "utf8")
