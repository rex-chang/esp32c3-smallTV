import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional, Any, cast

__version__ = "1.1.0"

class AntigravityUsageTool:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.platform = sys.platform
        self.pid: Optional[str] = None
        self.token: Optional[str] = None
        self.port: Optional[str] = None

    def log(self, message: str):
        if self.verbose:
            print(f"[DEBUG] {message}")

    def discover_server(self) -> bool:
        """从 language_server 进程提取 PID 和 CSRF Token"""
        self.log(f"Searching for server process on {self.platform}...")
        try:
            if self.platform == "win32":
                cmd = [
                    'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                    'Get-WmiObject Win32_Process -Filter "name LIKE \'language_server_windows_%\'" | Select-Object ProcessId, CommandLine | ConvertTo-Json'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                if not result.stdout.strip():
                    return False
                data = json.loads(result.stdout)
                if isinstance(data, list):
                    data = data[0]
                self.pid = str(data.get('ProcessId'))
                cmdline = data.get('CommandLine')
            else:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, check=True)
                cmdline = None
                for line in result.stdout.splitlines():
                    if 'language_server' in line and '--csrf_token' in line:
                        parts = line.split()
                        if len(parts) > 1:
                            self.pid = parts[1]
                            # ps aux: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                            # Command starts at field 11 (index 10)
                            base_idx = 10
                            cmdline = " ".join(parts[i] for i in range(base_idx, len(parts)))
                            break

            if not self.pid or not cmdline:
                return False

            self.log(f"Found process {self.pid}")

            # 提取 token 和 port
            s_cmdline = cast(str, cmdline)
            token_match = re.search(r'--csrf_token\s+([0-9a-fA-F-]+)', s_cmdline)
            port_match = re.search(r'--extension_server_port\s+(\d+)', s_cmdline)
            self.token = token_match.group(1) if token_match else None
            self.port = port_match.group(1) if port_match else None

            return self.token is not None
        except Exception as e:
            self.log(f"Discovery error: {e}")
            return False

    def get_listening_ports(self) -> List[str]:
        """获取进程监听的端口"""
        if not self.pid:
            return []
        ports = []
        try:
            if self.platform == "win32":
                result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, check=True)
                pattern = rf'TCP\s+(?:127\.0\.0\.1|0\.0\.0\.0):(\d+)\s+.*\s+LISTENING\s+{self.pid}'
                for match in re.finditer(pattern, result.stdout):
                    ports.append(match.group(1))
            else:
                try:
                    result = subprocess.run(['lsof', '-i', '-P', '-n', '-a', '-p', self.pid],
                                            capture_output=True, text=True, check=True)
                    for line in result.stdout.splitlines():
                        if 'LISTEN' in line:
                            m = re.search(r':(\d+)\s+', line)
                            if m:
                                ports.append(m.group(1))
                except Exception:
                    result = subprocess.run(['netstat', '-tunlp'], capture_output=True, text=True, check=True)
                    pattern = rf':(\d+)\s+.*\s+{self.pid}/'
                    for match in re.finditer(pattern, result.stdout):
                        ports.append(match.group(1))
            return list(set(ports))
        except Exception:
            return []

    def fetch_status(self, port: str) -> Optional[Dict[str, Any]]:
        """调用本地 GetUserStatus 接口"""
        url = f"http://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/GetUserStatus"
        headers = {
            "Content-Type": "application/json",
            "Connect-Protocol-Version": "1",
            "X-Codeium-Csrf-Token": cast(str, self.token)
        }
        payload = {"metadata": {"ideName": "antigravity", "extensionName": "antigravity", "locale": "en"}}
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception:
            return None

    @staticmethod
    def format_reset_time(reset_time_str: Optional[str]) -> str:
        if not reset_time_str:
            return "N/A"
        try:
            ts = reset_time_str.replace('Z', '+00:00')
            reset_time = datetime.fromisoformat(ts)
            # 转换为本地时区
            import time
            local_reset_time = reset_time.astimezone()
            now = datetime.now().astimezone()
            diff = local_reset_time - now
            if diff.total_seconds() <= 0:
                return "Ready"
            days, hours = diff.days, diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            # 格式化时间戳为 MM/DD HH:MM
            timestamp = local_reset_time.strftime("%m/%d %H:%M")
            if days > 0:
                return f"{days}d {hours}h ({timestamp})"
            if hours > 0:
                return f"{hours}h {minutes}m ({timestamp})"
            return f"{minutes}m ({timestamp})"
        except Exception:
            return "N/A"

    def run(self, output_json: bool = False):
        if not self.discover_server():
            print("Error: Could not find active Antigravity Language Server.")
            print("Hint: 请先打开 Antigravity IDE 并确保已登录。")
            sys.exit(1)

        ports = []
        if self.port:
            ports.append(self.port)
        ports.extend([p for p in self.get_listening_ports() if p not in ports])

        usage_data = None
        for port in ports:
            self.log(f"Testing port {port}...")
            res = self.fetch_status(port)
            if res and 'userStatus' in res:
                usage_data = res
                break

        if usage_data is None:
            print("Error: Failed to fetch status.")
            sys.exit(1)

        if output_json:
            print(json.dumps(usage_data, indent=2))
            return

        self.print_report(usage_data)

    def print_report(self, data: Dict[str, Any]):
        status = cast(Dict[str, Any], data['userStatus'])
        email = status.get('email', 'Unknown User')
        plan_status = status.get('planStatus', {})
        plan_info = plan_status.get('planInfo', {})
        tier = plan_info.get('planName', 'N/A')
        
        # 获取可用积分
        user_tier = status.get('userTier', {})
        available_credits = user_tier.get('availableCredits', [])
        total_credits = 0
        for credit in available_credits:
            credit_amount = credit.get('creditAmount', '0')
            try:
                total_credits += int(credit_amount)
            except ValueError:
                pass

        print(f"\n\033[1m{email}\033[0m")
        print(f"{'当前':>20} {'PRO':>10}")
        print(f"{'=' * 30}")

        cascade = cast(Dict[str, Any], status.get('cascadeModelConfigData', {}))
        configs = cast(List[Dict[str, Any]], cascade.get('clientModelConfigs', []))

        # 分组模型
        groups = {
            'Claude': [],
            'Gemini Pro': [],
            'Gemini Flash': [],
        }
        
        for cfg in configs:
            quota = cast(Optional[Dict[str, Any]], cfg.get('quotaInfo'))
            if not quota:
                continue
            label = str(cfg.get('label', 'Unknown Model'))
            rem_fraction = float(quota.get('remainingFraction', 1))
            reset_info = quota.get('resetTime')
            reset_in = self.format_reset_time(reset_info)
            pct = rem_fraction * 100
            bar_len = 20
            filled = int(rem_fraction * bar_len)
            bar = '█' * filled + '░' * (bar_len - filled)
            
            # 分类模型
            if 'Claude' in label:
                groups['Claude'].append((label, rem_fraction, reset_in))
            elif 'Pro' in label:
                groups['Gemini Pro'].append((label, rem_fraction, reset_in))
            elif 'Flash' in label:
                groups['Gemini Flash'].append((label, rem_fraction, reset_in))
        
        # 显示分组后的平均使用情况
        for group_name, models in groups.items():
            if models:
                avg_rem = sum(m[1] for m in models) / len(models)
                reset_in = models[0][2]  # 取第一个模型的重置时间
                pct = avg_rem * 100
                bar_len = 20
                filled = int(avg_rem * bar_len)
                bar = '█' * filled + '░' * (bar_len - filled)
                print(f"  {group_name}: {pct:.0f}%")
                print(f"    {reset_in}")
        
        print(f"\n  可用 AI 积分: {total_credits}")
        print(f"\n{'=' * 30}")

    @staticmethod
    def main():
        parser = argparse.ArgumentParser(description='Antigravity Usage Report Tool')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable debug output')
        parser.add_argument('-j', '--json', action='store_true', help='Output raw JSON')
        parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
        args = parser.parse_args()

        tool = AntigravityUsageTool(verbose=args.verbose)
        tool.run(output_json=args.json)


if __name__ == '__main__':
    AntigravityUsageTool.main()