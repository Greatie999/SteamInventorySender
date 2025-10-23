import asyncio
from sys import exit

from loguru import logger

from src.config import Config
from src.orchestrator import TradeOrchestrator
from src.services import (
    DataAccessService,
    SteamService,
    SteamParseService,
    TradePlanningService,
    OptimizerService,
    ConsoleUI,
)


class Program:
    def __init__(self):
        ConsoleUI.clear_screen()
        ConsoleUI.set_title("SteamInventorySender")

        try:
            self._config = Config.from_file()
            self._senders = DataAccessService.get_senders()
            self._acceptors = DataAccessService.get_acceptors()
            self._proxies = DataAccessService.get_proxies()

            logger.info(
                f"Configuration loaded | "
                f"senders={len(self._senders)} | "
                f"acceptors={len(self._acceptors)} | "
                f"proxies={self._proxies.qsize()}"
            )
        except Exception as ex:
            logger.exception(ex)
            input("Press Enter to exit...")
            exit(1)

    def run(self):
        logger.info("Starting trade distribution process")

        steam_service = SteamService()
        steamparse_service = SteamParseService(
            base_url=self._config.steam_parse.url,
            bearer_token=self._config.steam_parse.bearer_token,
        )
        optimizer = OptimizerService(overfill=self._config.trade_settings.overfill)
        trade_planning = TradePlanningService(optimizer=optimizer)

        orchestrator = TradeOrchestrator(
            config=self._config,
            senders=self._senders,
            acceptors=self._acceptors,
            steam_service=steam_service,
            steamparse_service=steamparse_service,
            trade_planning=trade_planning,
            proxies=self._proxies,
        )

        try:
            asyncio.run(orchestrator.execute())
        except KeyboardInterrupt:
            logger.warning("Process interrupted by user")
        except Exception as ex:
            logger.exception(ex)
        finally:
            logger.info("Process completed")
            input("Press Enter to exit...")


if __name__ == "__main__":
    Program().run()
