from typing import (
    Any,
    Optional,
    List,
    Generic,
    TypeVar,
)

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
)

T = TypeVar("T")


class BaseSteamParseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Error(BaseSteamParseModel):
    code: Optional[str] = None
    message: Optional[str] = None
    error_type: Optional[int] = Field(default=None, alias="type")


class ResponseBase(BaseSteamParseModel, Generic[T]):
    result: Optional[T] = None
    errors: Optional[List[Error]] = None
    is_error: bool = Field(alias="isError")
    time_generated: str = Field(alias="timeGenerated")


class BaseResponse(ResponseBase[Any]):
    pass


class CurrencyRate(BaseSteamParseModel):
    currency_type: int = Field(alias="currencyType")
    rate_to_usd: float = Field(alias="rateToUSD")
    updated_at: str = Field(alias="updatedAt")


class CurrencyRateResponse(ResponseBase[CurrencyRate]):
    pass


class CurrencyRateListResponse(ResponseBase[List[CurrencyRate]]):
    pass


class ItemStats(BaseSteamParseModel):
    average_price: Optional[float] = Field(default=None, alias="averagePrice")
    safe_price: Optional[float] = Field(default=None, alias="safePrice")
    quantity: Optional[int] = None


class Item(BaseSteamParseModel):
    hash_name: Optional[str] = Field(default=None, alias="hashName")
    steam_game: int = Field(alias="steamGame")
    item_id: Optional[int] = Field(default=None, alias="itemId")
    price_ask: Optional[float] = Field(default=None, alias="priceAsk")
    price_bid: Optional[float] = Field(default=None, alias="priceBid")
    statistics_1d: Optional[ItemStats] = Field(default=None, alias="statistics1d")
    statistics_3d: Optional[ItemStats] = Field(default=None, alias="statistics3d")
    statistics_7d: Optional[ItemStats] = Field(default=None, alias="statistics7d")
    statistics_30d: Optional[ItemStats] = Field(default=None, alias="statistics30d")
    refreshed_at: str = Field(alias="refreshedAt")
    updated_at: str = Field(alias="updatedAt")
    created_at: str = Field(alias="createdAt")


class ItemResponse(ResponseBase[Item]):
    pass


class TrackedItemsPage(BaseSteamParseModel):
    items: Optional[List[Item]] = None
    total_count: int = Field(alias="totalCount")
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")


class TrackedItemsResponse(ResponseBase[TrackedItemsPage]):
    pass


class HistogramPoint(BaseSteamParseModel):
    price: float
    quantity: int


class Histogram(BaseSteamParseModel):
    item_id: int = Field(alias="itemId")
    buy_orders: Optional[List[HistogramPoint]] = Field(default=None, alias="buyOrders")
    sell_orders: Optional[List[HistogramPoint]] = Field(default=None, alias="sellOrders")
    highest_buy_order: Optional[float] = Field(default=None, alias="highestBuyOrder")
    lowest_sell_order: Optional[float] = Field(default=None, alias="lowestSellOrder")
    total_buy_orders: Optional[int] = Field(default=None, alias="totalBuyOrders")
    total_sell_orders: Optional[int] = Field(default=None, alias="totalSellOrders")


class HistogramResponse(ResponseBase[Histogram]):
    pass


class PricePoint(BaseSteamParseModel):
    price: float
    quantity: int
    date: str


class PriceHistoryResponse(ResponseBase[List[PricePoint]]):
    pass


class StringResponse(ResponseBase[str]):
    pass


class TrackedItemsQuery(BaseSteamParseModel):
    game: Optional[int] = Field(default=None, alias="SteamGame")
    page: Optional[int] = Field(default=None, alias="Page")
    page_size: Optional[int] = Field(default=None, alias="PageSize")


class ItemInfoQuery(BaseSteamParseModel):
    hash_name: Optional[str] = Field(default=None, alias="HashName")
    game: Optional[int] = Field(default=None, alias="SteamGame")


class ItemDictionaryQuery(BaseSteamParseModel):
    key: Optional[str] = Field(default=None, alias="Key")
    game: Optional[int] = Field(default=None, alias="SteamGame")


class TrackItemBody(BaseSteamParseModel):
    hash_name: Optional[str] = Field(default=None, alias="hashName")
    game: int = Field(alias="steamGame")


class HistogramQuery(BaseSteamParseModel):
    market_hash_name: Optional[str] = Field(default=None, alias="MarketHashName")
    game: Optional[int] = Field(default=None, alias="SteamGame")
    currency: Optional[int] = Field(default=None, alias="Currency")
    force_refresh: Optional[bool] = Field(default=None, alias="ForceRefresh")


class PriceHistoryQuery(BaseSteamParseModel):
    market_hash_name: Optional[str] = Field(default=None, alias="MarketHashName")
    game: Optional[int] = Field(default=None, alias="SteamGame")
    currency: Optional[int] = Field(default=None, alias="Currency")
    force_refresh: Optional[bool] = Field(default=None, alias="ForceRefresh")
