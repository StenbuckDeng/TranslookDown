# license/fingerprint.py
"""
生成设备唯一指纹，用于绑定 License
支持 macOS 和 Windows 双平台
指纹基于 MAC 地址 + 硬件序列号（不可逆 SHA-256 hash）
"""

import hashlib
import uuid
import platform
import subprocess


def get_mac_address() -> str:
    """获取主网卡 MAC 地址"""
    mac = hex(uuid.getnode()).replace("0x", "").upper().zfill(12)
    return ":".join(mac[i:i+2] for i in range(0, 12, 2))


def get_serial_number() -> str:
    """
    获取硬件序列号
    macOS: system_profiler SPHardwareDataType
    Windows: wmic bios get serialnumber
    """
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "Serial Number" in line:
                    return line.split(":")[1].strip()

        elif system == "Windows":
            result = subprocess.run(
                ["wmic", "bios", "get", "serialnumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
            # Output: ['SerialNumber', '<value>']
            if len(lines) >= 2:
                return lines[1]

    except Exception:
        pass

    return "unknown"


def get_fingerprint() -> str:
    """
    生成设备指纹
    返回 64 位 hex 字符串，用于 License 绑定
    同一台机器每次结果相同
    """
    components = [
        get_mac_address(),
        get_serial_number(),
        platform.machine(),      # arm64 / x86_64 / AMD64
        platform.system(),       # Darwin / Windows
        platform.node(),         # 设备名（主机名）
    ]
    raw = "|".join(components)
    return hashlib.sha256(raw.encode()).hexdigest()


if __name__ == "__main__":
    print(f"Platform  : {platform.system()} {platform.machine()}")
    print(f"Hostname  : {platform.node()}")
    print(f"MAC Addr  : {get_mac_address()}")
    print(f"Serial    : {get_serial_number()}")
    print(f"Fingerprint: {get_fingerprint()}")
