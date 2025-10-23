from src.models import (
    Account,
    PricedItem,
)

from src.services import (
    ConsoleUI,
    ProgressTracker,
    ResultsWriter,
)


class ResultsService:
    def __init__(self, total_acceptors: int):
        self._tracker = ProgressTracker(total_acceptors)
        self._writer = ResultsWriter()
    
    def success(self, account: Account):
        self._tracker.increment_success()
        self._writer.write_success(account)
        ConsoleUI.update_title(self._tracker.get_stats())
    
    def error(self, account: Account, message: str = "Unable to process trade offer"):
        self._tracker.increment_error()
        self._writer.write_error(account, message)
        ConsoleUI.update_title(self._tracker.get_stats())
    
    def update_balance(self, priced_by_sender: dict[str, list[PricedItem]]):
        total = sum(
            sum(item.net_price for item in items)
            for items in priced_by_sender.values()
        )
        self._tracker.set_balance(total)
        ConsoleUI.update_title(self._tracker.get_stats())
