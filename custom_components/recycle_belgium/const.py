DOMAIN = "recycle_belgium"

API_BASE_URL = "https://api.fostplus.be/recyclecms/public/v1"

API_HEADERS = {
    "x-consumer": "recycleapp.be",
    "User-Agent": "HomeAssistant-RecycleBelgium/1.0",
    "Accept": "application/json",
}

CONF_POSTAL_CODE = "postal_code"
CONF_STREET = "street"
CONF_HOUSE_NUMBER = "house_number"

UPDATE_INTERVAL_HOURS = 6
COLLECTIONS_HORIZON_DAYS = 365

PLATFORMS = ["sensor"]
