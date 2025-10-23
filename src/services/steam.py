from pathlib import Path

from loguru import logger

from src.models import (
    Account,
    TradeCredentialsCache,
)
from src.steam import (
    Item,
    SteamAccount,
)


class SteamService:
    def __init__(self):
        self._sessions: dict[str, SteamAccount] = {}
        self._creds = TradeCredentialsCache.load(path=Path("data/trade.json"))

    async def close_session(self, account: Account) -> None:
        session = self._sessions.pop(account.username, None)
        if session:
            await session.close()
            logger.debug(f"{account.username} | Session closed")

    async def _session(self, account: Account) -> SteamAccount:
        if account.username in self._sessions:
            return self._sessions[account.username]

        logger.debug(f"{account.username} | Logging in to Steam")
        session = SteamAccount(
            username=account.username,
            password=account.password,
            shared_secret=account.secrets.shared_secret,
            identity_secret=account.secrets.identity_secret,
            proxy=account.proxy.to_format() if account.proxy else None,
        )
        await session.login()
        self._sessions[account.username] = session
        logger.debug(f"{account.username} | Logged in successfully")
        return session

    async def fetch_inventory(
        self,
        account: Account,
        app_id: int,
        context_id: int,
    ) -> list[Item]:
        session = await self._session(account)
        return await session.fetch_inventory(app_id, context_id)

    async def fetch_inventory_and_wallet(
        self,
        account: Account,
        app_id: int,
        context_id: int,
    ) -> tuple[list[Item], float, int]:
        session = await self._session(account)
        items = await session.fetch_inventory(app_id, context_id)
        wallet = await session.get_wallet()
        return items, float(wallet.total_balance), int(wallet.currency)

    async def get_trade_credentials(self, account: Account) -> tuple[int, str]:
        if cached := self._creds.get(account.username):
            logger.debug(f"{account.username} | Using cached trade credentials")
            return cached
        
        logger.debug(f"{account.username} | Fetching trade credentials")
        session = await self._session(account)
        token = await session.get_trade_token()
        self._creds.set(account.username, session.steam_id64, token)
        logger.debug(f"{account.username} | Trade credentials cached")
        return session.steam_id64, token

    async def send_trade_offer(
        self,
        sender: Account,
        items: list[Item],
        partner_steam_id64: int,
        partner_trade_token: str,
    ) -> int:
        session = await self._session(sender)
        return await session.send_trade_offer(
            partner_steam_id64=partner_steam_id64,
            partner_trade_token=partner_trade_token,
            me=items,
            them=[],
        )

    async def accept_trade_offer(
        self,
        acceptor: Account,
        trade_offer_id: int,
        partner_steam_id64: int,
    ) -> None:
        session = await self._session(acceptor)
        await session.accept_trade_offer(
            trade_offer_id=trade_offer_id,
            partner_steam_id64=partner_steam_id64,
        )
