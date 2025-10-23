import asyncio
import random
from pathlib import Path

from loguru import logger

from src.exceptions import DatabaseError
from src.models import (
    Account,
    Proxy,
)


class DataAccessService:
    DATA_DIR = Path("data")
    
    @staticmethod
    def _read_lines(filename: str) -> list[str]:
        try:
            return (DataAccessService.DATA_DIR / filename).read_text("utf-8").strip().split("\n")
        except FileNotFoundError:
            raise DatabaseError(f"File [{filename}] not found")
    
    @staticmethod
    def _write_lines(filename: str, lines: list[str]):
        (DataAccessService.DATA_DIR / filename).write_text("\n".join(lines) + "\n", "utf-8")
    
    @staticmethod
    def get_senders() -> list[Account]:
        logger.debug("Loading sender accounts from senders.txt")
        lines = DataAccessService._read_lines("senders.txt")
        accounts = []
        
        for line in lines:
            parts = line.split(":")
            if len(parts) != 6:
                raise DatabaseError(
                    f"Invalid sender format: {line}\n"
                    f"Expected: Username:Password:ProxyHost:ProxyPort:ProxyLogin:ProxyPassword"
                )
            
            username, password = parts[0], parts[1]
            proxy = Proxy.from_string(":".join(parts[2:6]))
            accounts.append(Account.create(username, password, proxy))
        
        logger.debug(f"Loaded {len(accounts)} sender accounts")
        return accounts
    
    @staticmethod
    def get_acceptors() -> list[Account]:
        logger.debug("Loading acceptor accounts from acceptors.txt")
        lines = DataAccessService._read_lines("acceptors.txt")
        accounts = []
        
        for line in lines:
            parts = line.split(":")
            if len(parts) != 2:
                raise DatabaseError(
                    f"Invalid acceptor format: {line}\n"
                    f"Expected: Username:Password"
                )
            username, password = parts
            accounts.append(Account.create(username, password))
        
        logger.debug(f"Loaded {len(accounts)} acceptor accounts")
        return accounts
    
    @staticmethod
    def remove_acceptor(account: Account):
        try:
            lines = DataAccessService._read_lines("acceptors.txt")
            lines.remove(f"{account.username}:{account.password}")
            DataAccessService._write_lines("acceptors.txt", lines)
        except (FileNotFoundError, ValueError):
            pass
    
    @staticmethod
    def get_proxies() -> asyncio.Queue[Proxy]:
        logger.debug("Loading proxy servers from proxies.txt")
        lines = DataAccessService._read_lines("proxies.txt")
        random.shuffle(lines)
        
        proxies = asyncio.Queue()
        for line in lines:
            try:
                proxies.put_nowait(Proxy.from_string(line))
            except ValueError:
                raise DatabaseError(
                    f"Invalid proxy format: {line}\n"
                    f"Expected: Host:Port:Username:Password"
                )
        
        logger.debug(f"Loaded {proxies.qsize()} proxies")
        return proxies
