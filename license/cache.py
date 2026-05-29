# license/cache.py
"""
本地 License 缓存
- 验证结果缓存 3 天，避免频繁请求后端
- 签名校验防止用户手动篡改缓存文件
"""

import json
import os
import time
import hashlib
from pathlib import Path


CACHE_FILE = Path.home() / ".translookdown" / "license_cache.json"
CACHE_TTL = 3 * 24 * 3600    # 缓存有效期：3 天
CACHE_SECRET = "translookdown_cache_v1"


def _sign(data: dict) -> str:
    """对缓存数据生成 16 位签名，防篡改"""
    raw = json.dumps(data, sort_keys=True) + CACHE_SECRET
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def save_cache(plan: str, license_key: str, expires_at: float) -> None:
    """保存验证结果到本地缓存文件"""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "plan": plan,
        "license_key": license_key[:8] + "...",  # 只存前8位，安全
        "cached_at": time.time(),
        "expires_at": expires_at,
    }
    data["sig"] = _sign(data)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_cache() -> dict | None:
    """
    读取本地缓存
    返回 None 表示缓存不存在、已过期或被篡改
    """
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)

        # 校验签名
        sig = data.pop("sig", "")
        if _sign(data) != sig:
            return None  # 被篡改

        data["sig"] = sig  # 还原

        # 检查缓存是否过期（3 天）
        if time.time() - data.get("cached_at", 0) > CACHE_TTL:
            return None

        return data

    except Exception:
        return None


def clear_cache() -> None:
    """清除缓存（用于退出登录 / 取消激活）"""
    try:
        CACHE_FILE.unlink()
    except FileNotFoundError:
        pass


def get_cache_info() -> dict:
    """获取缓存摘要（供 UI 展示用）"""
    cache = load_cache()
    if not cache:
        return {"valid": False}
    remaining = CACHE_TTL - (time.time() - cache.get("cached_at", 0))
    return {
        "valid": True,
        "plan": cache.get("plan", "free"),
        "expires_at": cache.get("expires_at"),
        "cache_remaining_hours": max(0, int(remaining / 3600)),
    }
