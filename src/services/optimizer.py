from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from src.models import (
    PricedItem,
    Selection,
)


class OptimizerService:
    def __init__(self, overfill: float = 0.50):
        self._overfill = overfill

    @staticmethod
    def _to_cents(value: float) -> int:
        dec = Decimal(str(value))
        return max(0, int((dec * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)))

    @staticmethod
    def _sum_cents(items: list[PricedItem]) -> int:
        return sum(OptimizerService._to_cents(it.net_price) for it in items)

    @staticmethod
    def _reconstruct(
        parents: list[tuple[int, int] | None],
        best: int,
        items: list[PricedItem],
    ) -> list[PricedItem]:
        indices = []
        curr = best
        while curr and parents[curr]:
            prev, idx = parents[curr]
            indices.append(idx)
            curr = prev
        indices.reverse()
        return [items[i] for i in indices]

    def find_optimal_subset(
        self,
        items: list[PricedItem],
        target: float,
    ) -> Selection | None:
        if not items:
            return None

        prices = [self._to_cents(it.net_price) for it in items]
        target_cents = self._to_cents(target)

        over_cents = self._to_cents(self._overfill)
        capacity = min(sum(prices), target_cents + over_cents)

        reachable = bytearray(capacity + 1)
        min_count = [len(items) + 1] * (capacity + 1)
        parents: list[tuple[int, int] | None] = [None] * (capacity + 1)
        reachable[0] = 1
        min_count[0] = 0

        for idx, price in enumerate(prices):
            if price == 0 or price > capacity:
                continue
            for s in range(capacity, price - 1, -1):
                if reachable[s - price]:
                    cnt = min_count[s - price] + 1
                    if not reachable[s] or cnt < min_count[s]:
                        reachable[s] = 1
                        min_count[s] = cnt
                        parents[s] = (s - price, idx)

        best = None
        for s in range(target_cents, capacity + 1):
            if reachable[s]:
                best = s
                break

        if best is None:
            return None

        selected = self._reconstruct(parents, best, items)
        total = self._sum_cents(selected) / 100.0

        return Selection(
            total=total,
            items=selected,
            item_count=len(selected),
        )

    def find_best_sender(
        self,
        sender_items: dict[str, list[PricedItem]],
        target: float,
    ) -> tuple[str, Selection] | None:
        candidates = [
            (sender, sel)
            for sender, items in sender_items.items()
            if (sel := self.find_optimal_subset(items, target))
        ]
        
        if not candidates:
            return None
        
        def score(selection: Selection) -> float:
            over = max(0.0, selection.total - target)
            return -over * 1e6 - selection.item_count * 1e3 - selection.total
        
        return max(candidates, key=lambda x: score(x[1]))
