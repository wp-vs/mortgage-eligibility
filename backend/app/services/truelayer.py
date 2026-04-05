import logging
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SANDBOX_AUTH_URL = "https://auth.truelayer-sandbox.com"
SANDBOX_API_URL = "https://api.truelayer-sandbox.com"
PROD_AUTH_URL = "https://auth.truelayer.com"
PROD_API_URL = "https://api.truelayer.com"


class TrueLayerService:
    def __init__(self):
        if settings.truelayer_sandbox:
            self.auth_url = SANDBOX_AUTH_URL
            self.api_url = SANDBOX_API_URL
        else:
            self.auth_url = PROD_AUTH_URL
            self.api_url = PROD_API_URL

    def get_auth_url(self, connection_id: int) -> str:
        params = {
            "response_type": "code",
            "client_id": settings.truelayer_client_id,
            "scope": "info accounts balance transactions",
            "redirect_uri": settings.truelayer_redirect_uri,
            "providers": "uk-ob-all uk-oauth-all",
            "state": str(connection_id),
        }
        return f"{self.auth_url}/?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.auth_url}/connect/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.truelayer_client_id,
                    "client_secret": settings.truelayer_client_secret,
                    "redirect_uri": settings.truelayer_redirect_uri,
                    "code": code,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_accounts(self, access_token: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/data/v1/accounts",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])

    async def get_transactions(
        self, access_token: str, account_id: str | None = None
    ) -> list[dict]:
        async with httpx.AsyncClient() as client:
            # If no account_id, get the first account
            if not account_id:
                accounts = await self.get_accounts(access_token)
                if not accounts:
                    return []
                account_id = accounts[0]["account_id"]

            response = await client.get(
                f"{self.api_url}/data/v1/accounts/{account_id}/transactions",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
