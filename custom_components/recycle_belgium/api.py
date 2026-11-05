"""Asynchronous client for the Recycle! / Fost Plus public API."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_HEADERS


TIMEOUT = aiohttp.ClientTimeout(total=20)


class RecycleApiError(Exception):
    """Error communicating with the Recycle! API."""


def normalize(value: str) -> str:
    """Normalize a street name for strict comparison."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char for char in value if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]", "", value.casefold())


class RecycleClient:
    """Client for the public Recycle! API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def request_json(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Perform an HTTP request and return a JSON object."""
        url = f"{API_BASE_URL}/{path.lstrip('/')}"

        try:
            async with self._session.request(
                method,
                url,
                headers=API_HEADERS,
                timeout=TIMEOUT,
                **kwargs,
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)

        except aiohttp.ClientResponseError as exc:
            raise RecycleApiError(
                f"Erreur HTTP {exc.status} lors de l'appel à {path}."
            ) from exc
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise RecycleApiError(
                f"Erreur de communication avec l'API ({path}) : {exc}"
            ) from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise RecycleApiError(
                f"La réponse de {path} n'est pas un JSON valide."
            ) from exc

        if not isinstance(payload, dict):
            raise RecycleApiError(
                f"Format inattendu pour {path} : objet JSON attendu."
            )

        return payload

    async def find_zipcodes(
        self,
        postcode: str,
    ) -> list[dict[str, Any]]:
        """Find available postal codes."""
        payload = await self.request_json(
            "GET",
            "zipcodes",
            params={"q": postcode},
        )

        items = [
            item
            for item in payload.get("items", [])
            if item.get("available", True)
        ]

        if not items:
            raise RecycleApiError(
                f"Aucun code postal disponible trouvé pour {postcode}."
            )

        return items

    async def find_street(
        self,
        zipcode_id: str,
        street: str,
    ) -> dict[str, Any]:
        """Find a street using an exact normalized name match."""
        query = street.split(".")[-1].strip()

        payload = await self.request_json(
            "POST",
            "streets",
            params={
                "q": query,
                "zipcodes": zipcode_id,
            },
        )

        items = payload.get("items", [])

        if not items:
            raise RecycleApiError(
                f"Aucune rue trouvée pour « {street} »."
            )

        wanted = normalize(street)
        exact = [
            item
            for item in items
            if normalize(str(item.get("name", ""))) == wanted
        ]

        if len(exact) == 1:
            return exact[0]

        suggestions = ", ".join(
            str(item.get("name", "Inconnue"))
            for item in items[:30]
        )

        raise RecycleApiError(
            f"Correspondance exacte introuvable ou ambiguë pour "
            f"« {street} ». Rues proposées : {suggestions}"
        )

    async def resolve_address(
        self,
        postcode: str,
        street: str,
    ) -> tuple[str, str, str]:
        """Resolve postal code and street IDs without guessing."""
        zipcodes = await self.find_zipcodes(postcode)
        last_error: RecycleApiError | None = None

        for zipcode in zipcodes:
            zipcode_id = str(zipcode["id"])

            try:
                street_item = await self.find_street(
                    zipcode_id,
                    street,
                )
                return (
                    zipcode_id,
                    str(street_item["id"]),
                    str(street_item.get("name", street)),
                )
            except RecycleApiError as exc:
                last_error = exc

        raise last_error or RecycleApiError(
            f"Aucune rue correspondante trouvée pour {postcode}."
        )

    async def get_collections(
        self,
        zipcode_id: str,
        street_id: str,
        house_number: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Retrieve collection events for an address."""
        payload = await self.request_json(
            "GET",
            "collections",
            params={
                "zipcodeId": zipcode_id,
                "streetId": street_id,
                "houseNumber": house_number,
                "fromDate": start.isoformat(),
                "untilDate": end.isoformat(),
                "size": 200,
            },
        )

        return payload.get("items", [])
