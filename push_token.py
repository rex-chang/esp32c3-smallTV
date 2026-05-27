#!/usr/bin/env python3
"""
push_token.py — 自动获取 AI 服务用量并推送到 ESP32 天气时钟

数据来源:
  - OpenAI/Codex: ~/.codex/auth.json → chatgpt.com/backend-api/wham/usage
  - Antigravity:   ~/.antigravity_cockpit/accounts/{uuid}.json → 缓存的配额数据

用法:
  python3 push_token.py                     循环获取并推送 (1~3分钟随机间隔)
  python3 push_token.py --once              仅执行一次
  python3 push_token.py --once --print       仅执行一次，打印 JSON
  python3 push_token.py --list "ChatGPT,45,100;Claude,20,100"
"""
import requests
import json
import sys
import os
import time
import random
import argparse
import base64
from pathlib import Path
from datetime import datetime

CODEX_AUTH_FILE = os.path.expanduser("~/.codex/auth.json")
AG_DIR = os.path.expanduser("~/.antigravity_cockpit")
AG_ACCOUNTS_FILE = os.path.join(AG_DIR, "accounts.json")

GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    base64.b64decode(b"MTA3MTAwNjA2MDU5MS10bWhzc2luMmgyMWxjcmUyMzV2dG9sb2poNGc0MDNlcC5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbQ==").decode("utf-8")
)
GOOGLE_CLIENT_SECRET = os.environ.get(
    "GOOGLE_CLIENT_SECRET",
    base64.b64decode(b"R09DU1BYLUs1OEZXUjQ4NkxkTEoxbUxCOHNYQzR6cURBZg==").decode("utf-8")
)
CODEX_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"

AG_CLOUD_URL = "https://cloudcode-pa.googleapis.com"

# ── OpenAI / Codex ────────────────────────────────────────────

