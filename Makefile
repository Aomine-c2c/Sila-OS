# KAIROS OS - Autonomous Build & Engineering Orchestration
# Purpose-built operating system for Quantitative Researchers, Algorithmic Traders, and Market Operators.

SHELL := /bin/bash
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
BUILD_DIR ?= $(ROOT_DIR)/build
OUT_DIR ?= $(ROOT_DIR)/out
TOOLS_DIR ?= $(ROOT_DIR)/tools
SCRIPTS_DIR ?= $(ROOT_DIR)/scripts

.PHONY: all help check clean init-buildenv build-system linux-base kernel boot storage \
        users networking services hardware graphics wayland hyprland shell desktop \
        settings packages security update trading research plugins ai adaptive \
        installer iso test release-eng

all: check

help:
	@echo "================================================================================"
	@echo " KAIROS OS Build System"
	@echo "================================================================================"
	@echo " Available Targets:"
	@echo "   init-buildenv    Initialize build directory structures and tool requirements"
	@echo "   check            Run linters, static analyzers, and sanity verification"
	@echo "   build-all        Execute end-to-end OS construction sequence (phases 1-27)"
	@echo "   clean            Clean all build caches and ephemeral outputs"
	@echo "================================================================================"

init-buildenv:
	@mkdir -p $(BUILD_DIR) $(OUT_DIR) $(BUILD_DIR)/rootfs $(BUILD_DIR)/iso
	@python3 scripts/check_environment.py

check: init-buildenv
	@echo "[+] Running KAIROS architectural validation suite..."
	@python3 -m unittest discover -s tests -p "test_*.py"

build-system: init-buildenv
	@echo "[Phase 1/27] Building hermetic build toolchain and container harness..."
	@bash scripts/build_phase.sh 01_build_system

linux-base: build-system
	@echo "[Phase 2/27] Assembling base Linux rootfs and FHS..."
	@bash scripts/build_phase.sh 02_linux_base

kernel: linux-base
	@echo "[Phase 3/27] Compiling low-latency PREEMPT_RT kernel and sysctl tuning..."
	@bash scripts/build_phase.sh 03_kernel

boot: kernel
	@echo "[Phase 4/27] Generating EFI boot stanzas, GRUB2/systemd-boot, and UKI..."
	@bash scripts/build_phase.sh 04_boot

storage: boot
	@echo "[Phase 5/27] Setting up transactional filesystem layouts (ZFS/Btrfs)..."
	@bash scripts/build_phase.sh 05_storage

users: storage
	@echo "[Phase 6/27] Configuring user privilege separation & PAM authentication..."
	@bash scripts/build_phase.sh 06_users

networking: users
	@echo "[Phase 7/27] Applying network low-latency stack & nftables policies..."
	@bash scripts/build_phase.sh 07_networking

services: networking
	@echo "[Phase 8/27] Deploying core system daemons and telemetry monitors..."
	@bash scripts/build_phase.sh 08_services

hardware: services
	@echo "[Phase 9/27] Configuring hardware acceleration, microcode, and GPU drivers..."
	@bash scripts/build_phase.sh 09_hardware

graphics: hardware
	@echo "[Phase 10/27] Verifying DRM/KMS, Mesa, and Vulkan display stack..."
	@bash scripts/build_phase.sh 10_graphics

wayland: graphics
	@echo "[Phase 11/27] Building Wayland display server protocols & seat management..."
	@bash scripts/build_phase.sh 11_wayland

hyprland: wayland
	@echo "[Phase 12/27] Configuring Hyprland multi-monitor financial layout & rules..."
	@bash scripts/build_phase.sh 12_hyprland

shell: hyprland
	@echo "[Phase 13/27] Deploying KAIROS Shell, Waybar ticker ribbons, and status bars..."
	@bash scripts/build_phase.sh 13_kairos_shell

desktop: shell
	@echo "[Phase 14/27] Configuring desktop utilities, zero-latency terminals, & notifications..."
	@bash scripts/build_phase.sh 14_desktop_utils

settings: desktop
	@echo "[Phase 15/27] Compiling kairos-control system configuration utility..."
	@bash scripts/build_phase.sh 15_system_settings

packages: settings
	@echo "[Phase 16/27] Configuring package managers & application sandbox layers..."
	@bash scripts/build_phase.sh 16_package_management

security: packages
	@echo "[Phase 17/27] Enforcing MAC (AppArmor), TPM2, and immutable root protection..."
	@bash scripts/build_phase.sh 17_security

update: security
	@echo "[Phase 18/27] Setting up transactional A/B update & recovery mechanism..."
	@bash scripts/build_phase.sh 18_update_recovery

trading: update
	@echo "[Phase 19/27] Deploying core trading infrastructure & immutable Risk Gatekeeper..."
	@bash scripts/build_phase.sh 19_trading_services

research: trading
	@echo "[Phase 20/27] Provisioning quantitative research analytics & data environment..."
	@bash scripts/build_phase.sh 20_research_env

plugins: research
	@echo "[Phase 21/27] Building capability-sandboxed WASM/gRPC plugin system..."
	@bash scripts/build_phase.sh 21_plugin_infra

ai: plugins
	@echo "[Phase 22/27] Integrating local AI agent runtime (Risk-isolated)..."
	@bash scripts/build_phase.sh 22_ai_agents

adaptive: ai
	@echo "[Phase 23/27] Activating Adaptive Evolution Intelligence telemetry loops..."
	@bash scripts/build_phase.sh 23_adaptive_intelligence

installer: adaptive
	@echo "[Phase 24/27] Packaging KAIROS installer and storage partitioner..."
	@bash scripts/build_phase.sh 24_installer

iso: installer
	@echo "[Phase 25/27] Mastering bootable Live ISO..."
	@bash scripts/build_phase.sh 25_iso_generation

test: iso
	@echo "[Phase 26/27] Running automated end-to-end integration & QEMU boot tests..."
	@bash scripts/build_phase.sh 26_automated_testing

release-eng: test
	@echo "[Phase 27/27] Generating release checksums, SBOM, and signed artifacts..."
	@bash scripts/build_phase.sh 27_release_engineering

build-all: release-eng
	@echo "================================================================================"
	@echo " KAIROS OS Build Complete. Target artifacts located in $(OUT_DIR)"
	@echo "================================================================================"

clean:
	@rm -rf $(BUILD_DIR) $(OUT_DIR)
	@echo "Cleaned build artifacts."
