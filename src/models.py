import json
from pathlib import Path

from pydantic import (
    BaseModel,
    Field,
    model_validator,
    ConfigDict,
)

from src.exceptions import DatabaseError


class PricedItem(BaseModel):
    market_hash_name: str
    app_id: int
    context_id: int
    asset_id: int
    class_id: int
    amount: int
    price: float
    fee_percent: float = 0.13
    net_price: float = 0.0

    @model_validator(mode="after")
    def _compute_net(self):
        self.net_price = self.price * max(0.0, 1.0 - self.fee_percent)
        return self

    @classmethod
    def from_item(cls, item, price: float) -> "PricedItem":
        return cls(
            market_hash_name=item.market_hash_name,
            app_id=item.app_id,
            context_id=item.context_id,
            asset_id=item.asset_id,
            class_id=item.class_id,
            amount=item.amount,
            price=price,
        )


class Selection(BaseModel):
    total: float
    items: list[PricedItem]
    item_count: int


class Proxy(BaseModel):
    host: str
    port: int
    username: str
    password: str

    def to_format(self) -> str:
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"

    @classmethod
    def from_string(cls, line: str) -> "Proxy":
        parts = line.split(":")
        if len(parts) != 4:
            raise ValueError(f"Invalid proxy format: {line}")
        host, port, username, password = parts
        return cls(
            host=host,
            port=int(port),
            username=username,
            password=password,
        )


class Secrets(BaseModel):
    shared_secret: str
    identity_secret: str

    @classmethod
    def load(cls, username: str, data_dir: Path = Path("data")) -> "Secrets":
        path = data_dir / "maFiles" / f"{username}.maFile"
        try:
            return cls(**json.loads(path.read_text("utf-8")))
        except FileNotFoundError:
            raise DatabaseError(f"Secrets file [{username}.maFile] not found")
        except Exception as ex:
            raise DatabaseError(f"Invalid secrets file [{username}.maFile]: {ex}")


class Account(BaseModel):
    username: str
    password: str
    secrets: Secrets
    proxy: Proxy | None = None

    @classmethod
    def create(
        cls,
        username: str,
        password: str,
        proxy: Proxy | None = None
    ) -> "Account":
        secrets = Secrets.load(username)
        return cls(
            username=username,
            password=password,
            secrets=secrets,
            proxy=proxy,
        )


class TradeCredentialsEntry(BaseModel):
    steam_id64: int
    token: str


class TradeCredentialsCache(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _path: Path | None = None
    data: dict[str, TradeCredentialsEntry] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "TradeCredentialsCache":
        """Загрузить кэш из файла"""
        p = Path(path)
        if p.exists():
            cache = cls.model_validate_json(p.read_text())
        else:
            cache = cls()
        cache._path = p
        return cache

    def get(self, username: str) -> tuple[int, str] | None:
        if entry := self.data.get(username):
            return entry.steam_id64, entry.token
        return None

    def set(
        self,
        username: str,
        steam_id64: int,
        token: str,
    ):
        self.data[username] = TradeCredentialsEntry(
            steam_id64=steam_id64,
            token=token,
        )
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(self.model_dump_json(indent=2, exclude={"_path"}))


class ProgressStats(BaseModel):
    progress: int
    total: int
    success: int
    errors: int
    balance: float
