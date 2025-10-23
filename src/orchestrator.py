import asyncio

from loguru import logger

from src.config import Config
from src.exceptions import TargetNotReachable
from src.models import (
    Account,
    PricedItem,
)
from src.services import (
    TradePlanningService,
    ResultsService,
    SteamService,
    SteamParseService,
)
from src.steam import Item
from src.steamparse import Game


class TradeOrchestrator:
    def __init__(
        self,
        config: Config,
        senders: list[Account],
        acceptors: list[Account],
        steam_service: SteamService,
        steamparse_service: SteamParseService,
        trade_planning: TradePlanningService,
        proxies: asyncio.Queue,
    ):
        self._config = config
        self._senders = senders
        self._senders_by_name = {s.username: s for s in senders}
        self._acceptors = acceptors
        self._steam = steam_service
        self._steamparse = steamparse_service
        self._planning = trade_planning
        self._results = ResultsService(len(acceptors))
        self._priced_by_sender: dict[str, list[PricedItem]] = {}
        self._original_by_sender: dict[str, dict[tuple[int, int], Item]] = {}
        self._price_dict: dict[str, float] = {}
        self._currency_rates: dict[int, float] = {}
        self._proxies = proxies

    async def _prepare_data(self) -> None:
        logger.info(f"Preparing data for {len(self._acceptors)} accounts")

        logger.debug("Checking sender inventories")
        tasks = [
            self._steam.fetch_inventory(
                account=s,
                app_id=self._config.trade_settings.app_id,
                context_id=self._config.trade_settings.context_id,
            )
            for s in self._senders
        ]
        inventories = await asyncio.gather(*tasks)
        inventories = [(s.username, inv) for s, inv in zip(self._senders, inventories)]

        for username, items in inventories:
            logger.debug(f"{username} | {len(items)} items available")
        logger.debug(f"All inventories checked")

        logger.debug("Getting current market prices")
        self._price_dict = await self._steamparse.fetch_price_dictionary(game=Game.CSGO)
        logger.debug(f"Market prices received | {len(self._price_dict)} items")

        self._priced_by_sender, self._original_by_sender = (
            self._planning.build_price_index(
                inventories=inventories,
                price_dict=self._price_dict,
                items_whitelist=self._config.trade_settings.items_whitelist,
                items_blacklist=self._config.trade_settings.items_blacklist,
            )
        )
        total_priced = sum(len(v) for v in self._priced_by_sender.values())
        logger.info(
            f"Ready to distribute {total_priced} items from "
            f"{len(self._priced_by_sender)} accounts"
        )

        self._results.update_balance(self._priced_by_sender)

        logger.debug("Getting currency exchange rates")
        self._currency_rates = await self._steamparse.fetch_currency_rates()
        await self._steamparse.close()
        logger.debug(f"Exchange rates received | {len(self._currency_rates)} currencies")

    async def _process_acceptor(self, acceptor: Account) -> None:
        ts = self._config.trade_settings
        attempts = self._config.program_settings.perform_trade_offer_attempts

        try:
            while attempts > 0:
                proxy = await self._proxies.get()
                try:
                    acceptor.proxy = proxy
                    await self._steam.close_session(acceptor)

                    items, wallet_total, wallet_currency = (
                        await self._steam.fetch_inventory_and_wallet(
                            account=acceptor,
                            app_id=ts.app_id,
                            context_id=ts.context_id,
                        )
                    )

                    items_value = 0.0
                    if ts.count_acceptor_inventory:
                        priced = [
                            PricedItem.from_item(it, price)
                            for it in items
                            if (price := self._price_dict.get(it.market_hash_name, 0)) > 0
                        ]
                        items_value = self._planning.estimate_value(priced)

                    wallet_usd = 0.0
                    if ts.count_acceptor_wallet:
                        wallet_usd = self._planning.wallet_to_usd(
                            wallet_total=wallet_total,
                            wallet_currency=wallet_currency,
                            currency_rates=self._currency_rates,
                        )

                    current = items_value + wallet_usd
                    logger.debug(
                        f"{acceptor.username} | inv={items_value:.2f} | "
                        f"wallet={wallet_usd:.2f} | "
                        f"current={current:.2f} | "
                        f"target={ts.target:.2f}"
                    )

                    if current >= ts.target:
                        logger.info(
                            f"{acceptor.username} | Already has target amount ${ts.target:.2f}"
                        )
                        self._results.success(acceptor)
                        return

                    missing = ts.target - current
                    sender_name, selection = self._planning.select_best_sender(
                        priced_by_sender=self._priced_by_sender,
                        target=missing,
                    )

                    sender = self._senders_by_name[sender_name]
                    logger.info(
                        f"{acceptor.username} | Sending {selection.item_count} items "
                        f"(${selection.total:.2f}) from {sender_name}"
                    )

                    chosen_items = self._planning.to_original(
                        selection=selection,
                        original_index=self._original_by_sender[sender_name]
                    )

                    partner_id, partner_token = await self._steam.get_trade_credentials(
                        account=acceptor
                    )
                    offer_id = await self._steam.send_trade_offer(
                        sender=sender,
                        items=chosen_items,
                        partner_steam_id64=partner_id,
                        partner_trade_token=partner_token,
                    )
                    logger.info(
                        f"{acceptor.username} | Trade offer #{offer_id} sent successfully"
                    )
                    await self._steam.accept_trade_offer(
                        acceptor=acceptor,
                        trade_offer_id=offer_id,
                        partner_steam_id64=partner_id,
                    )
                    logger.info(
                        f"{acceptor.username} | Trade offer #{offer_id} accepted successfully"
                    )
                    self._results.success(acceptor)
                    self._planning.remove_used(
                        priced_by_sender=self._priced_by_sender,
                        original_by_sender=self._original_by_sender,
                        sender_name=sender_name,
                        selection=selection,
                    )
                    self._results.update_balance(self._priced_by_sender)
                    return

                except Exception as ex:
                    if isinstance(ex, TargetNotReachable):
                        self._results.error(
                            account=acceptor,
                            message=f"Not enough items to reach target ${ts.target:.2f}"
                        )
                        return

                    attempts -= 1
                    if attempts > 0:
                        logger.warning(
                            f"{acceptor.username} | {ex.__class__.__name__} | "
                            f"Retrying ({attempts} attempts left)"
                        )
                        await asyncio.sleep(20)
                finally:
                    await self._proxies.put(proxy)

            self._results.error(acceptor)
        finally:
            await self._steam.close_session(acceptor)

    async def execute(self) -> None:
        try:
            await self._prepare_data()

            for acceptor in self._acceptors:
                await self._process_acceptor(acceptor)
                await asyncio.sleep(self._config.program_settings.send_trades_delay)
        finally:
            for sender in self._senders:
                await self._steam.close_session(sender)
