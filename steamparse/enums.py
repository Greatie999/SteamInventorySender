from enum import (
    IntEnum, 
    Enum,
)


class Currency(IntEnum):
    USD = 1
    GBP = 2
    EUR = 3
    CHF = 4
    RUB = 5
    PLN = 6
    BRL = 7
    JPY = 8
    NOK = 9
    IDR = 10
    MYR = 11
    PHP = 12
    SGD = 13
    THB = 14
    VND = 15
    KRW = 16
    UAH = 18
    MXN = 19
    CAD = 20
    AUD = 21
    NZD = 22
    CNY = 23
    INR = 24
    CLP = 25
    PEN = 26
    COP = 27
    ZAR = 28
    HKD = 29
    TWD = 30
    SAR = 31
    AED = 32
    ILS = 35
    KZT = 37
    KWD = 38
    QAR = 39
    CRC = 40
    UYU = 41


class Game(IntEnum):
    TF2 = 440
    DOTA2 = 570
    CSGO = 730
    STEAM = 753
    PUBG = 578080


class DictionaryKey(Enum):
    buy_order = "buy_order"
    min_price = "min_price"
    average_price_1d = "average_price_1d"
    safe_price_1d = "safe_price_1d"
    quantity_1d = "quantity_1d"
    average_price_3d = "average_price_3d"
    safe_price_3d = "safe_price_3d"
    quantity_3d = "quantity_3d"
    average_price_7d = "average_price_7d"
    safe_price_7d = "safe_price_7d"
    quantity_7d = "quantity_7d"
    average_price_30d = "average_price_30d"
    safe_price_30d = "safe_price_30d"
    quantity_30d = "quantity_30d"
