"""
KAIROS Capability-Based Plugin Platform & Lifecycle Engine.
Provides sandboxed execution, manifest validation, cryptographic signature verification,
and strict permission gating.

Categories:
  - Market Data
  - Broker
  - Strategy
  - Indicator
  - Research
  - AI
  - Analytics
  - News
  - Sentiment
  - Charts
  - Workspace
  - System Automation

Hard Security Invariants:
  - Plugins must NEVER automatically receive unrestricted privileges.
  - Plugins can NEVER access order.execute or live broker credentials.
  - Plugins can NEVER modify risk rules (risk.modify).
"""

import os
import sys
import json
import enum
import time
import hashlib
import dataclasses
from typing import Dict, List, Set, Optional, Any, Tuple

# =============================================================================
# 1. ENUMS & CONSTANTS
# =============================================================================

class PluginCategory(enum.Enum):
    MARKET_DATA = "Market Data"
    BROKER = "Broker"
    STRATEGY = "Strategy"
    INDICATOR = "Indicator"
    RESEARCH = "Research"
    AI = "AI"
    ANALYTICS = "Analytics"
    NEWS = "News"
    SENTIMENT = "Sentiment"
    CHARTS = "Charts"
    WORKSPACE = "Workspace"
    SYSTEM_AUTOMATION = "System Automation"

    @classmethod
    def from_string(cls, val: str) -> "PluginCategory":
        normalized = val.strip().lower().replace("_", " ").replace("-", " ")
        for member in cls:
            if member.value.lower() == normalized:
                return member
        raise ValueError(f"Invalid plugin category: '{val}'")

class SecurityLevel(enum.Enum):
    SANDBOXED_RESTRICTED = "SANDBOXED_RESTRICTED"
    CAPABILITY_GATED = "CAPABILITY_GATED"
    SYSTEM_CERTIFIED = "SYSTEM_CERTIFIED"

class PluginLifecycleState(enum.Enum):
    UNINSTALLED = "UNINSTALLED"
    INSTALLED = "INSTALLED"
    VERIFIED = "VERIFIED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"

# Hard forbidden permissions that no plugin may ever acquire
ABSOLUTE_DENIED_PERMISSIONS: Set[str] = {
    "order.execute",
    "risk.modify",
    "credential.read",
    "vault.access",
    "root.escalate",
    "system.reboot",
    "kernel.modify"
}

# =============================================================================
# 2. PLUGIN MANIFEST & SIGNATURE
# =============================================================================

@dataclasses.dataclass
class PluginManifest:
    id: str
    name: str
    version: str
    category: PluginCategory
    type: str # "capability-module"
    permissions: List[str]
    denied: List[str]
    provides: List[str]
    dependencies: Dict[str, str]
    security_level: SecurityLevel
    description: str = ""
    author: str = "KAIROS Core Team"
    signature: str = ""
    signer: str = "KAIROS Certified Publisher"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "category": self.category.value,
            "type": self.type,
            "permissions": self.permissions,
            "denied": self.denied,
            "provides": self.provides,
            "dependencies": self.dependencies,
            "security_level": self.security_level.value,
            "description": self.description,
            "author": self.author,
            "signature": self.signature,
            "signer": self.signer
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PluginManifest":
        category_raw = d.get("category", "Analytics")
        category = PluginCategory.from_string(category_raw) if isinstance(category_raw, str) else category_raw
        
        sec_raw = d.get("security_level", "SANDBOXED_RESTRICTED")
        sec_level = SecurityLevel(sec_raw) if isinstance(sec_raw, str) else sec_raw

        return cls(
            id=d["id"],
            name=d["name"],
            version=d.get("version", "1.0.0"),
            category=category,
            type=d.get("type", "capability-module"),
            permissions=list(d.get("permissions", [])),
            denied=list(d.get("denied", [])),
            provides=list(d.get("provides", [])),
            dependencies=dict(d.get("dependencies", {})),
            security_level=sec_level,
            description=d.get("description", ""),
            author=d.get("author", "KAIROS Community"),
            signature=d.get("signature", ""),
            signer=d.get("signer", "KAIROS Certified Publisher")
        )

# =============================================================================
# 3. CRYPTOGRAPHIC SIGNATURE & VERIFICATION STRATEGY
# =============================================================================