def load_codex_auth():
    try:
        return json.loads(Path(CODEX_AUTH_FILE).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_codex_auth(auth):
    auth["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    Path(CODEX_AUTH_FILE).write_text(json.dumps(auth, indent=2))


def decode_jwt_exp(token):
    """从 JWT 中提取过期时间 (exp)，失败返回 0"""
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("exp", 0)
    except Exception:
        return 0


def refresh_codex_token(refresh_token):
    resp = requests.post(
        "https://auth.openai.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CODEX_CLIENT_ID,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token"), data.get("refresh_token")
    print(f"  OpenAI token refresh failed: {resp.status_code} {resp.text[:200]}")
    return None, None


def ensure_codex_token(auth):
    """确保 access_token 有效，必要时刷新"""
    tokens = auth["tokens"]
    token = tokens.get("access_token", "")
    exp = decode_jwt_exp(token)
    if exp and time.time() > exp - 60:
        print("  OpenAI token expired, refreshing...")
        new_token, new_refresh = refresh_codex_token(tokens.get("refresh_token", ""))
        if new_token:
            tokens["access_token"] = new_token
            if new_refresh:
                tokens["refresh_token"] = new_refresh
            save_codex_auth(auth)
            return new_token
        print("  OpenAI token refresh failed, using existing token (may fail)")
    return token


def fetch_openai_usage():
    """从 ChatGPT 后端 API 获取用量。"""
    auth = load_codex_auth()
    if not auth:
        print("[OpenAI] 未找到 ~/.codex/auth.json")
        return []

    token = ensure_codex_token(auth)
    account_id = auth["tokens"]["account_id"]

    resp = requests.get(
        "https://chatgpt.com/backend-api/wham/usage",
        headers={
            "Authorization": f"Bearer {token}",
            "ChatGPT-Account-Id": account_id,
            "Accept": "application/json",
        },
        timeout=10,
    )

    if resp.status_code == 401:
        print("[OpenAI] 401, 尝试刷新后重试...")
        new_token, _ = refresh_codex_token(auth["tokens"].get("refresh_token", ""))
        if new_token:
            auth["tokens"]["access_token"] = new_token
            save_codex_auth(auth)
            resp = requests.get(
                "https://chatgpt.com/backend-api/wham/usage",
                headers={
                    "Authorization": f"Bearer {new_token}",
                    "ChatGPT-Account-Id": account_id,
                    "Accept": "application/json",
                },
                timeout=10,
            )

    if resp.status_code != 200:
        print(f"[OpenAI] API 返回 {resp.status_code}: {resp.text[:200]}")
        return []

    data = resp.json()
    rate_limit = data.get("rate_limit", {})
    plan_type = data.get("plan_type", "ChatGPT")

    services = []
    primary = rate_limit.get("primary_window", {})
    if primary:
        used_pct = int(primary.get("used_percent", 0))
        boost = primary.get("boost_call_info", {})
        boost_used = boost.get("rate_limit", {}).get("used_percent")

        name = "CodeX"
        if boost_used is not None:
            name += " +boost"
            used_pct = int(boost_used)

        services.append({
            "name": name,
            "used": used_pct,
            "limit": 100,
        })
        print(f"[OpenAI] {name}: {used_pct}%")

    return services


# ── Antigravity ────────────────────────────────────────────────

def load_antigravity_account():
    try:
        index = json.loads(Path(AG_ACCOUNTS_FILE).read_text())
        current_id = index.get("current_account_id")
        if not current_id:
            return None
        path = os.path.join(AG_DIR, "accounts", f"{current_id}.json")
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_antigravity_token(account, new_access_token, expires_in=3599):
    """刷新后写回 token"""
    account["token"]["access_token"] = new_access_token
    account["token"]["expiry_timestamp"] = int(time.time()) + expires_in
    path = os.path.join(AG_DIR, "accounts", f"{account['id']}.json")
    Path(path).write_text(json.dumps(account, indent=2))
    # 同步更新备份文件
    bak_path = os.path.join(AG_DIR, "accounts", f"{account['id']}.json.bak")
    if os.path.exists(bak_path):
        Path(bak_path).write_text(json.dumps(account, indent=2))


def refresh_ag_token(refresh_token):
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token"), data.get("expires_in", 3599)
    print(f"  Antigravity token refresh failed: {resp.status_code} {resp.text[:200]}")
    return None, None


def ensure_ag_token(account):
    token = account.get("token", {})
    expiry = token.get("expiry_timestamp", 0)
    if expiry and time.time() > expiry - 300:
        print("  Antigravity token expired, refreshing...")
        new_token, expires_in = refresh_ag_token(token.get("refresh_token", ""))
        if new_token:
            save_antigravity_token(account, new_token, expires_in)
            return new_token
        print("  Antigravity token refresh failed")
    return token.get("access_token", "")


def fetch_antigravity_live(account):
    """通过 Google Cloud Code Assist API 实时获取配额。"""
    token = ensure_ag_token(account)
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "antigravity/1.20.5",
    }

    # Step 1: loadCodeAssist → 获取 project_id
    resp = requests.post(
        f"{AG_CLOUD_URL}/v1internal:loadCodeAssist",
        json={},
        headers=headers,
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"[Antigravity] loadCodeAssist 返回 {resp.status_code}")
        return []

    data = resp.json()
    project_id = data.get("projectId", "")

    # Step 2: fetchAvailableModels → 获取各模型配额
    resp = requests.post(
        f"{AG_CLOUD_URL}/v1internal:fetchAvailableModels",
        json={"project": project_id},
        headers=headers,
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"[Antigravity] fetchAvailableModels 返回 {resp.status_code}")
        return []

    models_data = resp.json().get("models", {})

    # 过滤废弃/内部模型
    SKIP_PREFIX = ("gemini-2.5", "chat_", "tab_", "gpt-oss-")
    filtered = {}
    for name, info in models_data.items():
        if any(name.startswith(p) for p in SKIP_PREFIX):
            continue
        filtered[name] = info

    # 分组模型
    groups = {
        'Claude': [],
        'Gemini Pro': [],
        'Gemini Flash': [],
    }
    
    for name, info in filtered.items():
        display = info.get("displayName", name)
        quota = info.get("quotaInfo", {})
        remaining_frac = quota.get("remainingFraction")
        remaining = remaining_frac * 100 if remaining_frac is not None else 0
        used_pct = max(0, int(100 - remaining))
        
        # 分类模型
        if 'Claude' in display:
            groups['Claude'].append((display, used_pct, remaining))
        elif 'Pro' in display:
            groups['Gemini Pro'].append((display, used_pct, remaining))
        elif 'Flash' in display:
            groups['Gemini Flash'].append((display, used_pct, remaining))
    
    # 显示分组后的平均使用情况
    services = []
    for group_name, models in groups.items():
        if models:
            # 计算平均剩余百分比
            avg_remaining = sum(m[2] for m in models) / len(models)
            avg_used = 100 - avg_remaining
            
            services.append({
                "name": group_name,
                "used": int(avg_used),
                "limit": 100,
            })
            print(f"[Antigravity] {group_name}: {avg_remaining:.0f}% remaining (live)")
    
    return services


def fetch_antigravity_usage():
    """通过 Google Cloud Code Assist API 实时获取配额，fallback 到本地缓存。"""
    account = load_antigravity_account()
    if not account:
        print("[Antigravity] 未找到账号文件")
        return []

    # 优先使用本地缓存数据（更准确）
    quota = account.get("quota", {})
    models = quota.get("models", [])
    if models:
        tier = quota.get("subscription_tier", "?")
        # 过滤废弃模型 (gemini-2.5-*)
        models = [m for m in models if "gemini-2.5" not in m.get("name", "")]

        # 分组模型
        groups = {
            'Claude': [],
            'Gemini Pro': [],
            'Gemini Flash': [],
        }
        
        for m in models:
            display = m.get("display_name", m.get("name", "?"))
            remaining = m.get("percentage")
            remaining_val = remaining if remaining is not None else 0
            used_pct = max(0, 100 - int(remaining_val))
            
            # 分类模型
            if 'Claude' in display:
                groups['Claude'].append((display, used_pct, remaining_val))
            elif 'Pro' in display:
                groups['Gemini Pro'].append((display, used_pct, remaining_val))
            elif 'Flash' in display:
                groups['Gemini Flash'].append((display, used_pct, remaining_val))
        
        # 显示分组后的平均使用情况
        services = []
        for group_name, models in groups.items():
            if models:
                # 计算平均剩余百分比
                avg_remaining = sum(m[2] for m in models) / len(models)
                avg_used = 100 - avg_remaining
                
                services.append({
                    "name": group_name,
                    "used": int(avg_used),
                    "limit": 100,
                })
                print(f"[Antigravity] {group_name}: {avg_remaining:.0f}% remaining (cached)")
        
        if services:
            return services

    # 如果缓存数据不存在，尝试实时API
    print("[Antigravity] 缓存数据不存在，尝试实时API...")
    return fetch_antigravity_live(account)


# ── 主逻辑 ─────────────────────────────────────────────────────

def fetch_all():
    print("── 获取用量 ──")
    services = []

    print("\n▸ OpenAI / Codex:")
    services.extend(fetch_openai_usage())

    print("\n▸ Antigravity:")
    services.extend(fetch_antigravity_usage())

    if not services:
        print("\n⚠ 未获取到任何服务数据")
    else:
        total = len(services)
        print(f"\n── 共 {total} 个服务 ──")
    return services


def push_to_esp32(host, services):
    payload = {"services": services}
    url = f"http://{host}/token"
    try:
        resp = requests.post(url, json=payload, timeout=5)
        print(f"ESP32 [{resp.status_code}]: {resp.text.strip()}")
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"✗ 无法连接 {host}，请确认 ESP32 在同一网络")
        return False
    except requests.exceptions.Timeout:
        print(f"✗ 连接 {host} 超时")
        return False


