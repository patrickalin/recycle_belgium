"""Recycle Belgique integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from homeassistant.helpers import aiohttp_client

from .api import RecycleApiError, RecycleClient
from .const import (
    CONF_HOUSE_NUMBER,
    COLLECTIONS_HORIZON_DAYS,
    DOMAIN,
    UPDATE_INTERVAL_HOURS,
)

PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Recycle Belgique from a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    client = RecycleClient(session)

    async def async_update_data():
        """Fetch collection data."""
        from datetime import timedelta

        from homeassistant.util import dt as dt_util

        today = dt_util.now().date()
        end = today + timedelta(days=COLLECTIONS_HORIZON_DAYS)

        try:
            return await client.get_collections(
                entry.data["zipcode_id"],
                entry.data["street_id"],
                entry.data[CONF_HOUSE_NUMBER],
                today,
                end,
            )
        except RecycleApiError as err:
            raise UpdateFailed(
                f"Impossible de récupérer le calendrier des collectes : {err}"
            ) from err

    coordinator = DataUpdateCoordinator(
        hass,
        logger=__import__("logging").getLogger(__name__),
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
