from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from loguru import logger

from src.exceptions import TargetNotReachable
from src.models import (
    PricedItem,
    Selection,
)
from src.services.optimizer import OptimizerService
from src.steam import Item


class TradePlanningService:
    def __init__(self, optimizer: OptimizerService):
        self._optimizer = optimizer

    @staticmethod
    def _to_cents(value: float) -> int:
        dec = Decimal(str(value))
        return max(0, int((dec * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)))

    @staticmethod
    def _filter_items(
        items: list[Item],
        whitelist: list[str] | None,
        blacklist: list[str] | None,
    ) -> list[Item]:
        if whitelist:
            items = [
                item for item in items
                if any(w.lower() in item.market_hash_name.lower() for w in whitelist)
            ]
        if blacklist:
            items = [
                item for item in items
                if not any(b.lower() in item.market_hash_name.lower() for b in blacklist)
            ]
        return items

    def build_price_index(
        self,
        inventories: list[tuple[str, list[Item]]],
        price_dict: dict[str, float],
        items_whitelist: list[str] | None = None,
        items_blacklist: list[str] | None = None,
    ) -> tuple[dict[str, list[PricedItem]], dict[str, dict[tuple[int, int], Item]]]:
        priced_by_sender = {}
        original_by_sender = {}

        for username, items in inventories:
            items = self._filter_items(items, items_whitelist, items_blacklist)
            original_by_sender[username] = {(it.asset_id, it.class_id): it for it in items}

            priced = [
                PricedItem.from_item(item, price)
                for item in items
                if (price := price_dict.get(item.market_hash_name, 0)) > 0
            ]
            priced.sort(key=lambda x: x.price, reverse=True)
            priced_by_sender[username] = priced

        return priced_by_sender, original_by_sender

    def estimate_value(self, items: list[PricedItem]) -> float:
        return sum(self._to_cents(it.net_price) for it in items) / 100.0

    def wallet_to_usd(
        self,
        wallet_total: float,
        wallet_currency: int | None,
        currency_rates: dict[int, float],
    ) -> float:
        if wallet_currency is None:
            return 0.0

        if wallet_currency == 1:
            return self._to_cents(wallet_total) / 100.0

        if wallet_currency in currency_rates:
            return self._to_cents(wallet_total / currency_rates[wallet_currency]) / 100.0

        logger.debug(f"No currency rate for {wallet_currency}, wallet=0 USD")
        return 0.0

    def select_best_sender(
        self,
        priced_by_sender: dict[str, list[PricedItem]],
        target: float,
    ) -> tuple[str, Selection]:
        result = self._optimizer.find_best_sender(priced_by_sender, target)
        if result is None:
            raise TargetNotReachable()
        return result

    @staticmethod
    def to_original(
        selection: Selection,
        original_index: dict[tuple[int, int], Item],
    ) -> list[Item]:
        return [
            original_index[(pi.asset_id, pi.class_id)]
            for pi in selection.items
            if (pi.asset_id, pi.class_id) in original_index
        ]

    @staticmethod
    def remove_used(
        priced_by_sender: dict[str, list[PricedItem]],
        original_by_sender: dict[str, dict[tuple[int, int], Item]],
        sender_name: str,
        selection: Selection,
    ) -> None:
        used = {(it.asset_id, it.class_id) for it in selection.items}
        priced_by_sender[sender_name] = [
            it for it in priced_by_sender[sender_name] if (it.asset_id, it.class_id) not in used
        ]
        for key in used:
            original_by_sender[sender_name].pop(key, None)

        logger.debug(f"{sender_name} | {len(priced_by_sender[sender_name])} items remaining")

