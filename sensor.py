from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinator

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(key="ra_humidity", name="室内回风湿度", native_unit_of_measurement="%", icon="mdi:water-percent"),
    SensorEntityDescription(key="temp_raw", name="温度原始值", icon="mdi:thermometer"),
    SensorEntityDescription(key="filter_clean_hours", name="滤网清扫剩余时间", native_unit_of_measurement="h", icon="mdi:air-filter"),
    SensorEntityDescription(key="filter_replace_hours", name="滤网更换剩余时间", native_unit_of_measurement="h", icon="mdi:air-filter"),
    SensorEntityDescription(key="fault_code", name="故障代码", icon="mdi:alert-circle-outline"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = get_coordinator(hass, entry)
    async_add_entities([PanasonicErvSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS])


class PanasonicErvSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.name}_{description.key}"
        self._attr_name = f"{coordinator.name} {description.name}"

    @property
    def native_value(self):
        value = self.coordinator.data.get(self.entity_description.key)
        if self.entity_description.key == "temp_raw" and value is not None:
            return value - 30 if value > 0 else None
        return value
