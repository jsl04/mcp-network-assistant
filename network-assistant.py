#!/usr/bin/env python3
"""network-assistant-dnac.py
Lightweight helper that logs into Cisco Catalyst Center (DNA Center) and prints
a concise summary of devices, client health, and fabric domains.

Usage:
  python3 network-assistant-dnac.py \
      --dnac 198.18.128.100 \
      --username admin \
      --password Cisco123! \
      --verify False
"""

import argparse
import sys
from dnacentersdk import DNACenterAPI
from tabulate import tabulate


def parse_args():
    p = argparse.ArgumentParser(description="Catalyst Center Network Assistant")
    p.add_argument("--dnac", required=True, help="Catalyst Center IP or FQDN")
    p.add_argument("--username", default="admin")
    p.add_argument("--password", default="Cisco123!")
    p.add_argument("--verify", default="False", help="TLS cert verify True/False")
    return p.parse_args()


def main():
    args = parse_args()
    verify_flag = str(args.verify).lower() == "true"

    print(f"\nConnecting to Catalyst Center {args.dnac} ...")
    try:
        api = DNACenterAPI(
            base_url=f"https://{args.dnac}",
            username=args.username,
            password=args.password,
            verify=verify_flag,
            debug=False,
        )
    except Exception as exc:
        print(f"Authentication failed: {exc}")
        sys.exit(1)

    # 1. Device inventory
    devices = api.devices.get_device_list()["response"]
    rows = [
        [
            d.get("hostname") or d.get("managementIpAddress"),
            d.get("family"),
            d.get("platformId"),
            d.get("softwareVersion"),
        ]
        for d in devices
    ]
    print("\n### Inventory ###")
    print(tabulate(rows, headers=["Host", "Family", "Platform", "SW"], tablefmt="github"))

    # 2. Client health
    try:
        health = api.clients.get_overall_client_health()["response"]
        print("\n### Client Health ###")
        for h in health:
            cat = h["scoreCategory"]["value"]
            score = h.get("score")
            print(f"{cat:10s}: {score}")
    except Exception:
        print("Client health API not available on this version.")

    # 3. SDA fabric domains
    fabrics = api.sda.get_fabric_domain()["response"]
    print("\n### Fabric Domains ###")
    if fabrics:
        for f in fabrics:
            print(f"- {f['fabricName']}")
    else:
        print("No SDA fabric configured.")


if __name__ == "__main__":
    main()
