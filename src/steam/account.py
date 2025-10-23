import asyncio
import json
import re
from time import time

from bs4 import BeautifulSoup
from httpx import AsyncClient
from contextlib import suppress
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception,
)

from .enums import (
    SteamURL,
    Currency,
)
from .exceptions import (
    AuthorizationError,
    SetTokenError,
    UnknownInventoryError,
    PrivateInventoryError,
    NullInventoryError,
    InvalidAuthenticatorError,
    InvalidConfirmationPageError,
    MobileConfirmationError,
    NotFoundMobileConfirmationError,
    TradeError,
    TradeLinkError,
    ProfileSettingsError,
    TradeBanError,
    AccountOverflowError,
    TradeOffersLimitError,
    GetWalletError,
)
from .pb.enums_pb2 import k_ESessionPersistence_Persistent
from .pb.steammessages_auth.steamclient_pb2 import (
    CAuthentication_BeginAuthSessionViaCredentials_Request,
    CAuthentication_BeginAuthSessionViaCredentials_Response,
    CAuthentication_GetPasswordRSAPublicKey_Request,
    CAuthentication_GetPasswordRSAPublicKey_Response,
    CAuthentication_UpdateAuthSessionWithSteamGuardCode_Request,
    CAuthentication_UpdateAuthSessionWithSteamGuardCode_Response,
    EAuthSessionGuardType,
    k_EAuthSessionGuardType_DeviceCode,
    k_EAuthTokenPlatformType_WebBrowser,
    CAuthentication_PollAuthSessionStatus_Request,
    CAuthentication_PollAuthSessionStatus_Response,
)
from .schemas import (
    FinalizeLoginStatus,
    TransferInfoItem,
    LoginResult,
    Item,
    MobileConfirmation,
    SendOfferResponse,
    AcceptOfferResponse,
    Wallet,
)
from .utils import (
    generate_code,
    generate_sessionid,
    get_confirmation_hash,
    pbmessage_to_request,
    get_website_id_by_platform,
    generate_device_id,
    encrypt_password,
)


