# KAIROS OS Network Architecture & Health Telemetry Specification

## 1. Overview & Low-Latency Design
KAIROS OS networking is engineered to provide **predictable, sub-millisecond network latency** for financial trading execution, market data feeds, and quantitative research.

### Core Networking Invariants:
1. **Separation of Concerns**: The network substrate remains strictly independent from trading business logic. Network monitoring, interface management, and route resolution happen at the OS layer.
2. **Degraded Connectivity Detection**: Trading services (`kairos-riskd`, execution gateways) must be able to instantaneously query network health without issuing blocking network requests. Telemetry is exported atomically via `/run/kairos/network_health.json`.
3. **Deterministic Interface Prioritization**: Wired interfaces (`en*`, `eth*`) always take routing precedence over wireless links (`wl*`) through route metric weighting (Metric 100 vs Metric 600).
4. **Jitter-Free Time Synchronization**: High-precision timekeeping via `systemd-timesyncd` synchronized against low-jitter Stratum-1 NTP pools.

---

## 2. Connection Profiles & Dual-Stack Strategy

Profiles are managed declaratively via `systemd-networkd` under `/etc/systemd/network/`:

### 2.1. Wired Ethernet (DHCP Default) - `20-wired-dhcp.network`
- **Matches**: `en* eth*`
- **Addressing**: DHCPv4 and SLAAC / DHCPv6 with kernel IPv6 privacy extensions (`use_tempaddr = 2`).
- **Routing Metric**: `100` (High Priority).
- **Multicast**: Enabled by default for financial market data ingestion.

### 2.2. Wired Static IP - `25-wired-static.network.example`
- Template for deterministic static colocated setups.
- Pre-configured with dual DNS fallbacks (`1.1.1.1`, `9.9.9.9`) and static IPv4/IPv6 routes.

### 2.3. Wireless / Wi-Fi - `30-wireless-dhcp.network`
- **Matches**: `wl*`
- **Addressing**: DHCPv4 and SLAAC / DHCPv6.
- **Routing Metric**: `600` (Secondary Fallback).
- Automatically yields to wired connections when Ethernet is plugged in.

---

## 3. Kernel Socket & TCP Tuning (`99-kairos-network-tuning.conf`)

KAIROS tunes the Linux networking stack for financial data ingestion:

| Kernel Parameter | Setting | Trading Rationale |
|---|---|---|
| `net.core.default_qdisc` | `fq` | Fair Queueing packet scheduling prevents bufferbloat. |
| `net.ipv4.tcp_congestion_control` | `bbr` | Google BBR optimizes throughput and minimizes queueing delay. |
| `net.core.busy_read` / `busy_poll` | `50` | Low-latency socket polling in kernel space (reduces interrupt latency). |
| `net.core.rmem_max` / `wmem_max` | `64 MiB` | Prevents packet drops during high-volume market tick bursts. |
| `net.core.netdev_max_backlog` | `250000` | Deep device backlog for bursts of multicast traffic. |
| `net.ipv4.tcp_low_latency` | `1` | Disables TCP prequeue processing in favor of immediate execution. |

---

## 4. Network Health Monitoring Subsystem (`kairos-netmon`)

The autonomous monitoring engine continuously evaluates 5 distinct network failure and degradation states:

```
+-------------------------------------------------------------------------+
|                  KAIROS Network Monitor (kairos-netmon)                 |
+-------------------------------------------------------------------------+
       |                     |                     |                     |
       v                     v                     v                     v
[Physical Link Check]  [Gateway Probe]    [DNS Benchmark]     [Jitter/Loss Probe]
Carrier detection      ARP / ICMP probe   Query benchmark     RTT & drop counters
       |                     |                     |                     |
       +---------------------+---------------------+---------------------+
                                     |
                                     v
                  +-------------------------------------+
                  |   Aggregate State Classification:   |
                  |   - HEALTHY                         |
                  |   - DISCONNECTED                    |
                  |   - GATEWAY_FAILURE                 |
                  |   - DNS_FAILURE                     |
                  |   - HIGH_LATENCY                    |
                  |   - PACKET_LOSS                     |
                  +-------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|              Atomic IPC Export: /run/kairos/network_health.json         |
|  Trading daemons consume this non-blocking state to adjust order risks  |
+-------------------------------------------------------------------------+
```

### Telemetry JSON Schema:
```json
{
  "timestamp": 1726315800.0,
  "state": "HEALTHY",
  "is_degraded": false,
  "reasons": [],
  "gateway": {
    "ip": "192.168.1.1",
    "interface": "eth0",
    "rtt_ms": 1.25,
    "loss_pct": 0.0
  },
  "dns": {
    "resolution_ok": true,
    "resolved_ip": "1.1.1.1",
    "latency_ms": 12.4
  },
  "interfaces": {
    "eth0": {
      "type": "Wired (Ethernet)",
      "operstate": "up",
      "carrier": true,
      "mac": "00:15:5d:17:42:20",
      "speed": "10000 Mbps",
      "mtu": 1500,
      "ipv4": ["192.168.1.150/24"],
      "ipv6": ["fe80::.../64"]
    }
  }
}
```

---

## 5. CLI Operations

### 1. `kairos network status`
Displays the overall health state, trading quality grade, default gateway latency, packet loss, and active interface summaries.

### 2. `kairos network interfaces`
Enumerates all network interfaces, link states, carriers, MACs, link speeds, MTUs, and assigned IPv4/IPv6 addresses.

### 3. `kairos network diagnostics`
Executes real-time live probes checking physical carrier, gateway reachability, latency jitter, and DNS resolution benchmarks.
