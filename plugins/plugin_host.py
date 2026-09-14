"""
KAIROS Plugin Architecture - Sandboxed Capability-Based Plugin Host
Ensures third-party trading/analysis plugins cannot access network or execution
without explicitly declared and validated permissions.
"""

import abc
import enum
from typing import Set, Dict, Any

class Capability(enum.Enum):
    READ_MARKET_DATA = "read:market_data"
    COMPUTE_FEATURES = "compute:features"
    EMIT_SIGNAL = "emit:signal"
    # Note: DIRECT_BROKER_EXECUTION does NOT exist by design!

class KairosPlugin(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def required_capabilities(self) -> Set[Capability]:
        pass

    @abc.abstractmethod
    def on_market_tick(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        pass

class PluginManager:
    def __init__(self, allowed_capabilities: Set[Capability]):
        self.allowed_capabilities = allowed_capabilities
        self.registered_plugins: Dict[str, KairosPlugin] = {}

    def register(self, plugin: KairosPlugin) -> bool:
        unauthorized = plugin.required_capabilities - self.allowed_capabilities
        if unauthorized:
            raise PermissionError(
                f"Plugin {plugin.name} requested unauthorized capabilities: {[c.value for c in unauthorized]}"
            )
        self.registered_plugins[plugin.name] = plugin
        return True
