import asyncio
import os
from typing import Optional

from steam.account import SteamAccount



async def main():
    username = "fomematttrenhandnico"
    password = "UAmqaRhkdY"
    shared_secret = "RFibj/kr4oNcsk7S4KFZCvU9qaY="
    identity_secret = "cB/3GVSECYI4OGPoM9b/Wref3nM="
    # proxy = "http://greaties_mail_ru:68ccfe4746@193.176.227.249:30013"
    proxy = None

    app_id = "730"
    context_id = "2"

    async with SteamAccount(
        username=username,
        password=password,
        shared_secret=shared_secret,
        identity_secret=identity_secret,
        proxy=proxy,
    ) as acc:
        print("Logging in...")
        login_result = await acc.login()
        print("Logged in, steam_id64=", acc.steam_id64)

        print("Fetching trade token...")
        token = await acc.get_trade_token()
        print("Trade token:", token)

        print("Fetching mobile confirmations list...")
        confirmations = await acc.get_mobile_confirmations()
        print("Confirmations count:", len(confirmations))

        if app_id and context_id:
            print("Fetching inventory page(s)...")
            items = await acc.fetch_inventory(int(app_id), int(context_id))
            print("Inventory items:", len(items))


if __name__ == "__main__":
    asyncio.run(main())


