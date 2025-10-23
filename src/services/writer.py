from pathlib import Path

from loguru import logger

from src.models import Account
from src.services.repository import DataAccessService


class ResultsWriter:
    def __init__(
        self,
        results_dir: Path = Path("results")
    ):
        self._results_dir = results_dir
        self._success_file = results_dir / "success.txt"
        self._error_file = results_dir / "error.txt"
        self._results_dir.mkdir(exist_ok=True)
    
    def write_success(self, account: Account):
        logger.success(f"{account.username} | Trade offer processed successfully")
        with self._success_file.open("a", encoding="utf-8") as f:
            f.write(f"{account.username}:{account.password}\n")
        DataAccessService.remove_acceptor(account)
    
    def write_error(
        self,
        account: Account,
        message: str = "Unable to process trade offer",
    ):
        logger.error(f"{account.username} | {message}")
        with self._error_file.open("a", encoding="utf-8") as f:
            f.write(f"{account.username}:{account.password}\n")
        DataAccessService.remove_acceptor(account)
