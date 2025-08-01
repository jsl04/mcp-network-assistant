# Cisco Network Assistant MCP Tools Reference

*Generated 2025-08-01 00:01 UTC*

This document describes the JSON-over-HTTP tools exposed by the **Cisco Network Assistant MCP server** so that retrieval‑augmented generation (RAG) systems such as Claude Desktop or LM Studio can call them reliably.

---

## 1  Base URL

| Environment | Example URL |
|-------------|-------------|
| Direct FastMCP (lab) | `http://serverip:8000/mcp` |
| Via nginx proxy (port 4242) | `http://serverip:4242/mcp` |

All tools are simple **HTTP GET** (or **POST JSON** when arguments are required) beneath that prefix.

---

## 2  Tool Catalogue

| Tool name | Method | Arguments (JSON) | Returns |
|-----------|--------|------------------|---------|
| `inventory` | `GET /inventory` | _none_ | `[{hostname, ip, family, platform, sw_version, serial}]` |
| `client_health` | `GET /client_health` | _none_ | On success: list with `score, category, total, healthy, unhealthy, time`; if empty: `{{"message":"No client‑health samples in the last 5 minutes."}}` |
| `compliance_summary` | `GET /compliance_summary` | _none_ | `[{hostname, status, failedRules}]` |
| `sda_fabrics` | `GET /sda_fabrics` | _none_ | `[{id, name}]` |
| `sgt_catalog` | `GET /sgt_catalog` | _none_ | `[{id, name, value, desc}]` |
| `sgt_matrix` | `GET /sgt_matrix` | _none_ | `[{src, dst, rule}]` |
| `ise_live_radius` | `GET /ise_live_radius` | _none_ | recent RADIUS auths |
| `ise_endpoints` | `GET /ise_endpoints` | _none_ | current ISE endpoints |
| `config_drift` | `POST /config_drift` | `{{"hostname":"<host>","hours_back":<int>}}` | `{{"added":int,"removed":int,"sample":"..."}}` |

### Example — inventory

```http
GET /mcp/inventory HTTP/1.1
Host: 198.18.128.60:8000
```

```json
[
  {{
    "hostname": "cat9000v-uadp-0",
    "ip": "198.18.1.11",
    "family": "Switches and Hubs",
    "platform": "C9KV-UADP-8P",
    "sw_version": "17.15.1",
    "serial": "blank"
  }}
]
```

### Example — config_drift

```http
POST /mcp/config_drift HTTP/1.1
Content-Type: application/json
Host: 198.18.128.60:8000

{{"hostname":"cat8000v-0.lab.local","hours_back":24}}
```

```json
{{
  "added": 3,
  "removed": 0,
  "sample": "@@ -10,0 +11,3 @@\n+ntp server 198.18.133.20\n+ip ssh version 2\n+aaa authentication login default group radius\n"
}}
```

---

## 3  Error conventions

| Condition | Tool response |
|-----------|---------------|
| Empty upstream data | `{{"message":"No <x> samples in the last 5 minutes."}}` |
| Invalid input | `{{"message":"Device '<host>' not found."}}` |
| Upstream API exception | `{{"message":"<exception text>"}}` |

---

## 4  Adding new tools

1. Define an **async** function under the same `mcp` instance.
2. Ensure every value in the returned dict/list is a primitive or string.
3. Restart the MCP server; FastMCP auto‑registers it.

---

## 5  Security Notes

* MCP runs read-only REST calls—no config changes are made.
* Store ISE credentials as read‑only users.
* Use nginx/Caddy for HTTPS + port mapping in production.
