from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinator, get_hub

MODE_OPTIONS = ["热交换", "普通/旁通", "内循环", "自动"]
FAN_OPTIONS = ["低噪音", "弱", "强"]
MODE_TO_VALUE = {"热交换": 0, "普通/旁通": 1, "内循环": 2, "自动": 3}
FAN_TO_VALUE = {"低噪音": 1, "弱": 2, "强": 3}
VALUE_TO_MODE = {v: k for k, v in MODE_TO_VALUE.items()}
VALUE_TO_FAN = {v: k for k, v in FAN_TO_VALUE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = get_coordinator(hass, entry)
    hub = get_hub(hass, entry)
    async_add_entities([
        PanasonicErvModeSelect(coordinator, hub),
        PanasonicErvFanSpeedSelect(coordinator, hub),
    ])


class PanasonicErvModeSelect(CoordinatorEntity, SelectEntity):
    _attr_name = "运行模式"
    _attr_icon = "mdi:rotate-right"

    def __init__(self, coordinator, hub):
        super().__init__(coordinator)
        self._hub = hub
        self._attr_unique_id = f"{coordinator.name}_mode"

    @property
    def current_option(self):
        return VALUE_TO_MODE.get(self.coordinator.data.get("mode"))

    @property
    def options(self):
        return MODE_OPTIONS

    async def async_select_option(self, option: str):
        await self.hass.async_add_executor_job(self._hub.write_register, 2, MODE_TO_VALUE[option])
        await self.coordinator.async_request_refresh()


class PanasonicErvFanSpeedSelect(CoordinatorEntity, SelectEntity):
    _attr_name = "风量"
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, hub):
        super().__init__(coordinator)
        self._hub = hub
        self._attr_unique_id = f"{coordinator.name}_fan_speed"

    @property
    def current_option(self):
        return VALUE_TO_FAN.get(self.coordinator.data.get("fan_speed"))

    @property
    def options(self):
        return FAN_OPTIONS

    async def async_select_option(self, option: str):
        await self.hass.async_add_executor_job(self._hub.write_register, 3, FAN_TO_VALUE[option])
        await self.coordinator.async_request_refresh()
