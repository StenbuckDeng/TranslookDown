#!/usr/bin/env python3
"""
TranslookDown License Generator
================================
用法：
  python3 gen_license.py                     # 生成一个 Pro License（手动模式）
  python3 gen_license.py --plan team         # 生成 Team License
  python3 gen_license.py --years 2           # 有效期 2 年（默认 1 年）
  python3 gen_license.py --push              # 生成后自动写入 Cloudflare KV
  python3 gen_license.py --list              # 列出 KV 中所有 License
  python3 gen_license.py --revoke TLD-XXXX  # 吊销某个 License

自动写入 KV 需要设置环境变量：
  export CF_API_TOKEN="你的 Cloudflare API Token"
  export CF_ACCOUNT_ID="0d4293cde18c312726d39db486071195"
  export CF_KV_NAMESPACE_ID="42f09113c9a64457b4422a3c489e2225"
"""

import argparse

# 自动加载同目录下的 .env 文件
import pathlib
_env_file = pathlib.Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            import os as _os2; _os2.environ.setdefault(_k.strip(), _v.strip())

import json
import os
import random
import string
import time
import sys
from datetime import datetime, timedelta

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ─── 配置（可改 ）────────────────────────────────────────────
CF_ACCOUNT_ID    = os.getenv("CF_ACCOUNT_ID",    "0d4293cde18c312726d39db486071195")
CF_KV_NS_ID      = os.getenv("CF_KV_NAMESPACE_ID","42f09113c9a64457b4422a3c489e2225")
CF_API_TOKEN     = os.getenv("CF_API_TOKEN",      "")  # 必须设置才能自动写 KV
KEY_PREFIX       = "TLD"
# ────────────────────────────────────────────────────────────


def gen_key() -> str:
    """生成一个唯一 License Key，格式：TLD-XXXXX-XXXXX-XXXXX"""
    def rand5():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"{KEY_PREFIX}-{rand5()}-{rand5()}-{rand5()}"


def make_license(plan: str, years: int, email: str = "") -> dict:
    """生成 License 数据结构"""
    expires_at = int(time.time()) + years * 365 * 86400
    return {
        "plan":       plan,
        "expires_at": expires_at,
        "expires_str": datetime.fromtimestamp(expires_at).strftime("%Y-%m-%d"),
        "devices":    [],
        "ttl":        years * 365 * 86400,
        "buyer_email": email,
        "created_at": int(time.time()),
    }


# ─── Cloudflare KV API ───────────────────────────────────────

def cf_headers():
    return {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type":  "application/json",
    }

def cf_base():
    return f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/storage/kv/namespaces/{CF_KV_NS_ID}"


def kv_write(key: str, value: dict) -> bool:
    """写入一条 License 到 KV"""
    if not HAS_REQUESTS:
        print("❌ 需要安装 requests：pip3 install requests")
        return False
    if not CF_API_TOKEN:
        print("❌ 请先设置环境变量 CF_API_TOKEN")
        return False

    url = f"{cf_base()}/values/license:{key}"
    resp = requests.put(
        url,
        headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
        data=json.dumps(value),
        params={"expiration_ttl": value.get("ttl", 31536000)},
    )
    return resp.status_code == 200


def kv_delete(key: str) -> bool:
    """从 KV 删除一条 License（吊销）"""
    if not HAS_REQUESTS or not CF_API_TOKEN:
        print("❌ 需要 requests 和 CF_API_TOKEN")
        return False

    url = f"{cf_base()}/values/license:{key}"
    resp = requests.delete(url, headers=cf_headers())
    return resp.status_code == 200


def kv_list() -> list:
    """列出 KV 中所有 License"""
    if not HAS_REQUESTS or not CF_API_TOKEN:
        print("❌ 需要 requests 和 CF_API_TOKEN")
        return []

    url = f"{cf_base()}/keys"
    resp = requests.get(url, headers=cf_headers(), params={"prefix": "license:"})
    if resp.status_code != 200:
        print(f"❌ 查询失败：{resp.text}")
        return []
    return resp.json().get("result", [])


