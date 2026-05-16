from __future__ import annotations

from pymodbus.client import ModbusTcpClient

# 保持寄存器（从地址 1 起读 16 个）
REG_READ_START = 1
REG_READ_COUNT = 16

# 控制寄存器（写入地址，真机已验证）
REG_POWER = 1
REG_MODE = 2
REG_FAN_SPEED = 3


class PanaErvHub:
    """Modbus 通信（RTU over TCP，有人模块透传）。"""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    def _client(self) -> ModbusTcpClient:
        return ModbusTcpClient(self.host, port=self.port, timeout=3, framer="rtu")

    def read_data(self) -> dict:
        client = self._client()
        if not client.connect():
            raise ConnectionError(f"无法连接到 {self.host}:{self.port}")
        try:
            result = client.read_holding_registers(
                address=REG_READ_START, count=REG_READ_COUNT
            )
            if result.isError():
                raise ConnectionError(f"读取寄存器失败: {result}")
            reg = result.registers
            return {
                "power": reg[0],
                "mode": reg[1],
                "fan_speed": reg[2],
                "actual_mode": reg[3],
                "actual_fan_speed": reg[4],
                "ra_humidity": reg[6],
                "temp_raw": reg[7],
                "filter_clean_hours": reg[9],
                "filter_replace_hours": reg[11],
                "fault_code": reg[14],
            }
        finally:
            client.close()

    def write_register(self, address: int, value: int) -> None:
        client = self._client()
        if not client.connect():
            raise ConnectionError(f"无法连接到 {self.host}:{self.port}")
        try:
            result = client.write_registers(address=address, values=[value])
            if result.isError():
                raise ConnectionError(f"写入寄存器失败: {result}")
        finally:
            client.close()

    def read_raw_registers(self) -> list[int]:
        client = self._client()
        if not client.connect():
            raise ConnectionError(f"无法连接到 {self.host}:{self.port}")
        try:
            result = client.read_holding_registers(
                address=REG_READ_START, count=REG_READ_COUNT
            )
            if result.isError():
                raise ConnectionError(f"读取寄存器失败: {result}")
            return list(result.registers)
        finally:
            client.close()
