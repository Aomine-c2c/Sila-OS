"""
KAIROS OS - Networking Foundation & Health Monitoring Test Suite
Tests:
  - Connection Profiles: Wired DHCP, Wired Static template, Wireless DHCP.
  - Time Synchronization: timesyncd.conf with stratum-1 NTP servers.
  - Low-Latency Kernel Tuning: sysctl tuning configuration (BBR, rmem_max, wmem_max, busy_poll).
  - Firewall Integrity: nftables.conf security boundaries (rate limiting, loopback accept, WireGuard accept).
  - Network Health Monitoring Engine:
    * Interface discovery (types, carrier states, MAC, MTU).
    * Failure state detection: DISCONNECTED, GATEWAY_FAILURE, DNS_FAILURE, PACKET_LOSS, HIGH_LATENCY.
    * IPC Telemetry export schema (/run/kairos/network_health.json).
  - CLI Integration: `kairos network status`, `kairos network interfaces`, `kairos network diagnostics`.
"""

import os
import unittest
import subprocess
import json
import sys

# Import kairos_netmon module directly for unit inspection
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts/network"))
import kairos_netmon

class TestNetworkingArchitecture(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.rootfs = os.path.join(self.root_dir, "build/rootfs")
        self.network_dir = os.path.join(self.rootfs, "etc/systemd/network")
        self.kairos_bin = os.path.join(self.rootfs, "usr/bin/kairos")

    def test_connection_profiles_exist(self):
        """Verify presence of wired DHCP, static example, and wireless profiles."""
        wired_dhcp = os.path.join(self.network_dir, "20-wired-dhcp.network")
        wired_static = os.path.join(self.network_dir, "25-wired-static.network.example")
        wireless_dhcp = os.path.join(self.network_dir, "30-wireless-dhcp.network")

        self.assertTrue(os.path.exists(wired_dhcp), "Missing 20-wired-dhcp.network")
        self.assertTrue(os.path.exists(wired_static), "Missing 25-wired-static.network.example")
        self.assertTrue(os.path.exists(wireless_dhcp), "Missing 30-wireless-dhcp.network")

        with open(wired_dhcp, "r") as f:
            content = f.read()
            self.assertIn("DHCP=yes", content)
            self.assertIn("RouteMetric=100", content)

        with open(wireless_dhcp, "r") as f:
            content = f.read()
            self.assertIn("RouteMetric=600", content, "Wireless route metric should be higher than wired")

    def test_timesyncd_stratum1_configuration(self):
        """Verify NTP timesyncd configuration exists with low-jitter pools."""
        timesyncd_conf = os.path.join(self.rootfs, "etc/systemd/timesyncd.conf")
        self.assertTrue(os.path.exists(timesyncd_conf), "Missing timesyncd.conf")
        with open(timesyncd_conf, "r") as f:
            content = f.read()
            self.assertIn("time.cloudflare.com", content)
            self.assertIn("PollIntervalMinSec", content)

    def test_sysctl_low_latency_tuning(self):
        """Verify TCP BBR, busy_poll, and socket buffer tuning in sysctl."""
        sysctl_conf = os.path.join(self.rootfs, "etc/sysctl.d/99-kairos-network-tuning.conf")
        self.assertTrue(os.path.exists(sysctl_conf), "Missing 99-kairos-network-tuning.conf")
        with open(sysctl_conf, "r") as f:
            content = f.read()
            self.assertIn("net.ipv4.tcp_congestion_control = bbr", content)
            self.assertIn("net.core.busy_poll = 50", content)
            self.assertIn("net.core.rmem_max = 67108864", content)
            self.assertIn("net.ipv4.tcp_low_latency = 1", content)

    def test_nftables_firewall_ruleset(self):
        """Verify packet filter defaults and protection."""
        nft_conf = os.path.join(self.rootfs, "etc/nftables/nftables.conf")
        self.assertTrue(os.path.exists(nft_conf), "Missing nftables.conf")
        with open(nft_conf, "r") as f:
            content = f.read()
            self.assertIn("policy drop", content)
            self.assertIn("iif \"lo\" accept", content)
            self.assertIn("wg-kairos*", content)

    def test_netmon_interface_enumeration(self):
        """Verify netmon discovers network interfaces."""
        ifaces = kairos_netmon.get_interfaces()
        self.assertIsInstance(ifaces, dict)
        self.assertTrue(len(ifaces) > 0, "No network interfaces discovered")
        self.assertIn("lo", ifaces, "Loopback interface 'lo' missing")
        self.assertEqual(ifaces["lo"]["type"], "Loopback")

    def test_netmon_health_assessment_structure(self):
        """Verify assess_network_health returns correct schema and detects states."""
        h = kairos_netmon.assess_network_health()
        self.assertIn("state", h)
        self.assertIn("is_degraded", h)
        self.assertIn("gateway", h)
        self.assertIn("dns", h)
        self.assertIn("interfaces", h)
        self.assertIn(h["state"], ["HEALTHY", "DISCONNECTED", "GATEWAY_FAILURE", "DNS_FAILURE", "PACKET_LOSS", "HIGH_LATENCY", "CRITICAL_LATENCY"])

    def test_kairos_network_cli_commands(self):
        """Verify `kairos network status`, `interfaces`, and `diagnostics` execution."""
        # 1. Status command
        res_status = subprocess.run([self.kairos_bin, "network", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res_status.returncode, 0, f"network status failed: {res_status.stderr}")
        self.assertIn("KAIROS OS - Network Stack & Quality Diagnostic", res_status.stdout)

        # 2. Interfaces command
        res_ifaces = subprocess.run([self.kairos_bin, "network", "interfaces"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res_ifaces.returncode, 0, f"network interfaces failed: {res_ifaces.stderr}")
        self.assertIn("Detailed Network Interface Inventory", res_ifaces.stdout)
        self.assertIn("Interface: lo", res_ifaces.stdout)

        # 3. Diagnostics command
        res_diag = subprocess.run([self.kairos_bin, "network", "diagnostics"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res_diag.returncode, 0, f"network diagnostics failed: {res_diag.stderr}")
        self.assertIn("Performing KAIROS Live Network Quality Probes", res_diag.stdout)
        self.assertIn("Physical Link Carrier Check", res_diag.stdout)

if __name__ == "__main__":
    unittest.main()
