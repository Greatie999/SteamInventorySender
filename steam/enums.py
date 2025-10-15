from enum import Enum


class SteamURL(str, Enum):
    API = "https://api.steampowered.com"
    LOGIN = "https://login.steampowered.com"
    COMMUNITY = "https://steamcommunity.com"
    STORE = "https://store.steampowered.com"
