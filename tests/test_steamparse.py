import asyncio
from loguru import logger
from steamparse import (
    SteamParseClient,
    Game,
    Currency,
    DictionaryKey,
    TrackedItemsQuery,
    ItemInfoQuery,
    ItemDictionaryQuery,
    TrackItemBody,
    HistogramQuery,
    PriceHistoryQuery,
)


async def demo():
    async with SteamParseClient(
        base_url="http://65.109.143.76:5000",
        bearer_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXJ2aWNlIjoiZ2VuYSIsImp0aSI6ImEyZjU4ZDMwLTFkODgtNDIxNy04MzFlLTdjOGFlOGIwZTc2NiIsImV4cCI6MTg0NjgzMzA0NSwiaXNzIjoic3RlYW0ifQ.QmClV0bapTS-01Px0OXb2ZPGNj5ktCBp9I8q-b5AC-0",
    ) as client:
        # 1) Все курсы
        currencies = await client.list_currency_rates()
        logger.info("currencies: {}", currencies.model_dump())

        # 2) Курс конкретной валюты
        usd = await client.get_currency_rate(Currency.USD)
        logger.info("currency USD: {}", usd.model_dump())

        # 3) Трекаемые предметы
        tracked = await client.get_tracked_items(
            TrackedItemsQuery(game=Game.CSGO, page=1, page_size=20)
        )
        logger.info("tracked: {}", tracked.model_dump())

        # 4) Информация о предмете
        item = await client.get_item(
            ItemInfoQuery(
                hash_name="AK-47 | Redline (Field-Tested)",
                game=Game.CSGO,
            )
        )
        logger.info("item: {}", item.model_dump())

        # 5) Словарь предметов по ключу
        dictionary = await client.get_item_dictionary(
            ItemDictionaryQuery(key=DictionaryKey.average_price_1d.value, game=Game.CSGO)
        )
        logger.info("dictionary: {}", str(dictionary.model_dump())[:150])

        # 6) Начать трекинг предмета
        track = await client.track_item(
            TrackItemBody(hash_name="AK-47 | Redline (Field-Tested)", game=Game.CSGO)
        )
        logger.info("track: {}", track.model_dump())

        # # 7) Снять предмет с трекинга
        # untrack = await client.untrack_item(
        #     TrackItemBody(hash_name="AK-47 | Redline (Field-Tested)", game=Game.CSGO)
        # )
        # logger.info("untrack: {}", untrack.model_dump())

        # 8) Гистограмма ордеров
        hist = await client.get_histogram(
            HistogramQuery(
                market_hash_name="AK-47 | Redline (Field-Tested)",
                game=Game.CSGO,
                currency=Currency.USD,
                force_refresh=False,
            )
        )
        logger.info("hist: {}", str(hist.model_dump())[:150])

        # 9) История цен
        price_history = await client.get_price_history(
            PriceHistoryQuery(
                market_hash_name="AK-47 | Redline (Field-Tested)",
                game=Game.CSGO,
                currency=Currency.USD,
                force_refresh=False,
            )
        )
        logger.info("price_history: {}", str(price_history.model_dump())[:150])


if __name__ == "__main__":
    asyncio.run(demo())
