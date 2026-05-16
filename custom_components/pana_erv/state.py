from __future__ import annotations

# 真机两档：寄存器 1=弱，3=强（勿写入 2）
SPEED_TO_PERCENT = {
    1: 50,
    3: 100,
}

SPEED_TO_NAME = {
    1: "弱",
    3: "强",
}

MODE_TO_PRESET = {
    0: "热交换",
    1: "普通模式",
}

PRESET_TO_MODE = {
    "热交换": 0,
    "普通模式": 1,
}

_INVALID_REGISTER = 65535


def percentage_to_speed(percentage: int) -> int:
    return 1 if percentage <= 50 else 3


def speed_to_percentage(speed: int | None) -> int | None:
    if speed is None:
        return None
    return SPEED_TO_PERCENT.get(speed)


def _valid_register(value: int | None) -> int | None:
    if not isinstance(value, int):
        return None
    if value < 0 or value >= _INVALID_REGISTER:
        return None
    return value


def _valid_temperature(temp_raw: int | None) -> int | None:
    temp_raw = _valid_register(temp_raw)
    if temp_raw is None:
        return None
    celsius = temp_raw - 30
    if -40 <= celsius <= 60:
        return celsius
    return None


def _speed_label(speed: int | None) -> str | None:
    speed = _valid_register(speed)
    if speed is None:
        return None
    return SPEED_TO_NAME.get(speed)


def _mode_label(mode: int | None) -> str | None:
    mode = _valid_register(mode)
    if mode is None:
        return None
    return MODE_TO_PRESET.get(mode)


def build_extra_attributes(data: dict) -> dict:
    """与 fan 实体 extra_state_attributes 一致；无效值不展示。"""
    attrs: dict = {}

    if label := _speed_label(data.get("fan_speed")):
        attrs["当前风量档位"] = label
    if label := _mode_label(data.get("mode")):
        attrs["当前模式"] = label
    if label := _speed_label(data.get("actual_fan_speed")):
        attrs["实际风量档位"] = label
    if label := _mode_label(data.get("actual_mode")):
        attrs["实际模式"] = label

    humidity = _valid_register(data.get("ra_humidity"))
    if humidity is not None:
        attrs["室内湿度"] = humidity

    temperature = _valid_temperature(data.get("temp_raw"))
    if temperature is not None:
        attrs["温度"] = temperature

    clean_hours = _valid_register(data.get("filter_clean_hours"))
    if clean_hours is not None:
        attrs["滤网清扫剩余时间(小时)"] = clean_hours

    replace_hours = _valid_register(data.get("filter_replace_hours"))
    if replace_hours is not None:
        attrs["滤网更换剩余时间(小时)"] = replace_hours

    fault = _valid_register(data.get("fault_code"))
    if fault is not None and fault != 0:
        attrs["故障代码"] = fault

    return attrs


def build_fan_view(data: dict) -> dict:
    speed = data.get("fan_speed")
    mode = data.get("mode")
    return {
        "is_on": data.get("power") == 1,
        "percentage": speed_to_percentage(speed),
        "preset_mode": _mode_label(mode),
        **build_extra_attributes(data),
    }
