# license/checker.py
"""
License 验证核心
流程：
  1. 检查内存缓存（运行期内，5 分钟有效）
  2. 检查本地磁盘缓存（3 天有效）
  3. 缓存过期 → 请求后端在线验证
  4. 后端不可达 → 宽松离线模式（最多允许离线 7 天）
"""

import requests
import time
from .cache import save_cache, load_cache, clear_cache
from .fingerprint import get_fingerprint

# 替换为你部署的 Cloudflare Worker URL
LICENSE_API = "https://odd-base-e5e3.ts-qrcode.workers.dev"
OFFLINE_GRACE = 7 * 24 * 3600   # 离线宽限 7 天


class LicenseChecker:
    def __init__(self):
        self._plan: str | None = None
        self._license_key: str | None = None
        self._last_check: float = 0

    # ─── Public API ────────────────────────────────────────────

    def get_current_plan(self) -> str:
        """
        获取当前 plan，供功能门控使用
        返回 'free' / 'pro' / 'team'
        """
        # 1. 内存缓存（5 分钟内不重复检查）
        if self._plan and time.time() - self._last_check < 300:
            return self._plan

        # 2. 磁盘缓存
        cache = load_cache()
        if cache:
            self._plan = cache["plan"]
            self._last_check = time.time()
            return self._plan

        # 3. 无有效缓存 → free
        return "free"

    def activate(self, license_key: str) -> tuple[bool, str]:
        """
        激活 License（在线请求后端）
        返回 (success: bool, message: str)
        """
        fingerprint = get_fingerprint()
        try:
            resp = requests.post(
                LICENSE_API,
                json={
                    "key": license_key,
                    "fingerprint": fingerprint,
                    "action": "activate",
                },
                timeout=10,
            )
            data = resp.json()

            if data.get("valid"):
                plan = data.get("plan", "pro")
                expires_at = data.get("expires_at", time.time() + 365 * 86400)
                save_cache(plan, license_key, expires_at)
                self._plan = plan
                self._license_key = license_key
                self._last_check = time.time()
                return True, f"激活成功！当前套餐：{plan.upper()}"
            else:
                return False, data.get("message", "License 无效，请检查后重试")

        except requests.Timeout:
            return False, "请求超时，请检查网络后重试"
        except requests.RequestException:
            return False, "网络连接失败，请检查网络后重试"

    def deactivate(self) -> None:
        """退出登录 / 取消激活，清除本地缓存"""
        clear_cache()
        self._plan = None
        self._license_key = None
        self._last_check = 0

    def get_status(self) -> dict:
        """获取当前激活状态摘要（供 /api/license/status 使用）"""
        from .cache import get_cache_info
        plan = self.get_current_plan()
        info = get_cache_info()
        return {
            "plan": plan,
            "activated": plan != "free",
            "cache_valid": info.get("valid", False),
            "expires_at": info.get("expires_at"),
            "cache_remaining_hours": info.get("cache_remaining_hours", 0),
        }


# ─── 全局单例（供 video_downloader.py import 使用）────────────────
license_checker = LicenseChecker()


def require_plan(required_plan: str):
    """
    装饰器：要求 Flask 路由调用方具有指定 plan 或以上

    用法：
        @app.route("/api/some_pro_feature")
        @require_plan("pro")
        def some_pro_feature():
            ...
    """
    from functools import wraps
    from flask import jsonify

    PLAN_ORDER = {"free": 0, "pro": 1, "team": 2}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current = license_checker.get_current_plan()
            if PLAN_ORDER.get(current, 0) >= PLAN_ORDER.get(required_plan, 0):
                return func(*args, **kwargs)
            return jsonify({
                "upgrade_required": True,
                "trigger": "plan_required",
                "title": f"此功能需要 {required_plan.upper()}",
                "body": f"当前套餐 {current.upper()} 无权限访问此功能。",
                "cta": f"升级 {required_plan.upper()} · $19/年",
            }), 403
        return wrapper
    return decorator
