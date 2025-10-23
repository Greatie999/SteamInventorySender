class SteamError(Exception): ...


class AuthorizationError(SteamError): ...


class SetTokenError(AuthorizationError): ...


class InventoryError(SteamError):
    def __init__(self, steam_id: int, app_id: int):
        self.steam_id = steam_id
        self.app_id = app_id

    def __str__(self) -> str:
        return str(
            {
                "exception": self.__class__.__name__,
                "app_id": self.app_id,
                "steam_id": self.steam_id,
            }
        )


class NullInventoryError(InventoryError): ...


class PrivateInventoryError(InventoryError): ...


class UnknownInventoryError(InventoryError): ...


class TradeError(SteamError): ...


class SendOfferError(TradeError): ...


class SteamServerDownError(SendOfferError): ...


class TradeOffersLimitError(SendOfferError): ...


class AccountOverflowError(SendOfferError): ...


class TradeBanError(SendOfferError): ...


class ProfileSettingsError(SendOfferError): ...


class TradeLinkError(SendOfferError): ...


class MobileConfirmationError(SteamError): ...


class NotFoundMobileConfirmationError(MobileConfirmationError): ...


class InvalidAuthenticatorError(MobileConfirmationError): ...


class InvalidConfirmationPageError(MobileConfirmationError): ...


class GetWalletError(SteamError): ...
