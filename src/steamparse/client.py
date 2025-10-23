import json
from typing import (
    Any,
    Dict,
    Literal,
    Optional,
    Type,
    TypeVar,
)

from httpx import (
    AsyncClient,
    Response,
)
from pydantic import (
    BaseModel,
    ValidationError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
)

from .endpoints import (
    CURRENCY_RATES,
    CURRENCY_RATE_BY,
    ITEMS_TRACKED,
    ITEMS_INFO,
    ITEMS_DICTIONARY,
    ITEMS_TRACK,
    STEAM_HISTOGRAM,
    STEAM_PRICE_HISTORY,
)
from .exceptions import (
    error_retry_policy,
    handle_retry_error,
    SteamParseError,
)
from .schemas import (
    CurrencyRateResponse,
    CurrencyRateListResponse,
    TrackedItemsResponse,
    ItemResponse,
    HistogramResponse,
    PriceHistoryResponse,
    TrackedItemsQuery,
    ItemInfoQuery,
    ItemDictionaryQuery,
    TrackItemBody,
    HistogramQuery,
    PriceHistoryQuery,
    BaseResponse,
)

T = TypeVar("T", bound=BaseModel)


class SteamParseClient:
    def __init__(
        self,
        base_url: str = "http://65.109.143.76:5000",
        bearer_token: Optional[str] = None,
        timeout: float = 20.0,
        client: Optional[AsyncClient] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._bearer_token = bearer_token
        self._client = client or AsyncClient(
            timeout=timeout,
            base_url=self._base_url,
        )

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        return headers

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(5),
        retry_error_callback=handle_retry_error,
        retry=error_retry_policy,
    )
    async def _request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        endpoint: str,
        response_model: Optional[Type[T]],
        *,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> T:
        response = await self._client.request(
            method=method,
            url=endpoint,
            params=params,
            json=data,
            headers=self._headers(),
        )
        return await self._handle_response(response, response_model)

    @staticmethod
    async def _handle_response(response: Response, response_model: Type[T]) -> T:
        if not response.is_success:
            raise SteamParseError(
                f"SteamParse Client Error (Status Code: {response.status_code}, Text: {response.text})"
            )
        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            raise SteamParseError("SteamParse Client Error (Invalid JSON)") from e
        try:
            return response_model.model_validate(response_data)
        except ValidationError as e:
            raise SteamParseError("SteamParse Client Error (Invalid Pydantic Model)") from e

    async def list_currency_rates(self) -> CurrencyRateListResponse:
        return await self._request(
            method="GET",
            endpoint=CURRENCY_RATES,
            response_model=CurrencyRateListResponse,
        )

    async def get_currency_rate(self, currency: int) -> CurrencyRateResponse:
        return await self._request(
            method="GET",
            endpoint=CURRENCY_RATE_BY.format(currency=currency),
            response_model=CurrencyRateResponse,
        )

    async def get_tracked_items(self, query: TrackedItemsQuery) -> TrackedItemsResponse:
        return await self._request(
            method="GET",
            endpoint=ITEMS_TRACKED,
            response_model=TrackedItemsResponse,
            params=query.model_dump(by_alias=True, exclude_none=True),
        )

    async def get_item(self, query: ItemInfoQuery) -> ItemResponse:
        return await self._request(
            method="GET",
            endpoint=ITEMS_INFO,
            response_model=ItemResponse,
            params=query.model_dump(by_alias=True, exclude_none=True),
        )

    async def get_item_dictionary(self, query: ItemDictionaryQuery) -> BaseResponse:
        return await self._request(
            method="GET",
            endpoint=ITEMS_DICTIONARY,
            response_model=BaseResponse,
            params=query.model_dump(by_alias=True, exclude_none=True),
        )

    async def track_item(self, body: TrackItemBody) -> BaseResponse:
        return await self._request(
            method="POST",
            endpoint=ITEMS_TRACK,
            response_model=BaseResponse,
            data=body.model_dump(by_alias=True, exclude_none=True),
        )

    async def untrack_item(self, body: TrackItemBody) -> BaseResponse:
        return await self._request(
            method="DELETE",
            endpoint=ITEMS_TRACK,
            response_model=BaseResponse,
            data=body.model_dump(by_alias=True, exclude_none=True),
        )

    async def get_histogram(self, query: HistogramQuery) -> HistogramResponse:
        return await self._request(
            method="POST",
            endpoint=STEAM_HISTOGRAM,
            response_model=HistogramResponse,
            params=query.model_dump(by_alias=True, exclude_none=True),
        )

    async def get_price_history(self, query: PriceHistoryQuery) -> PriceHistoryResponse:
        return await self._request(
            method="POST",
            endpoint=STEAM_PRICE_HISTORY,
            response_model=PriceHistoryResponse,
            params=query.model_dump(by_alias=True, exclude_none=True),
        )
