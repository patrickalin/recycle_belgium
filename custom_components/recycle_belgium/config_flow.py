"""Configuration flow for Recycle Belgique."""

from __future__ import annotations

import logging
import re

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from homeassistant.helpers import aiohttp_client

from .api import RecycleApiError, RecycleClient
from .const import (
    CONF_HOUSE_NUMBER,
    CONF_POSTAL_CODE,
    CONF_STREET,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for Recycle Belgique."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial configuration step."""
        errors = {}

        if user_input is not None:
            postcode = user_input[CONF_POSTAL_CODE].strip()
            street = user_input[CONF_STREET].strip()
            house_number = user_input[CONF_HOUSE_NUMBER].strip()

            if not re.fullmatch(r"\d{4}", postcode):
                errors["base"] = "invalid_postcode"
            elif not house_number:
                errors["base"] = "invalid_house_number"
            else:
                session = aiohttp_client.async_get_clientsession(
                    self.hass
                )
                client = RecycleClient(session)

                try:
                    zipcode_id, street_id, street_name = (
                        await client.resolve_address(postcode, street)
                    )

                    await self.async_set_unique_id(
                        f"{postcode}_{street_id}_{house_number}".lower()
                    )
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"{house_number} {street_name}, {postcode}",
                        data={
                            CONF_POSTAL_CODE: postcode,
                            CONF_STREET: street_name,
                            CONF_HOUSE_NUMBER: house_number,
                            "zipcode_id": zipcode_id,
                            "street_id": street_id,
                        },
                    )

                except RecycleApiError:
                    _LOGGER.exception(
                        "Impossible de valider l'adresse Recycle Belgique"
                    )
                    errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_POSTAL_CODE): str,
                vol.Required(CONF_STREET): str,
                vol.Required(CONF_HOUSE_NUMBER): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