class SteamAccount:
    def __init__(
        self,
        username: str,
        password: str,
        shared_secret: str,
        identity_secret: str,
        *,
        proxy: str | None = None,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/141.0.0.0 Safari/537.36"
        ),
    ):
        self._username: str = username
        self._password: str = password
        self._shared_secret: str = shared_secret
        self._identity_secret: str = identity_secret
        self._device_id: str | None = None
        self._platform = k_EAuthTokenPlatformType_WebBrowser
        self._logged_in: bool = False
        self._steam_id64: int | None = None
        self._session_id: str | None = None
        self._trade_token: str | None = None
        self._currency: Currency | None = None
        self._timeout: float = 20.0
        self._user_agent = user_agent
        self._client = AsyncClient(
            headers={"User-Agent": self._user_agent},
            timeout=self._timeout,
            proxy=proxy,
            follow_redirects=True,
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    @property
    def shared_secret(self) -> str:
        return self._shared_secret

    @property
    def identity_secret(self) -> str:
        return self._identity_secret

    @property
    def device_id(self) -> str | None:
        return self._device_id

    @property
    def logged_in(self) -> bool:
        return self._logged_in

    @property
    def steam_id64(self) -> int | None:
        return self._steam_id64

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def trade_token(self) -> str | None:
        return self._trade_token

    @property
    def currency(self) -> Currency | None:
        return self._currency

    async def reset(self, proxy: str | None = None):
        with suppress(Exception):
            await self.close()
        self._client = AsyncClient(
            headers={"User-Agent": self._user_agent},
            timeout=self._timeout,
            proxy=proxy,
            follow_redirects=True,
        )
        self._logged_in = False
        self._steam_id64 = None
        self._session_id = None
        self._trade_token = None
        self._currency = None
        self._device_id = None

    async def _poll_auth_session_status(
        self,
        client_id: int,
        request_id: bytes,
    ) -> CAuthentication_PollAuthSessionStatus_Response:
        message = CAuthentication_PollAuthSessionStatus_Request(
            client_id=client_id,
            request_id=request_id,
        )
        response = await self._client.post(
            url=f"{SteamURL.API.value}/IAuthenticationService/PollAuthSessionStatus/v1",
            data={"input_protobuf_encoded": pbmessage_to_request(message)},
        )
        if not response.status_code == 200:
            raise AuthorizationError
        return CAuthentication_PollAuthSessionStatus_Response.FromString(response.content)

    async def _finalize_login(self, refresh_token: str) -> FinalizeLoginStatus:
        data = {
            "nonce": refresh_token,
            "sessionid": self._session_id,
            "redir": f"{SteamURL.COMMUNITY.value}/login/home/?goto=",
        }
        response = await self._client.post(
            url=f"{SteamURL.LOGIN.value}/jwt/finalizelogin",
            data=data,
        )
        data = response.json()
        success = data.get("success")
        if success is False:
            raise AuthorizationError
        return FinalizeLoginStatus.model_validate(data)

    async def _set_tokens(self, transfer_info: list[TransferInfoItem]):
        for token in transfer_info:
            await self._set_token(
                url=token.url,
                nonce=token.params.nonce,
                auth=token.params.auth,
            )

    async def _set_token(self, url: str, nonce: str, auth: str):
        data = {
            "nonce": nonce,
            "auth": auth,
            "steamID": self._steam_id64,
        }
        response = await self._client.post(
            url=url,
            data=data,
        )
        data = response.json()
        result = data.get("result")
        if not result == 1:
            raise SetTokenError

    async def _getrsakey(
        self,
    ) -> CAuthentication_GetPasswordRSAPublicKey_Response:
        message = CAuthentication_GetPasswordRSAPublicKey_Request(account_name=self._username)
        response = await self._client.get(
            url=f"{SteamURL.API.value}/IAuthenticationService/GetPasswordRSAPublicKey/v1",
            params={"input_protobuf_encoded": pbmessage_to_request(message)},
        )
        return CAuthentication_GetPasswordRSAPublicKey_Response.FromString(response.content)

    async def _begin_auth_session_via_credentials(
        self,
        password: str,
        timestamp: int,
    ) -> CAuthentication_BeginAuthSessionViaCredentials_Response:
        message = CAuthentication_BeginAuthSessionViaCredentials_Request(
            account_name=self._username,
            encrypted_password=password,
            encryption_timestamp=timestamp,
            remember_login=True,
            platform_type=self._platform,
            website_id=get_website_id_by_platform(self._platform),
            persistence=k_ESessionPersistence_Persistent,
        )
        response = await self._client.post(
            url=f"{SteamURL.API.value}/IAuthenticationService/BeginAuthSessionViaCredentials/v1",
            data={"input_protobuf_encoded": pbmessage_to_request(message)},
        )
        if not response.status_code == 200:
            raise AuthorizationError
        return CAuthentication_BeginAuthSessionViaCredentials_Response.FromString(response.content)

    async def _update_auth_session_with_steam_guard(
        self,
        client_id: int,
        steamid: int,
        code: str,
        code_type: EAuthSessionGuardType,
    ) -> CAuthentication_UpdateAuthSessionWithSteamGuardCode_Response:
        message = CAuthentication_UpdateAuthSessionWithSteamGuardCode_Request(
            client_id=client_id,
            steamid=steamid,
            code=code,
            code_type=code_type,
        )
        response = await self._client.post(
            url=f"{SteamURL.API.value}/IAuthenticationService/UpdateAuthSessionWithSteamGuardCode/v1",
            data={"input_protobuf_encoded": pbmessage_to_request(message)},
        )
        if not response.status_code == 200:
            raise AuthorizationError
        return CAuthentication_UpdateAuthSessionWithSteamGuardCode_Response.FromString(
            response.content
        )

    async def _confirm_authorization(
        self,
        session: CAuthentication_BeginAuthSessionViaCredentials_Response,
    ):
        if (
            not next(iter(session.allowed_confirmations)).confirmation_type
            == k_EAuthSessionGuardType_DeviceCode
        ):
            raise AuthorizationError("Unsupported confirmation type")

        await self._update_auth_session_with_steam_guard(
            client_id=session.client_id,
            steamid=session.steamid,
            code=generate_code(self._shared_secret),
            code_type=k_EAuthSessionGuardType_DeviceCode,
        )
        return

    def _transfer_cookie(self, name: str, value: str):
        for domain in ["steamcommunity.com", "help.steampowered.com"]:
            self._client.cookies.set(name, value, domain=domain)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(31),
        retry=retry_if_exception(
            lambda e: not (
                re.search(r"Already logged in", str(e))
                or re.search(r"Unsupported confirmation type", str(e))
            )
        ),
        reraise=True,
    )
    async def login(self) -> LoginResult:
        if self._logged_in:
            raise AuthorizationError("Already logged in")

        self._session_id = generate_sessionid()
        self._transfer_cookie("sessionid", self._session_id)

        keys = await self._getrsakey()
        encrypted_password = encrypt_password(self._password, keys)

        session = await self._begin_auth_session_via_credentials(
            password=encrypted_password,
            timestamp=keys.timestamp,
        )
        if session.allowed_confirmations:
            await self._confirm_authorization(session=session)

        session_status = await self._poll_auth_session_status(
            client_id=session.client_id,
            request_id=session.request_id,
        )

        tokens = await self._finalize_login(refresh_token=session_status.refresh_token)
        self._steam_id64 = int(tokens.steamID)
        await self._set_tokens(tokens.transfer_info)
        self._device_id = generate_device_id(self._steam_id64)

        self._logged_in = True
        return LoginResult(
            client_id=session.client_id,
            refresh_token=session_status.refresh_token,
            access_token=session_status.access_token,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(10),
        reraise=True,
    )
    async def _get_inventory_page(
        self,
        app_id: int,
        context_id: int,
        start: int,
    ) -> dict:
        params = {
            "trading": 1,
            "l": "english",
            "start": start,
        }
        response = await self._client.get(
            url=f"{SteamURL.COMMUNITY.value}/profiles/{self._steam_id64}/inventory/json/{app_id}/{context_id}/",
            params=params,
        )
        if response.text == "null":
            raise NullInventoryError(steam_id=self._steam_id64, app_id=app_id)
        return response.json()

    async def fetch_inventory(
        self,
        app_id: int,
        context_id: int,
    ) -> list[Item]:
        inventory = {
            "rgInventory": {},
            "rgDescriptions": {},
        }

        start = 0
        while True:
            response = await self._get_inventory_page(app_id, context_id, start)
            if not response["success"]:
                error = response.get("Error", "")
                if not error:
                    raise UnknownInventoryError(steam_id=self.steam_id64, app_id=app_id)
                if error == "This profile is private.":
                    raise PrivateInventoryError(steam_id=self.steam_id64, app_id=app_id)

            inventory["rgInventory"].update(response["rgInventory"])
            inventory["rgDescriptions"].update(response["rgDescriptions"])
            if response.get("more"):
                start = response["more_start"]
                await asyncio.sleep(30)
            else:
                break

        items = []
        if not inventory.get("rgInventory"):
            return items
        for asset in inventory.get("rgInventory").values():
            class_id = asset["classid"]
            description = next(
                (x for x in inventory.get("rgDescriptions").values() if x["classid"] == class_id),
                None,
            )
            name = description["name"]
            market_hash_name = description["market_hash_name"]
            amount = asset["amount"]
            asset_id = asset["id"]
            class_id = asset["classid"]
            items.append(
                Item(
                    name=name,
                    market_hash_name=market_hash_name,
                    app_id=int(app_id),
                    context_id=int(context_id),
                    amount=int(amount),
                    asset_id=int(asset_id),
                    class_id=int(class_id),
                )
            )
        return items

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(10),
        reraise=True,
    )
    async def get_trade_token(self) -> str:
        headers = {
            "Referer": f"{SteamURL.COMMUNITY.value}/profiles/{self._steam_id64}/tradeoffers/"
        }
        cookies = {
            "Steam_Language": "english",
        }
        response = await self._client.get(
            url=f"{SteamURL.COMMUNITY.value}/profiles/{self._steam_id64}/tradeoffers/privacy",
            headers=headers,
            cookies=cookies,
        )
        soup = BeautifulSoup(response.text, "html.parser")
        link = soup.find("input", {"id": "trade_offer_access_url"}).attrs["value"]
        token = link.split("&token=")[-1]
        self._trade_token = token
        return token

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(10),
        reraise=True,
    )
    async def get_mobile_confirmations(self) -> list[MobileConfirmation]:
        server_time = int(time())
        confirmation_hash = get_confirmation_hash(
            identity_secret=self._identity_secret,
            tag="conf",
            server_time=server_time,
        )
        headers = {
            "X-Requested-With": "com.valvesoftware.android.steam.community",
        }
        cookies = {
            "Steam_Language": "english",
        }
        params = {
            "p": self._device_id,
            "a": self._steam_id64,
            "k": confirmation_hash,
            "t": server_time,
            "m": "android",
            "tag": "conf",
        }
        response = await self._client.get(
            url=f"{SteamURL.COMMUNITY.value}/mobileconf/getlist",
            headers=headers,
            cookies=cookies,
            params=params,
        )
        if "Invalid authenticator" in response.text:
            raise InvalidAuthenticatorError
        if "There was a problem loading the confirmations page" in response.text:
            raise InvalidConfirmationPageError

        confirmations = []
        raw_confirmations = response.json()["conf"]
        for confirmation in raw_confirmations:
            confirmations.append(
                MobileConfirmation(
                    confirmation_id=int(confirmation["id"]),
                    confirmation_key=int(confirmation["nonce"]),
                    trade_offer_id=int(confirmation["creator_id"]),
                )
            )
        return confirmations

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(10),
        reraise=True,
    )
    async def mobile_confirm(self, confirmation: MobileConfirmation):
        server_time = int(time())
        confirmation_hash = get_confirmation_hash(
            identity_secret=self._identity_secret,
            tag="allow",
            server_time=server_time,
        )
        params = {
            "op": "allow",
            "p": self._device_id,
            "a": self._steam_id64,
            "k": confirmation_hash,
            "t": server_time,
            "m": "android",
            "tag": "allow",
            "cid": confirmation.confirmation_id,
            "ck": confirmation.confirmation_key,
        }
        response = await self._client.get(
            url=f"{SteamURL.COMMUNITY.value}/mobileconf/ajaxop",
            params=params,
        )
        success = response.json()["success"]
        if success is not True:
            raise MobileConfirmationError

    async def mobile_confirm_by_trade_offer_id(self, trade_offer_id: int):
        confirmations = await self.get_mobile_confirmations()
        for confirmation in confirmations:
            if confirmation.trade_offer_id == trade_offer_id:
                return await self.mobile_confirm(confirmation)
        raise NotFoundMobileConfirmationError

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(10),
        reraise=True,
    )
    async def send_trade_offer(
        self,
        partner_steam_id64: int,
        partner_trade_token: str,
        me: list[Item] = None,
        them: list[Item] = None,
    ) -> int:
        data = {
            "sessionid": self._session_id,
            "serverid": 1,
            "partner": partner_steam_id64,
            "tradeoffermessage": "",
            "json_tradeoffer": json.dumps(
                {
                    "newversion": True,
                    "version": 2,
                    "me": {
                        "assets": ([x.trade_asset for x in me] if me is not None else []),
                        "currency": [],
                        "ready": False,
                    },
                    "them": {
                        "assets": ([x.trade_asset for x in them] if them is not None else []),
                        "currency": [],
                        "ready": False,
                    },
                }
            ),
            "captcha": "",
            "trade_offer_create_params": json.dumps(
                {"trade_offer_access_token": partner_trade_token}
            ),
        }
        response = await self._client.post(
            url=f"{SteamURL.COMMUNITY.value}/tradeoffer/new/send",
            data=data,
            headers={"Referer": f"{SteamURL.COMMUNITY.value}/tradeoffer/new/"},
        )
        data = response.json()

        error = data.get("strError")
        if isinstance(error, str):
            mapping = [
                (
                    "Trade URL is no longer valid",
                    TradeLinkError,
                    "Trade URL is no longer valid",
                ),
                (
                    "is not available to trade",
                    ProfileSettingsError,
                    "Account is not available for trade offers",
                ),
                (
                    "they have a trade ban",
                    TradeBanError,
                    "User has a trade ban",
                ),
                (
                    "maximum number of items",
                    AccountOverflowError,
                    "Maximum number of items per account",
                ),
                (
                    "sent too many trade offers",
                    TradeOffersLimitError,
                    "Too many exchange offers have been sent",
                ),
            ]
            for needle, exc, message in mapping:
                if needle in error:
                    raise exc(message)
            raise TradeError(error)

        offer_response = SendOfferResponse.model_validate(data)
        if offer_response.needs_mobile_confirmation:
            await self.mobile_confirm_by_trade_offer_id(offer_response.trade_offer_id)
        return offer_response.trade_offer_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(10),
        reraise=True,
    )
    async def accept_trade_offer(
        self,
        trade_offer_id: int,
        partner_steam_id64: int,
    ) -> AcceptOfferResponse:
        response = await self._client.post(
            url=f"{SteamURL.COMMUNITY.value}/tradeoffer/{trade_offer_id}/accept",
            data={
                "sessionid": self._session_id,
                "serverid": "1",
                "tradeofferid": trade_offer_id,
                "partner": partner_steam_id64,
                "captcha": "",
            },
            headers={"Referer": f"{SteamURL.COMMUNITY.value}/tradeoffer/{trade_offer_id}/"},
        )
        return AcceptOfferResponse.model_validate(response.json())

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(10),
        reraise=True,
    )
    async def get_wallet(self) -> Wallet:
        response = await self._client.get(
            url=f"{SteamURL.COMMUNITY.value}/market/",
            cookies={"Steam_Language": "english"},
        )
        if not response.status_code == 200:
            raise GetWalletError

        match = re.search(r"var g_rgWalletInfo = (.*);", response.text)
        if match is None:
            raise GetWalletError

        wallet = Wallet.model_validate_json(match.group(1))
        self._currency = wallet.currency
        return wallet
