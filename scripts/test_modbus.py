#!/usr/bin/env python3
"""
本机测试 Pana ERV 的 Modbus 逻辑（与 Home Assistant 集成共用 hub.py / state.py）。

示例:
  # 安装依赖（仅需 pymodbus，无需安装 homeassistant）
  source .venv/bin/activate && pip install -r scripts/requirements-test.txt

  # 离线自检：逻辑与显示格式
  python scripts/test_modbus.py --self-test

  # 连接真机只读
  python scripts/test_modbus.py --host 192.168.30.135 --port 8899

  # 连续轮询 3 次
  python scripts/test_modbus.py --host 192.168.30.135 --watch 3 --interval 2

  # 写入测试（会改设备状态，慎用）
  python scripts/test_modbus.py --host 192.168.30.135 --write-power 1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "pana_erv"


def _load_module(name: str, filename: str):
    path = INTEGRATION / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_hub = _load_module("pana_erv_hub", "hub.py")
_state = _load_module("pana_erv_state", "state.py")
PanaErvHub = _hub.PanaErvHub
build_fan_view = _state.build_fan_view
percentage_to_speed = _state.percentage_to_speed

MOCK_REGISTERS = [
    1,  # power
    0,  # mode 热交换
    3,  # fan_speed 强
    0,  # actual_mode
    3,  # actual_fan_speed
    0,
    55,  # ra_humidity
    55,  # temp_raw -> 25°C
    0,
    100,  # filter_clean
    0,
    200,  # filter_replace
    0,
    0,
    0,  # fault
]


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def _print_result(data: dict, raw: list[int] | None = None) -> None:
    view = build_fan_view(data)
    _print_section("原始寄存器")
    if raw is not None:
        for i, val in enumerate(raw, start=1):
            print(f"  [{i:2d}] = {val}")
    _print_section("解析数据 (hub.read_data)")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    _print_section("HA Fan 实体预览 (state.build_fan_view)")
    print(json.dumps(view, ensure_ascii=False, indent=2))


def run_self_test() -> None:
    """不连设备：mock Modbus，验证读写与状态解析。"""
    _print_section("离线自检")

    mock_result = MagicMock()
    mock_result.isError.return_value = False
    mock_result.registers = MOCK_REGISTERS

    mock_client = MagicMock()
    mock_client.connect.return_value = True
    mock_client.read_holding_registers.return_value = mock_result
    mock_client.write_registers.return_value = MagicMock(isError=lambda: False)

    hub = PanaErvHub("127.0.0.1", 8899)
    with patch.object(hub, "_client", return_value=mock_client):
        data = hub.read_data()
        _print_result(data, raw=MOCK_REGISTERS)
        hub.write_register(1, 1)
        mock_client.write_registers.assert_called_with(address=1, values=[1])

    print("\n✓ 离线自检通过（hub 读写 + state 解析）")


def run_unit_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


class TestStateParsing(unittest.TestCase):
    def test_build_fan_view_from_mock_registers(self):
        data = {
            "power": MOCK_REGISTERS[0],
            "mode": MOCK_REGISTERS[1],
            "fan_speed": MOCK_REGISTERS[2],
            "actual_mode": MOCK_REGISTERS[3],
            "actual_fan_speed": MOCK_REGISTERS[4],
            "ra_humidity": MOCK_REGISTERS[6],
            "temp_raw": MOCK_REGISTERS[7],
            "filter_clean_hours": MOCK_REGISTERS[9],
            "filter_replace_hours": MOCK_REGISTERS[11],
            "fault_code": MOCK_REGISTERS[14],
        }
        view = build_fan_view(data)
        self.assertTrue(view["is_on"])
        self.assertEqual(view["percentage"], 100)
        self.assertEqual(view["当前风量档位"], "强")
        self.assertEqual(view["preset_mode"], "热交换")
        self.assertEqual(view["温度"], 25)
        self.assertEqual(view["室内湿度"], 55)

    def test_two_speed_mapping(self):
        self.assertEqual(percentage_to_speed(30), 1)
        self.assertEqual(percentage_to_speed(50), 1)
        self.assertEqual(percentage_to_speed(51), 3)
        self.assertEqual(percentage_to_speed(100), 3)

    def test_invalid_registers_filtered(self):
        data = {
            "power": 1,
            "mode": 0,
            "fan_speed": 3,
            "actual_mode": 0,
            "actual_fan_speed": 3,
            "ra_humidity": 65535,
            "temp_raw": 32639,
            "filter_clean_hours": 65535,
            "filter_replace_hours": 65535,
            "fault_code": 0,
        }
        view = build_fan_view(data)
        self.assertNotIn("室内湿度", view)
        self.assertNotIn("温度", view)
        self.assertNotIn("滤网清扫剩余时间(小时)", view)


def read_once(host: str, port: int, show_raw: bool, *, quiet: bool = False) -> dict:
    hub = PanaErvHub(host, port)
    raw = hub.read_raw_registers() if show_raw else None
    data = hub.read_data()
    if not quiet:
        _print_result(data, raw=raw)
    return data


def _snapshot(data: dict) -> dict:
    return {
        "power": data.get("power"),
        "mode": data.get("mode"),
        "fan_speed": data.get("fan_speed"),
    }


def run_control_tests(host: str, port: int, settle: float = 1.5) -> None:
    """依次测试电源、风量、模式写入，结束后尽量恢复原状态。"""
    hub = PanaErvHub(host, port)
    _print_section("控制命令测试")

    print("读取初始状态...")
    before = hub.read_data()
    snap = _snapshot(before)
    print("  初始:", json.dumps(snap, ensure_ascii=False))

    errors: list[str] = []

    def check(label: str, field: str, expected: int, *, retries: int = 3) -> None:
        actual = None
        for attempt in range(retries):
            time.sleep(settle if attempt == 0 else 1.0)
            actual = hub.read_data().get(field)
            if actual == expected:
                break
        ok = actual == expected
        mark = "✓" if ok else "✗"
        print(f"  {mark} {label}: 期望 {field}={expected}, 实际={actual}")
        if not ok:
            errors.append(f"{label}: 期望 {field}={expected}, 实际 {actual}")

    try:
        # 1. 开机
        print("\n[1] 写入寄存器 1=1 (开机)")
        REG_POWER = _hub.REG_POWER
        REG_MODE = _hub.REG_MODE
        REG_FAN_SPEED = _hub.REG_FAN_SPEED

        hub.write_register(REG_POWER, 1)
        check("开机", "power", 1)

        target_speed = 1 if snap.get("fan_speed") != 1 else 3
        print(f"\n[2] 写入寄存器 {REG_FAN_SPEED}={target_speed} (风量 弱/强)")
        hub.write_register(REG_FAN_SPEED, target_speed)
        check(f"风量档位 {target_speed}", "fan_speed", target_speed, retries=4)

        target_mode = 1 if before.get("mode") == 0 else 0
        mode_name = "普通模式" if target_mode == 1 else "热交换"
        print(f"\n[3] 写入寄存器 {REG_MODE}={target_mode} ({mode_name})")
        hub.write_register(REG_MODE, target_mode)
        check(mode_name, "mode", target_mode)

        print(f"\n[4] 写入寄存器 {REG_POWER}=0 (关机)")
        hub.write_register(REG_POWER, 0)
        check("关机", "power", 0)

    finally:
        # 恢复初始状态（关机时需先开机再写模式/风量）
        print("\n恢复初始状态...")
        REG_POWER = _hub.REG_POWER
        REG_MODE = _hub.REG_MODE
        REG_FAN_SPEED = _hub.REG_FAN_SPEED

        if snap["power"] == 0:
            hub.write_register(REG_POWER, 1)
            time.sleep(settle)
        if snap.get("fan_speed") is not None:
            hub.write_register(REG_FAN_SPEED, snap["fan_speed"])
            time.sleep(1.2)
        if snap.get("mode") is not None:
            hub.write_register(REG_MODE, snap["mode"])
            time.sleep(1.2)
        if snap["power"] == 0:
            hub.write_register(REG_POWER, 0)
            time.sleep(settle)

        restored = hub.read_data()
        print("  恢复后:", json.dumps(_snapshot(restored), ensure_ascii=False))
        if _snapshot(restored) != snap:
            print("  警告: 与初始快照不完全一致，设备可能需在开机状态下恢复风量/模式")

    if errors:
        _print_section("控制测试失败")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("\n✓ 控制命令测试全部通过")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pana ERV 本机 Modbus 测试")
    parser.add_argument("--self-test", action="store_true", help="离线 mock 自检，不连设备")
    parser.add_argument("--unit-test", action="store_true", help="运行单元测试")
    parser.add_argument("--host", default="192.168.30.135", help="有人模块 IP")
    parser.add_argument("--port", type=int, default=8899, help="Modbus 端口")
    parser.add_argument("--watch", type=int, default=0, help="轮询次数，0 表示只读一次")
    parser.add_argument("--interval", type=float, default=2.0, help="轮询间隔秒")
    parser.add_argument("--raw", action="store_true", help="显示原始寄存器")
    parser.add_argument("--write-power", type=int, choices=[0, 1], help="写入电源 0=关 1=开")
    parser.add_argument("--write-mode", type=int, choices=[0, 1], help="写入模式 0=热交换 1=普通")
    parser.add_argument("--write-speed", type=int, choices=[1, 2, 3], help="写入风量档位")
    parser.add_argument(
        "--test-controls",
        action="store_true",
        help="自动测试开机/风量/模式/关机并恢复原状态（会短暂改变设备）",
    )
    parser.add_argument("--settle", type=float, default=1.5, help="写入后等待设备响应秒数")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return

    if args.unit_test:
        run_unit_tests()
        return

    if args.test_controls:
        try:
            read_once(args.host, args.port, show_raw=True)
            run_control_tests(args.host, args.port, settle=args.settle)
        except Exception as err:
            print(f"\n✗ 失败: {err}", file=sys.stderr)
            sys.exit(1)
        return

    if args.write_power is not None or args.write_mode is not None or args.write_speed is not None:
        hub = PanaErvHub(args.host, args.port)
        if args.write_power is not None:
            print(f"写入寄存器 1 (电源) = {args.write_power}")
            hub.write_register(1, args.write_power)
        if args.write_mode is not None:
            print(f"写入寄存器 2 (模式) = {args.write_mode}")
            hub.write_register(2, args.write_mode)
        if args.write_speed is not None:
            print(f"写入寄存器 3 (风量) = {args.write_speed}")
            hub.write_register(3, args.write_speed)
        time.sleep(0.5)

    count = max(1, args.watch) if args.watch else 1
    for i in range(count):
        if count > 1:
            _print_section(f"第 {i + 1}/{count} 次读取")
        try:
            read_once(args.host, args.port, show_raw=args.raw)
        except Exception as err:
            print(f"\n✗ 失败: {err}", file=sys.stderr)
            print(
                "\n提示: 确认本机能 ping 通有人模块；IP/端口正确；"
                "可先运行: python scripts/test_modbus.py --self-test",
                file=sys.stderr,
            )
            sys.exit(1)
        if i < count - 1:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
