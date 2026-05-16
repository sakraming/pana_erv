from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_NAME, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN
from .hub import PanaErvHub

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.FAN]

__all__ = ["PanaErvHub", "get_coordinator", "get_hub"]


def get_hub(hass: HomeAssistant, entry: ConfigEntry) -> PanaErvHub:
    return hass.data[DOMAIN][entry.entry_id]["hub"]


def get_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> DataUpdateCoordinator:
    return hass.data[DOMAIN][entry.entry_id]["coordinator"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data.get(CONF_HOST)
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    hub = PanaErvHub(host, port)

    async def async_update_data() -> dict:
        try:
            return await hass.async_add_executor_job(hub.read_data)
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=name,
        update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "hub": hub,
        "coordinator": coordinator,
        "name": name,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