def run_loop(host, once=False, print_only=False):
    """主循环：周期性获取数据并推送到 ESP32"""
    consecutive_failures = 0
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"\n{'─' * 40}")
        print(f"[{now}] 获取用量...")
        
        services = fetch_all()
        if not services:
            consecutive_failures += 1
            if consecutive_failures >= 5:
                print(f"[{now}] ⚠ 连续 {consecutive_failures} 次获取失败")
            wait = min(60 + consecutive_failures * 30, 300)
            print(f"[{now}] 等待 {wait}s 后重试...")
            time.sleep(wait)
            continue
        
        consecutive_failures = 0
        
        if print_only:
            print(json.dumps({"services": services}, indent=2))
        else:
            push_to_esp32(host, services)
        
        if once:
            break
        
        interval = random.randint(60, 180)
        next_time = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{next_time}] 下次刷新: {interval}s ({interval // 60}m{interval % 60:02d}s)")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(
        description="获取 AI 服务用量并推送到 ESP32 天气时钟",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python3 push_token.py                     循环获取并推送 (1~3分钟随机间隔)
  python3 push_token.py --once              仅执行一次
  python3 push_token.py --once --print       仅执行一次，打印 JSON
  python3 push_token.py --list "ChatGPT,45,100;Claude,20,100"
        """,
    )
    parser.add_argument("--host", default="sd3.local", help="ESP32 地址 (默认: sd3.local)")
    parser.add_argument("-f", "--file", help="JSON 文件路径")
    parser.add_argument("--inline", help="内联 JSON 字符串")
    parser.add_argument("--list", help="逗号分隔: name,used,limit;name,used,limit;...")
    parser.add_argument("--fetch", action="store_true", help="自动从本地配置文件获取用量 (默认行为)")
    parser.add_argument("--once", action="store_true", help="仅执行一次 (默认循环)")
    parser.add_argument("--print", action="store_true", help="仅打印 JSON, 不推送")
    args = parser.parse_args()

    # --list / --file / --inline 模式: 单次执行
    if args.file or args.inline or args.list:
        if args.file:
            with open(args.file) as f:
                payload = json.load(f)
        elif args.inline:
            payload = json.loads(args.inline)
        elif args.list:
            services = []
            for item in args.list.strip(";").split(";"):
                parts = item.strip().split(",")
                if len(parts) >= 3:
                    services.append({
                        "name": parts[0].strip(),
                        "used": int(parts[1].strip()),
                        "limit": int(parts[2].strip()),
                    })
            payload = {"services": services}
        
        if args.print:
            print(json.dumps(payload, indent=2))
        else:
            push_to_esp32(args.host, payload["services"])
        return

    # 默认: 循环获取并推送
    run_loop(host=args.host, once=args.once, print_only=args.print)


if __name__ == "__main__":
    main()
