from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinator, get_hub
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = get_coordinator(hass, entry)
    hub = get_hub(hass, entry)
    async_add_entities([PanasonicErvPowerSwitch(coordinator, hub)])


class PanasonicErvPowerSwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "新风电源"
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator, hub):
        super().__init__(coordinator)
        self._hub = hub
        self._attr_unique_id = f"{coordinator.name}_power"

    @property
    def is_on(self):
        return self.coordinator.data.get("power") == 1

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self._hub.write_register, 1, 1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self._hub.write_register, 1, 0)
        await self.coordinator.async_request_refresh()
