#!/usr/bin/env python3
import requests
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Push token plan usage data to ESP32 weather clock"
    )
    parser.add_argument(
        "--host", default="sd3.local",
        help="ESP32 hostname or IP (default: sd3.local)"
    )
    parser.add_argument(
        "--file", "-f",
        help="JSON file path containing token data"
    )
    parser.add_argument(
        "--inline",
        help='Inline JSON string, e.g. \'{"services":[{"name":"OpenAI","used":150000,"limit":500000}]}\''
    )
    parser.add_argument(
        "--list",
        help="Comma-separated list: name,used,limit;name,used,limit;...",
    )
    args = parser.parse_args()

    payload = {}

    if args.file:
        with open(args.file, "r") as f:
            payload = json.load(f)
    elif args.inline:
        payload = json.loads(args.inline)
    elif args.list:
        services = []
        for item in args.list.strip(";").split(";"):
            parts = item.strip().split(",")
            if len(parts) == 3:
                services.append({
                    "name": parts[0].strip(),
                    "used": int(parts[1].strip()),
                    "limit": int(parts[2].strip()),
                })
        payload = {"services": services}
    else:
        parser.print_help()
        print("\nExample usage:")
        print('  python3 push_token.py --inline \'{"services":[{"name":"OpenAI","used":150000,"limit":500000}]}\'')
        print('  python3 push_token.py --list "OpenAI,150000,500000;Anthropic,80000,200000"')
        print('  python3 push_token.py -f data.json')
        sys.exit(1)

    url = f"http://{args.host}/token"
    try:
        resp = requests.post(url, json=payload, timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 200:
            print("Token data pushed successfully!")
        else:
            print("Failed to push token data.")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to {args.host}")
        print("Make sure the ESP32 is on the same network and the web server is running.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Error: Connection to {args.host} timed out")
        sys.exit(1)


if __name__ == "__main__":
    main()