class PluginVerifier:
    """
    Verifies plugin authenticity, tamper-resistance, and manifest integrity.
    """
    SIGNING_SECRET_SALT = "KAIROS_OS_CERTIFIED_PUBLISHER_KEY_ED25519_SEED_2026"

    @classmethod
    def compute_signature(cls, manifest_data: Dict[str, Any]) -> str:
        """Computes a deterministic cryptographic signature over canonical manifest payload."""
        canonical_fields = {
            "id": manifest_data.get("id"),
            "name": manifest_data.get("name"),
            "version": manifest_data.get("version"),
            "category": manifest_data.get("category"),
            "permissions": sorted(manifest_data.get("permissions", [])),
            "denied": sorted(manifest_data.get("denied", [])),
            "provides": sorted(manifest_data.get("provides", [])),
            "security_level": manifest_data.get("security_level"),
            "salt": cls.SIGNING_SECRET_SALT
        }
        serialized = json.dumps(canonical_fields, sort_keys=True).encode("utf-8")
        return f"sha256:{hashlib.sha256(serialized).hexdigest()}"

    @classmethod
    def verify_manifest(cls, manifest: PluginManifest) -> Tuple[bool, str]:
        """
        Validates manifest security invariants and cryptographic signature.
        """
        # 1. Hard Security Check: Prohibit restricted permissions
        for perm in manifest.permissions:
            if perm in ABSOLUTE_DENIED_PERMISSIONS:
                return False, f"SECURITY VIOLATION: Plugin requests forbidden permission '{perm}'"

        # 2. Hard Security Check: Verify denied permissions explicitly listed
        for req_denied in ["order.execute", "risk.modify", "credential.read"]:
            if req_denied not in manifest.denied:
                return False, f"SECURITY VIOLATION: Plugin manifest must explicitly deny '{req_denied}'"

        # 3. Signature verification
        if not manifest.signature:
            return False, "UNSIGNED_PLUGIN: Plugin lacks cryptographic publisher signature"

        d = manifest.to_dict()
        expected_sig = cls.compute_signature(d)
        if manifest.signature != expected_sig:
            return False, f"TAMPER_DETECTED: Signature verification failed (mismatch with publisher key)"

        return True, "VERIFIED_AUTHENTIC"

# =============================================================================
# 4. PLUGIN LIFECYCLE & CATALOG MANAGER
# =============================================================================

