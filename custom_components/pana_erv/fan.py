from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinator, get_hub
from .const import DOMAIN
from .hub import REG_FAN_SPEED, REG_MODE, REG_POWER
from .state import (
    MODE_TO_PRESET,
    PRESET_TO_MODE,
    build_extra_attributes,
    percentage_to_speed,
    speed_to_percentage,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = get_coordinator(hass, entry)
    hub = get_hub(hass, entry)
    async_add_entities([PanaErvFan(coordinator, hub, entry)])


class PanaErvFan(CoordinatorEntity, FanEntity):
    _attr_name = "松下新风"
    _attr_icon = "mdi:air-filter"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator, hub, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._hub = hub
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Panasonic",
            model="ERV (Modbus)",
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get("power") == 1

    @property
    def percentage(self) -> int | None:
        return speed_to_percentage(self.coordinator.data.get("fan_speed"))

    @property
    def percentage_step(self) -> int:
        return 50

    @property
    def preset_modes(self) -> list[str]:
        return list(PRESET_TO_MODE.keys())

    @property
    def current_preset_mode(self) -> str | None:
        mode = self.coordinator.data.get("mode")
        return MODE_TO_PRESET.get(mode)

    @property
    def extra_state_attributes(self):
        return build_extra_attributes(self.coordinator.data)

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs
    ) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return

        await self.hass.async_add_executor_job(self._hub.write_register, REG_POWER, 1)

        if preset_mode is not None:
            mode_value = PRESET_TO_MODE.get(preset_mode)
            if mode_value is not None:
                await self.hass.async_add_executor_job(
                    self._hub.write_register, REG_MODE, mode_value
                )

        if percentage is not None:
            speed = percentage_to_speed(percentage)
            await self.hass.async_add_executor_job(
                self._hub.write_register, REG_FAN_SPEED, speed
            )

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._hub.write_register, REG_POWER, 0)
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return

        if not self.is_on:
            await self.hass.async_add_executor_job(self._hub.write_register, REG_POWER, 1)

        speed = percentage_to_speed(percentage)
        await self.hass.async_add_executor_job(
            self._hub.write_register, REG_FAN_SPEED, speed
        )
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode_value = PRESET_TO_MODE.get(preset_mode)
        if mode_value is None:
            return

        if not self.is_on:
            await self.hass.async_add_executor_job(self._hub.write_register, REG_POWER, 1)

        await self.hass.async_add_executor_job(
            self._hub.write_register, REG_MODE, mode_value
        )
        await self.coordinator.async_request_refresh()
