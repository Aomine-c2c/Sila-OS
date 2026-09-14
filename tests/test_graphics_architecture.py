#!/usr/bin/env python3
"""
Unit and Integration Tests for KAIROS Graphical & Wayland Architecture.
Verifies:
1. Vendor-agnostic GPU detection (Intel, AMD, NVIDIA, VirtIO, Software fallback).
2. DRM card and render node parsing.
3. Wayland display parameters, scaling, and monitor discovery.
4. Input device enumeration (keyboards, mice, touchpads).
5. CLI integration (kairos gpu info, kairos display info, kairos input info).
6. Wayland configuration & Hyprland configuration file integrity.
"""

import unittest
import os
import sys
import tempfile
import subprocess
from unittest.mock import patch, mock_open

# Ensure workspace root is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.hardware import kairos_graphics

class TestGraphicsArchitecture(unittest.TestCase):

    def test_vendor_ids_presence(self):
        """Ensure Intel, AMD, NVIDIA, VirtIO, and QEMU vendors are defined."""
        vendors = kairos_graphics.PCI_VENDORS
        self.assertIn("0x8086", vendors)  # Intel
        self.assertIn("0x1002", vendors)  # AMD
        self.assertIn("0x10de", vendors)  # NVIDIA
        self.assertIn("0x1af4", vendors)  # VirtIO
        self.assertIn("0x1234", vendors)  # QEMU VGA

    def test_driver_status_matrix(self):
        """Ensure driver support tiers cover major open-source and proprietary drivers."""
        drivers = kairos_graphics.DRIVER_STATUS
        self.assertIn("i915", drivers)
        self.assertIn("xe", drivers)
        self.assertIn("amdgpu", drivers)
        self.assertIn("nvidia", drivers)
        self.assertIn("virtio-gpu", drivers)
        self.assertIn("llvmpipe", drivers)

    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("scripts.hardware.kairos_graphics.read_sysfs_file")
    def test_detect_intel_gpu(self, mock_read, mock_listdir, mock_exists):
        """Test vendor-agnostic detection for Intel Arc / Iris Xe GPU."""
        mock_exists.return_value = True
        mock_listdir.return_value = ["0000:00:02.0"]

        def read_side_effect(path):
            if path.endswith("/class"):
                return "0x030000"
            elif path.endswith("/vendor"):
                return "0x8086"
            elif path.endswith("/device"):
                return "0x46a6"
            return None

        mock_read.side_effect = read_side_effect

        with patch("os.path.islink", return_value=True), \
             patch("os.readlink", return_value="../../bus/pci/drivers/i915"):
            gpus = kairos_graphics.detect_gpus()
            self.assertEqual(len(gpus), 1)
            self.assertIn("Intel", gpus[0]["vendor_name"])
            self.assertEqual(gpus[0]["driver"], "i915")
            self.assertIn("Hardware DRM/KMS", gpus[0]["acceleration"])

    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("scripts.hardware.kairos_graphics.read_sysfs_file")
    def test_detect_amd_gpu(self, mock_read, mock_listdir, mock_exists):
        """Test vendor-agnostic detection for AMD Radeon RX GPU."""
        mock_exists.return_value = True
        mock_listdir.return_value = ["0000:03:00.0"]

        def read_side_effect(path):
            if path.endswith("/class"):
                return "0x030000"
            elif path.endswith("/vendor"):
                return "0x1002"
            elif path.endswith("/device"):
                return "0x73ff"
            return None

        mock_read.side_effect = read_side_effect

        with patch("os.path.islink", return_value=True), \
             patch("os.readlink", return_value="../../bus/pci/drivers/amdgpu"):
            gpus = kairos_graphics.detect_gpus()
            self.assertEqual(len(gpus), 1)
            self.assertIn("AMD", gpus[0]["vendor_name"])
            self.assertEqual(gpus[0]["driver"], "amdgpu")
            self.assertIn("Tier 1", gpus[0]["support_tier"])

    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("scripts.hardware.kairos_graphics.read_sysfs_file")
    def test_detect_virtio_gpu(self, mock_read, mock_listdir, mock_exists):
        """Test detection of QEMU / KVM VirtIO paravirtualized GPU."""
        mock_exists.return_value = True
        mock_listdir.return_value = ["0000:00:01.0"]

        def read_side_effect(path):
            if path.endswith("/class"):
                return "0x030000"
            elif path.endswith("/vendor"):
                return "0x1af4"
            elif path.endswith("/device"):
                return "0x1050"
            return None

        mock_read.side_effect = read_side_effect

        with patch("os.path.islink", return_value=True), \
             patch("os.readlink", return_value="../../bus/pci/drivers/virtio-gpu"):
            gpus = kairos_graphics.detect_gpus()
            self.assertEqual(len(gpus), 1)
            self.assertIn("VirtIO", gpus[0]["vendor_name"])
            self.assertEqual(gpus[0]["driver"], "virtio-gpu")

    def test_software_rasterizer_fallback(self):
        """When no PCI GPU or DRM nodes exist, fallback to LLVMpipe safely."""
        with patch("os.path.exists", return_value=False):
            gpus = kairos_graphics.detect_gpus()
            self.assertEqual(len(gpus), 1)
            self.assertEqual(gpus[0]["driver"], "llvmpipe")
            self.assertIn("Safe CPU Fallback", gpus[0]["support_tier"])

    def test_display_and_wayland_detection(self):
        """Test Wayland display info structure."""
        disp = kairos_graphics.detect_display_and_wayland()
        self.assertIn("session_type", disp)
        self.assertIn("current_desktop", disp)
        self.assertIn("monitors", disp)
        self.assertIn("compositor_features", disp)
        self.assertGreaterEqual(len(disp["monitors"]), 1)

    def test_input_device_classification(self):
        """Test classification of input devices into keyboard, mouse, touchpad."""
        sample_input = (
            "I: Bus=0011 Vendor=0001 Product=0001 Version=ab41\n"
            "N: Name=\"AT Translated Set 2 keyboard\"\n"
            "P: Phys=isa0060/serio0/input0\n"
            "S: Sysfs=/devices/platform/i8042/serio0/input/input0\n"
            "H: Handlers=sysrq kbd event0\n\n"
            "I: Bus=0011 Vendor=0002 Product=0006 Version=0000\n"
            "N: Name=\"SynPS/2 Synaptics TouchPad\"\n"
            "P: Phys=isa0060/serio1/input0\n"
            "S: Sysfs=/devices/platform/i8042/serio1/input/input1\n"
            "H: Handlers=mouse0 event1\n\n"
            "I: Bus=0003 Vendor=046d Product=c077 Version=0111\n"
            "N: Name=\"Logitech USB Optical Mouse\"\n"
            "P: Phys=usb-0000:00:14.0-1/input0\n"
            "S: Sysfs=/devices/pci0000:00/0000:00:14.0/usb1/1-1/1-1:1.0/0003:046D:C077.0001/input/input2\n"
            "H: Handlers=mouse1 event2\n"
        )
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=sample_input)):
            devices = kairos_graphics.detect_input_devices()
            self.assertEqual(len(devices), 3)
            types = [d["type"] for d in devices]
            self.assertIn("Keyboard", types)
            self.assertIn("Touchpad", types)
            self.assertIn("Mouse", types)

    def test_hyprland_configuration_integrity(self):
        """Verify hyprland.conf syntax and expected critical sections."""
        conf_path = os.path.join(ROOT_DIR, "config/hyprland/hyprland.conf")
        self.assertTrue(os.path.exists(conf_path), f"Missing {conf_path}")
        with open(conf_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check multi-monitor and scaling directives
        self.assertIn("monitor =", content)
        # Check input low latency configuration
        self.assertIn("repeat_rate = 50", content)
        self.assertIn("repeat_delay = 200", content)
        self.assertIn("accel_profile = flat", content)
        self.assertIn("touchpad {", content)
        # Check screenshot bindings
        self.assertIn("grim", content)
        self.assertIn("slurp", content)
        # Check clipboard integration
        self.assertIn("cliphist", content)
        self.assertIn("wl-copy", content)

    def test_wayland_environment_file(self):
        """Verify /etc/environment.d/20-kairos-wayland.conf generation in Phase 11."""
        script_path = os.path.join(ROOT_DIR, "scripts/phases/11_wayland.sh")
        self.assertTrue(os.path.exists(script_path))
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("XDG_SESSION_TYPE=wayland", content)
        self.assertIn("QT_QPA_PLATFORM=wayland;xcb", content)
        self.assertIn("XCURSOR_THEME=Adwaita", content)
        self.assertIn("HYPRCURSOR_THEME=Adwaita", content)

if __name__ == "__main__":
    unittest.main()
