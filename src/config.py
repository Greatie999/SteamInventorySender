import sys
from pathlib import Path

from pydantic import (
    BaseModel,
    Field,
)

from src.exceptions import ConfigError


class ProgramSettings(BaseModel):
    perform_trade_offer_attempts: int = Field(alias="PerformTradeOfferAttempts", ge=1, le=10)
    send_trades_delay: int = Field(alias="SendTradesDelay", ge=1)


class SteamParseSettings(BaseModel):
    url: str = Field(alias="URL")
    bearer_token: str = Field(alias="Token")


class TradeSettings(BaseModel):
    app_id: int = Field(alias="AppID", default=730)
    context_id: int = Field(alias="ContextID", default=2)
    target: float = Field(alias="Target")
    overfill: float = Field(alias="MaxOverfill", default=0.50)
    count_acceptor_inventory: bool = Field(alias="CountAcceptorCS2Inventory", default=True)
    count_acceptor_wallet: bool = Field(alias="CountAcceptorWallet", default=True)
    items_whitelist: list[str] | None = Field(alias="ItemsWhitelist", default=None)
    items_blacklist: list[str] | None = Field(alias="ItemsBlacklist", default=None)


class Config(BaseModel):
    program_settings: ProgramSettings = Field(alias="ProgramSettings")
    trade_settings: TradeSettings = Field(alias="TradeSettings")
    steam_parse: SteamParseSettings = Field(alias="SteamParse")

    @classmethod
    def from_file(cls) -> "Config":
        try:
            return Config.model_validate_json(
                json_data=Path("data/config.json").read_text("utf-8")
            )
        except FileNotFoundError:
            raise ConfigError("Config file [config.json] not found")
        except Exception as e:
            raise ConfigError(f"Error reading config: {e}")


logger_config = {
    "handlers": [
        {
            "sink": sys.stdout,
            "colorize": True,
            "level": "DEBUG",
            "format": "<bold>{time:YYYY/MM/DD HH:mm:ss} <level>{message}</level></bold>",
            "enqueue": True,
        },
        {
            "sink": "log/debug.log",
            "level": "DEBUG",
            "format": "[{level}] {time:YYYY/MM/DD HH:mm:ss} | {message}",
            "enqueue": True,
        },
    ]
}