def kv_get(key: str) -> dict | None:
    """读取单条 License"""
    if not HAS_REQUESTS or not CF_API_TOKEN:
        return None
    url = f"{cf_base()}/values/license:{key}"
    resp = requests.get(url, headers=cf_headers())
    if resp.status_code == 200:
        try:
            return resp.json()
        except Exception:
            return None
    return None


# ─── 命令行入口 ──────────────────────────────────────────────

def cmd_generate(args):
    key     = gen_key()
    data    = make_license(args.plan, args.years, args.email)
    kv_key  = f"license:{key}"
    kv_val  = {k: v for k, v in data.items() if k != "expires_str"}

    print("=" * 52)
    print(f"  🔑 License Key   : {key}")
    print(f"  📦 Plan          : {data['plan'].upper()}")
    print(f"  📅 Expires       : {data['expires_str']} ({args.years} 年)")
    if args.email:
        print(f"  📧 Email         : {args.email}")
    print("=" * 52)

    if args.push:
        print("\n► 写入 Cloudflare KV...", end=" ")
        ok = kv_write(key, kv_val)
        if ok:
            print("✅ 成功！")
            print(f"\n用户激活方式：在 app 右上角点 FREE 徽章，输入以下 Key：\n  {key}")
        else:
            print("❌ 写入失败，请检查 CF_API_TOKEN 是否正确")
            _print_manual(kv_key, kv_val)
    else:
        _print_manual(kv_key, kv_val)


def _print_manual(kv_key: str, kv_val: dict):
    print("\n► 手动写入 Cloudflare KV（Dashboard → Workers KV → LICENSE_KV → 添加条目）：")
    print(f"\n  Key  : {kv_key}")
    print(f"  Value: {json.dumps(kv_val, ensure_ascii=False)}")
    print("\n  或在 Cloudflare Dashboard 粘贴：")
    print(f"  https://dash.cloudflare.com/0d4293cde18c312726d39db486071195/workers/kv/namespaces/42f09113c9a64457b4422a3c489e2225")


def cmd_list(args):
    print("► 列出所有 License...")
    keys = kv_list()
    if not keys:
        print("（KV 中暂无 License）")
        return
    print(f"\n{'Key':<30} {'Plan':<8} {'过期时间':<12} {'绑定设备数'}")
    print("-" * 65)
    for item in keys:
        raw_key = item["name"].replace("license:", "")
        data = kv_get(raw_key)
        if data:
            exp = datetime.fromtimestamp(data.get("expires_at", 0)).strftime("%Y-%m-%d") if data.get("expires_at") else "永久"
            devices = len(data.get("devices", []))
            plan = data.get("plan", "?").upper()
            print(f"{raw_key:<30} {plan:<8} {exp:<12} {devices}")
        else:
            print(f"{raw_key:<30} （读取失败）")


def cmd_revoke(args):
    key = args.key.replace("license:", "")  # 兼容带前缀的情况
    print(f"► 吊销 License: {key}...", end=" ")
    ok = kv_delete(key)
    if ok:
        print("✅ 已吊销，该 Key 立即失效")
    else:
        print("❌ 失败，请手动在 CF Dashboard 删除")


def main():
    parser = argparse.ArgumentParser(description="TranslookDown License 管理工具")
    sub = parser.add_subparsers(dest="cmd")

    # generate（默认）
    gen = sub.add_parser("generate", help="生成新 License（默认命令）")
    gen.add_argument("--plan",  default="pro",  choices=["pro", "team"], help="套餐类型（默认 pro）")
    gen.add_argument("--years", default=1,      type=int,                help="有效期（年，默认 1）")
    gen.add_argument("--email", default="",                              help="买家邮箱（可选，仅记录用）")
    gen.add_argument("--push",  action="store_true",                     help="自动写入 Cloudflare KV")

    # list
    sub.add_parser("list", help="列出所有 License")

    # revoke
    rev = sub.add_parser("revoke", help="吊销 License")
    rev.add_argument("key", help="要吊销的 License Key")

    args = parser.parse_args()

    # 默认命令 = generate
    if args.cmd is None:
        args.cmd = "generate"
        args.plan  = "pro"
        args.years = 1
        args.email = ""
        args.push  = False

    if args.cmd == "generate":
        cmd_generate(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "revoke":
        cmd_revoke(args)


if __name__ == "__main__":
    main()
