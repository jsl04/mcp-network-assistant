#!/usr/bin/env python3

import time, argparse
from dnacentersdk import DNACenterAPI
from mcp.server.fastmcp import FastMCP
import uvicorn

# ── CLI ────────────────────────────────────────────────────
p = argparse.ArgumentParser()
p.add_argument("--dnac", required=True)
p.add_argument("--username", required=True)
p.add_argument("--password", required=True)
p.add_argument("--port", type=int, default=8000)
p.add_argument("--mount-path", default="",   # ← NEW
               help="URL prefix ('' for root, default '')")
args = p.parse_args()

# ── Catalyst Center API ───────────────────────────────────
api = DNACenterAPI(
    base_url=f"https://{args.dnac}",
    username=args.username,
    password=args.password,
    version="2.3.7.6",
    verify=False,
)

# ── FastMCP app (root mount!) ─────────────────────────────
mcp = FastMCP("cisco_network_assistant", mount_path="/mcp")

def _device_map() -> dict[str, str]:
    """hostname → deviceUuid"""
    devs = api.devices.get_device_list()
    devs = devs.get("response", devs) if isinstance(devs, dict) else devs
    return {d["hostname"]: d["id"] for d in devs or []}
  
@mcp.tool()
async def compliance_summary(hostname: str | None = None) -> list[dict] | dict:
    """
    If hostname is None → return every device.
    If hostname is given  → return that device's compliance entry or
                             {"message":"<host> not found / no data"}.
    """
    def safe(v): return None if v is None else str(v)

    try:
        resp = api.compliance.get_device_compliance()
        items = resp.get("response", resp)
    except AttributeError:
        r = api._session.get("/compliance/device")  # leading slash matters
        if not r.text:
            items = []          # 204 No Content
        else:
            items = r.json().get("response", [])

    if not items:
        return {"message": "Catalyst Center returned no compliance data."}

    rows = [
        {
            "hostname":    safe(d.get("deviceName")),
            "status":      safe(d.get("complianceStatus")),
            "failedRules": safe(d.get("nonCompliantRuleCount")),
        }
        for d in items
    ]

    if hostname is None:
        return rows

    # filter for a single device
    for row in rows:
        if row["hostname"] == hostname:
            return [row]
    return {"message": f"No compliance data for '{hostname}'."}

import difflib, time, math

@mcp.tool()
async def config_drift(hostname: str, hours_back: int = 24) -> dict:
    """
    Diff the current config vs. the snapshot 'hours_back' ago.
    Returns {"added": int, "removed": int, "sample": "..." }
    If no earlier snapshot → message field instead.
    """
    uuid = _device_map().get(hostname)
    if not uuid:
        return {"message": f"Device '{hostname}' not found."}

    now_ms = int(time.time()*1000)
    # CC keeps configs with epochMs timestamps; round to closest minute
    past_ms = now_ms - hours_back*3600*1000
    past_ms = math.floor(past_ms / 60_000) * 60_000

    try:
        cur = api.network_device.get_device_config_by_uuid(uuid)["response"]
        old = api.network_device.get_device_config_by_uuid(uuid, timestamp=past_ms)["response"]
    except Exception as exc:
        return {"message": f"No snapshot ~{hours_back}h ago: {exc}"}

    cur_lines = cur.splitlines()
    old_lines = old.splitlines()
    diff = list(difflib.unified_diff(old_lines, cur_lines, n=0))

    added = sum(1 for l in diff if l.startswith("+ ") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("- ") and not l.startswith("---"))

    # return only first 20 diff lines so the payload stays small
    sample = "\n".join(diff[:20])

    return {"added": added, "removed": removed, "sample": sample}

@mcp.tool()
async def inventory() -> list[dict]:
    """Return Catalyst Center device inventory (JSON-safe)."""
    raw = api.devices.get_device_list()
    raw = raw.get("response", raw) if isinstance(raw, dict) else raw

    safe = lambda v: None if v is None else str(v)

    cleaned = []
    for d in raw or []:
        cleaned.append({
            "hostname":   safe(d.get("hostname") or d.get("managementIpAddress")),
            "ip":         safe(d.get("managementIpAddress")),
            "family":     safe(d.get("family")),
            "platform":   safe(d.get("platformId")),
            "sw_version": safe(d.get("softwareVersion")),
            "serial":     safe(d.get("serialNumber")),
            "uptime":     safe(d.get("upTime")),           # often Decimal
            "last_upd":   safe(d.get("lastUpdated")),      # datetime
        })
    return cleaned

@mcp.tool()
async def client_health() -> list[dict] | dict:
    """
    Overall client health, JSON-friendly.
    If Catalyst Center has no data, return a short explanatory dict.
    """
    import math, time
    ts_now = int(time.time() * 1000)

    def fetch(ts_ms):
        resp = api.clients.get_overall_client_health(timestamp=ts_ms)
        return resp.get("response", resp) if isinstance(resp, dict) else resp

    data = fetch(ts_now)
    if not data:
        # fallback to previous 5-minute bucket
        bucket = math.floor(ts_now / 300_000) * 300_000
        data = fetch(bucket)

    if not data or all(e.get("score") is None for e in data):
        return {"message": "No client-health samples in the last 5 minutes."}

    safe = lambda v: None if v is None else str(v)
    return [
        {
            "score":     safe(e.get("score")),
            "category":  safe(e.get("category")),
            "total":     safe(e.get("totalCount")),
            "healthy":   safe(e.get("healthyCount")),
            "unhealthy": safe(e.get("unHealthyCount")),
            "time":      safe(e.get("timestamp")),
        }
        for e in data
    ]
@mcp.tool()
async def sda_fabrics() -> list[dict]:
    resp = api.sda.get_fabric_sites()
    data = resp.get("response", resp)
    return [
        {"id": d.get("id"), "name": d.get("siteNameHierarchy")}
        for d in data or []
    ]

# ── Serve with uvicorn on 0.0.0.0:8000 ────────────────────
mcp.run(transport="streamable-http") 
