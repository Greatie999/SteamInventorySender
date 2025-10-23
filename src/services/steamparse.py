from src.steamparse import (
    SteamParseClient,
    Game,
    DictionaryKey,
    ItemDictionaryQuery,
)


class SteamParseService:
    def __init__(
        self,
        base_url: str,
        bearer_token: str | None = None,
        timeout: float = 30.0
    ):
        self._client = SteamParseClient(
            base_url=base_url,
            bearer_token=bearer_token,
            timeout=timeout,
        )

    async def close(self):
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def fetch_price_dictionary(self, game: Game = Game.CSGO) -> dict[str, float]:
        resp = await self._client.get_item_dictionary(
            ItemDictionaryQuery(
                Key=DictionaryKey.safe_price_7d.value,
                SteamGame=game,
            )
        )
        return resp.model_dump().get("result", {})

    async def fetch_currency_rates(self) -> dict[int, float]:
        resp = await self._client.list_currency_rates()
        return {
            cr.currency_type: cr.rate_to_usd
            for cr in (resp.result or [])
            if cr.currency_type > 0 and cr.rate_to_usd > 0
        }