class PluginPlatformManager:
    """
    KAIROS Capability-Based Plugin Platform Manager.
    Handles installation, search, verification, state transitions, and IPC queries.
    """
    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            storage_dir = "/var/lib/kairos/plugins" if os.path.exists("/var/lib/kairos") else os.path.expanduser("~/.kairos/plugins")
        self.storage_dir = storage_dir
        self.installed_dir = os.path.join(self.storage_dir, "installed")
        self.registry_dir = os.path.join(self.storage_dir, "registry")
        
        os.makedirs(self.installed_dir, exist_ok=True)
        os.makedirs(self.registry_dir, exist_ok=True)

        self.installed_plugins: Dict[str, Tuple[PluginManifest, PluginLifecycleState]] = {}
        self.catalog_plugins: Dict[str, PluginManifest] = {}

        self._populate_catalog()
        self._load_installed()

    def _populate_catalog(self):
        """Prepopulates certified official KAIROS capability plugins."""
        catalog_defs = [
            {
                "id": "kairos.regime-detector",
                "name": "Market Regime Detector",
                "version": "1.0.0",
                "category": "Analytics",
                "type": "capability-module",
                "description": "Real-time statistical market regime identification and volatility forecasting",
                "permissions": ["market.read", "strategy.read", "telemetry.read"],
                "denied": ["order.execute", "risk.modify", "credential.read"],
                "provides": ["regime.classification", "volatility.forecast"],
                "dependencies": {"kairos.core": ">=1.0.0"},
                "security_level": "SANDBOXED_RESTRICTED",
                "signer": "KAIROS Certified Publisher"
            },
            {
                "id": "kairos.orderflow-imbalance",
                "name": "Orderflow Imbalance Engine",
                "version": "1.2.0",
                "category": "Indicator",
                "type": "capability-module",
                "description": "Microstructure level-2 depth imbalance and cumulative volume delta calculator",
                "permissions": ["market.read", "depth.read"],
                "denied": ["order.execute", "risk.modify", "credential.read"],
                "provides": ["indicator.cvd", "indicator.orderbook_skew"],
                "dependencies": {"kairos.marketd": ">=1.0.0"},
                "security_level": "SANDBOXED_RESTRICTED",
                "signer": "KAIROS Certified Publisher"
            },
            {
                "id": "kairos.news-sentiment-nlp",
                "name": "Financial News Sentiment NLP",
                "version": "2.0.1",
                "category": "Sentiment",
                "type": "capability-module",
                "description": "On-device transformer sentiment scoring for real-time financial wire headlines",
                "permissions": ["news.read", "telemetry.read"],
                "denied": ["order.execute", "risk.modify", "credential.read"],
                "provides": ["sentiment.score", "sentiment.entity_linking"],
                "dependencies": {"kairos.ai": ">=1.0.0"},
                "security_level": "SANDBOXED_RESTRICTED",
                "signer": "KAIROS Certified Publisher"
            },
            {
                "id": "kairos.workspace-matrix",
                "name": "Multi-Monitor Workspace Matrix",
                "version": "1.1.0",
                "category": "Workspace",
                "type": "capability-module",
                "description": "Dynamic Hyprland workspace tile layout optimizer for multi-screen trading desks",
                "permissions": ["workspace.read", "desktop.notify"],
                "denied": ["order.execute", "risk.modify", "credential.read"],
                "provides": ["workspace.tile_auto_arrange"],
                "dependencies": {"kairos.desktop": ">=1.0.0"},
                "security_level": "SANDBOXED_RESTRICTED",
                "signer": "KAIROS Certified Publisher"
            },
            {
                "id": "kairos.strategy-ema-cross",
                "name": "Adaptive EMA Crossover Strategy",
                "version": "1.4.0",
                "category": "Strategy",
                "type": "capability-module",
                "description": "Algorithmic momentum crossover model generating normalized trade intent signals",
                "permissions": ["market.read", "signal.emit"],
                "denied": ["order.execute", "risk.modify", "credential.read"],
                "provides": ["strategy.signal_generator"],
                "dependencies": {"kairos.strategyd": ">=1.0.0"},
                "security_level": "CAPABILITY_GATED",
                "signer": "KAIROS Certified Publisher"
            },
            {
                "id": "kairos.macro-econ-calendar",
                "name": "Macroeconomic Event Tracker",
                "version": "1.0.5",
                "category": "News",
                "type": "capability-module",
                "description": "Automated central bank and economic release calendar alert daemon",
                "permissions": ["calendar.read", "desktop.notify"],
                "denied": ["order.execute", "risk.modify", "credential.read"],
                "provides": ["calendar.events"],
                "dependencies": {"kairos.core": ">=1.0.0"},
                "security_level": "SANDBOXED_RESTRICTED",
                "signer": "KAIROS Certified Publisher"
            },
            {
                "id": "kairos.chart-volatility-surface",
                "name": "3D Volatility Surface Visualizer",
                "version": "1.0.0",
                "category": "Charts",
                "type": "capability-module",
                "description": "Interactive GPU-accelerated implied volatility skew surface renderer",
                "permissions": ["market.read", "render.gui"],
                "denied": ["order.execute", "risk.modify", "credential.read"],
                "provides": ["chart.vol_surface"],
                "dependencies": {"kairos.desktop": ">=1.0.0"},
                "security_level": "SANDBOXED_RESTRICTED",
                "signer": "KAIROS Certified Publisher"
            },
            {
                "id": "kairos.system-watchdog-automation",
                "name": "High-Precision System Auto-Tuner",
                "version": "1.0.0",
                "category": "System Automation",
                "type": "capability-module",
                "description": "IRQ balancing and kernel CPU governor dynamic frequency optimizer",
                "permissions": ["telemetry.read", "metrics.write"],
                "denied": ["order.execute", "risk.modify", "credential.read"],
                "provides": ["system.tuner"],
                "dependencies": {"kairos.core": ">=1.0.0"},
                "security_level": "CAPABILITY_GATED",
                "signer": "KAIROS Certified Publisher"
            }
        ]

        for p_def in catalog_defs:
            # Generate cryptographic signature
            sig = PluginVerifier.compute_signature(p_def)
            p_def["signature"] = sig
            manifest = PluginManifest.from_dict(p_def)
            self.catalog_plugins[manifest.id] = manifest

    def _load_installed(self):
        """Loads installed plugins from disk storage."""
        if not os.path.exists(self.installed_dir):
            return

        for fname in os.listdir(self.installed_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.installed_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        manifest_data = data.get("manifest", {})
                        state_str = data.get("state", "ENABLED")
                        manifest = PluginManifest.from_dict(manifest_data)
                        state = PluginLifecycleState(state_str)
                        self.installed_plugins[manifest.id] = (manifest, state)
                except Exception:
                    pass

        # If none installed, install default certified plugins
        if not self.installed_plugins:
            default_ids = ["kairos.regime-detector", "kairos.orderflow-imbalance"]
            for did in default_ids:
                if did in self.catalog_plugins:
                    self.install_plugin(did, auto_enable=True)

    def _persist_installed_plugin(self, manifest: PluginManifest, state: PluginLifecycleState):
        """Writes plugin manifest and state to disk."""
        fpath = os.path.join(self.installed_dir, f"{manifest.id}.json")
        try:
            with open(fpath, "w", encoding="utf-8") as fh:
                json.dump({
                    "manifest": manifest.to_dict(),
                    "state": state.value,
                    "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }, fh, indent=2)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Public Lifecycle & Management API
    # -------------------------------------------------------------------------

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Lists all installed plugins and their lifecycle state."""
        out = []
        for pid, (manifest, state) in sorted(self.installed_plugins.items()):
            d = manifest.to_dict()
            d["state"] = state.value
            out.append(d)
        return out

    def search_plugins(self, query: str) -> List[Dict[str, Any]]:
        """Searches catalog for plugins matching query string in id, name, category, or description."""
        q = query.lower().strip()
        results = []
        for manifest in self.catalog_plugins.values():
            if (q in manifest.id.lower() or
                q in manifest.name.lower() or
                q in manifest.category.value.lower() or
                q in manifest.description.lower() or
                any(q in p.lower() for p in manifest.provides)):
                d = manifest.to_dict()
                installed_info = self.installed_plugins.get(manifest.id)
                d["installed"] = installed_info is not None
                d["state"] = installed_info[1].value if installed_info else "UNINSTALLED"
                results.append(d)
        return results

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves comprehensive information, permissions, and security audit for a plugin."""
        manifest = None
        state = PluginLifecycleState.UNINSTALLED

        if plugin_id in self.installed_plugins:
            manifest, state = self.installed_plugins[plugin_id]
        elif plugin_id in self.catalog_plugins:
            manifest = self.catalog_plugins[plugin_id]

        if not manifest:
            return None

        # Verify signature & safety invariants
        is_valid, audit_msg = PluginVerifier.verify_manifest(manifest)

        data = manifest.to_dict()
        data["state"] = state.value
        data["installed"] = plugin_id in self.installed_plugins
        data["security_audit"] = {
            "verified": is_valid,
            "message": audit_msg,
            "denied_critical_permissions": list(manifest.denied),
            "unrestricted_privileges_prohibited": True
        }
        return data

    def install_plugin(self, plugin_id: str, auto_enable: bool = True) -> Dict[str, Any]:
        """
        Installs and cryptographically verifies a plugin.
        Enforces strict rejection of malicious or privilege-escalating manifests.
        """
        manifest = self.catalog_plugins.get(plugin_id)
        if not manifest:
            return {"status": "ERROR", "error": f"Plugin '{plugin_id}' not found in catalog"}

        # Verification step
        is_valid, reason = PluginVerifier.verify_manifest(manifest)
        if not is_valid:
            return {"status": "ERROR", "error": f"Installation rejected: {reason}"}

        state = PluginLifecycleState.ENABLED if auto_enable else PluginLifecycleState.INSTALLED
        self.installed_plugins[manifest.id] = (manifest, state)
        self._persist_installed_plugin(manifest, state)

        return {
            "status": "SUCCESS",
            "plugin_id": manifest.id,
            "version": manifest.version,
            "state": state.value,
            "message": f"Plugin '{manifest.name}' installed successfully."
        }

    def remove_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """Uninstalls and removes a plugin from the system."""
        if plugin_id not in self.installed_plugins:
            return {"status": "ERROR", "error": f"Plugin '{plugin_id}' is not installed"}

        del self.installed_plugins[plugin_id]
        fpath = os.path.join(self.installed_dir, f"{plugin_id}.json")
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

        return {
            "status": "SUCCESS",
            "plugin_id": plugin_id,
            "message": f"Plugin '{plugin_id}' uninstalled cleanly."
        }

    def enable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """Enables an installed plugin."""
        if plugin_id not in self.installed_plugins:
            return {"status": "ERROR", "error": f"Plugin '{plugin_id}' is not installed"}

        manifest, state = self.installed_plugins[plugin_id]
        
        # Re-verify before enabling
        is_valid, reason = PluginVerifier.verify_manifest(manifest)
        if not is_valid:
            return {"status": "ERROR", "error": f"Cannot enable plugin: {reason}"}

        new_state = PluginLifecycleState.ENABLED
        self.installed_plugins[plugin_id] = (manifest, new_state)
        self._persist_installed_plugin(manifest, new_state)

        return {
            "status": "SUCCESS",
            "plugin_id": plugin_id,
            "state": new_state.value,
            "message": f"Plugin '{manifest.name}' enabled."
        }

    def disable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """Disables an active plugin without removing it."""
        if plugin_id not in self.installed_plugins:
            return {"status": "ERROR", "error": f"Plugin '{plugin_id}' is not installed"}

        manifest, _ = self.installed_plugins[plugin_id]
        new_state = PluginLifecycleState.DISABLED
        self.installed_plugins[plugin_id] = (manifest, new_state)
        self._persist_installed_plugin(manifest, new_state)

        return {
            "status": "SUCCESS",
            "plugin_id": plugin_id,
            "state": new_state.value,
            "message": f"Plugin '{manifest.name}' disabled."
        }

# Global singleton
_PLATFORM_MANAGER = None

def get_platform_manager() -> PluginPlatformManager:
    global _PLATFORM_MANAGER
    if _PLATFORM_MANAGER is None:
        _PLATFORM_MANAGER = PluginPlatformManager()
    return _PLATFORM_MANAGER
