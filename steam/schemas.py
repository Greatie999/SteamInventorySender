from pydantic import (
    BaseModel,
    Field
)


class Params(BaseModel):
    nonce: str
    auth: str


class TransferInfoItem(BaseModel):
    url: str
    params: Params


class FinalizeLoginStatus(BaseModel):
    steamID: str
    redir: str
    transfer_info: list[TransferInfoItem]
    primary_domain: str


class LoginResult(BaseModel):
    client_id: int
    refresh_token: str
    access_token: str


class Item(BaseModel):
    name: str
    market_hash_name: str
    app_id: int
    context_id: int
    amount: int
    asset_id: int
    class_id: int

    @property
    def trade_asset(self):
        return {
            "appid": self.app_id,
            "contextid": str(self.context_id),
            "amount": self.amount,
            "assetid": str(self.asset_id)
        }


class SendOfferResponse(BaseModel):
    trade_offer_id: int = Field(alias="tradeofferid")
    needs_mobile_confirmation: bool


class AcceptOfferResponse(BaseModel):
    trade_id: int = Field(alias="tradeid")


class MobileConfirmation(BaseModel):
    confirmation_id: int
    confirmation_key: int
    trade_offer_id: int
