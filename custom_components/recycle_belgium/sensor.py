"""Sensors for Recycle Belgique."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN


CATEGORIES = {
    "verre": {
        "name": "Verre",
        "icon": "mdi:bottle-wine",
    },
    "papier_carton": {
        "name": "Papiers-cartons",
        "icon": "mdi:newspaper-variant",
    },
    "organique": {
        "name": "Déchets organiques",
        "icon": "mdi:leaf",
    },
    "ordures": {
        "name": "Ordures ménagères",
        "icon": "mdi:trash-can",
    },
    "pmc": {
        "name": "PMC",
        "icon": "mdi:recycle",
    },
}


def normalize(value: str) -> str:
    """Normalize a label for category matching."""
    import unicodedata

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char for char in value if not unicodedata.combining(char)
    )
    return "".join(
        char for char in value.casefold() if char.isalnum()
    )


def identify_category(label: str) -> str | None:
    """Identify a waste category from its API label."""
    value = normalize(label)

    if value in ("pmc", "pmd"):
        return "pmc"

    if any(word in value for word in (
        "verre",
        "glas",
        "glass",
    )):
        return "verre"

    if any(word in value for word in (
        "papier",
        "carton",
        "paper",
        "cardboard",
        "papiercarton",
    )):
        return "papier_carton"

    if any(word in value for word in (
        "organique",
        "organic",
        "gft",
        "biodechets",
        "dechetsverts",
    )):
        return "organique"

    if any(word in value for word in (
        "orduresmenageres",
        "dechetsmenagers",
        "dechetsresiduels",
        "restafval",
        "huisvuil",
        "residualwaste",
    )):
        return "ordures"

    return None


def get_collection_date(item: dict) -> date | None:
    """Extract the date supplied by the API."""
    raw_date = item.get("timestamp")

    if not raw_date:
        return None

    try:
        return datetime.fromisoformat(
            str(raw_date).replace("Z", "+00:00")
        ).date()
    except (ValueError, TypeError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up collection sensors."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            RecycleCollectionSensor(coordinator, entry, category)
            for category in CATEGORIES
        ]
    )


class RecycleCollectionSensor(
    CoordinatorEntity,
    SensorEntity,
):
    """Sensor showing the next collection date."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        category: str,
    ) -> None:
        super().__init__(coordinator)

        self._category = category
        self._entry = entry

        config = CATEGORIES[category]

        self._attr_translation_key = category
        self._attr_icon = config["icon"]
        self._attr_unique_id = (
            f"{entry.entry_id}_{category}"
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Recycle Belgium",
            manufacturer="Alin.be",
            configuration_url="https://github.com/patrickalin/recycle_belgium",
        )

    @property
    def available(self) -> bool:
        """Return whether the coordinator has valid data."""
        return super().available

    def _upcoming_dates(self) -> list[date]:
        """Return future collection dates for this category."""
        from homeassistant.util import dt as dt_util

        today = dt_util.now().date()
        dates = set()

        for item in self.coordinator.data or []:
            if item.get("type") != "collection":
                continue

            exception = item.get("exception") or {}
            if exception.get("replacedBy"):
                continue

            fraction = item.get("fraction") or {}
            names = fraction.get("name") or {}

            label = (
                names.get("fr")
                or names.get("nl")
                or names.get("en")
                or ""
            )

            if identify_category(str(label)) != self._category:
                continue

            collection_date = get_collection_date(item)

            if collection_date and collection_date >= today:
                dates.add(collection_date)

        return sorted(dates)

    @property
    def native_value(self) -> date | None:
        """Return the next collection date."""
        dates = self._upcoming_dates()
        return dates[0] if dates else None

    @property
    def extra_state_attributes(self) -> dict:
        """Return upcoming collection dates."""
        return {
            "upcoming_dates": [
                collection_date.isoformat()
                for collection_date in self._upcoming_dates()
            ]
        }
