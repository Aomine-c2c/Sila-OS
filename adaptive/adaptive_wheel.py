#!/usr/bin/env python3
"""
KAIROS Adaptive Wheel Model & Visual Reticle Engine
===================================================
An ORIGINAL visual representation of the continuous adaptive intelligence cycle.
Strictly engineered as a precision mechanical dial/reticle mechanism.

Core Principles:
1. Not a loading spinner, not a gaming effect, not a logo animation.
2. The wheel NEVER continuously spins for decoration.
3. Rotates ONLY when an actual adaptive event occurs.
4. A validated evolution triggers one controlled stepped 60° rotation with
   eased mechanical escapement and a subtle perimeter stipple lattice grain pulse.
5. Multi-modal outputs: SVG vector dial, CSS keyframe styles, Waybar badges,
   desktop notifications, and ANSI terminal rendering.

Sectors (6):
  - OBSERVE  (0°)
  - DIAGNOSE (60°)
  - ADAPT    (120°)
  - VALIDATE (180°)
  - DEPLOY   (240°)
  - LEARN    (300°)

States (8):
  - IDLE
  - OBSERVING
  - DIAGNOSING
  - TESTING
  - VALIDATING
  - EVOLUTION_COMPLETE
  - ROLLBACK
  - HALTED
"""

import os
import sys
import json
import time
import math
import subprocess
from enum import Enum
from typing import Dict, Any, Optional, Tuple

class AdaptiveWheelSector(str, Enum):
    OBSERVE = "OBSERVE"
    DIAGNOSE = "DIAGNOSE"
    ADAPT = "ADAPT"
    VALIDATE = "VALIDATE"
    DEPLOY = "DEPLOY"
    LEARN = "LEARN"

class AdaptiveWheelState(str, Enum):
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    DIAGNOSING = "DIAGNOSING"
    TESTING = "TESTING"
    VALIDATING = "VALIDATING"
    EVOLUTION_COMPLETE = "EVOLUTION_COMPLETE"
    ROLLBACK = "ROLLBACK"
    HALTED = "HALTED"

# Angular positions for sectors (in degrees)
SECTOR_ANGLES: Dict[AdaptiveWheelSector, int] = {
    AdaptiveWheelSector.OBSERVE: 0,
    AdaptiveWheelSector.DIAGNOSE: 60,
    AdaptiveWheelSector.ADAPT: 120,
    AdaptiveWheelSector.VALIDATE: 180,
    AdaptiveWheelSector.DEPLOY: 240,
    AdaptiveWheelSector.LEARN: 300,
}

# State properties: (Active Sector, Color Light, Color Dark, Badge Icon)
STATE_SPECS: Dict[AdaptiveWheelState, Dict[str, Any]] = {
    AdaptiveWheelState.IDLE: {
        "sector": AdaptiveWheelSector.OBSERVE,
        "color_light": "#64748b",
        "color_dark": "#7b8496",
        "icon": "⎊",
        "label": "IDLE / CALIBRATED",
    },
    AdaptiveWheelState.OBSERVING: {
        "sector": AdaptiveWheelSector.OBSERVE,
        "color_light": "#0284c7",
        "color_dark": "#00f0ff",
        "icon": "◎",
        "label": "OBSERVING TELEMETRY",
    },
    AdaptiveWheelState.DIAGNOSING: {
        "sector": AdaptiveWheelSector.DIAGNOSE,
        "color_light": "#059669",
        "color_dark": "#00ff88",
        "icon": "◈",
        "label": "DIAGNOSING DRIFT",
    },
    AdaptiveWheelState.TESTING: {
        "sector": AdaptiveWheelSector.ADAPT,
        "color_light": "#d97706",
        "color_dark": "#ffd700",
        "icon": "◇",
        "label": "TESTING CANDIDATE",
    },
    AdaptiveWheelState.VALIDATING: {
        "sector": AdaptiveWheelSector.VALIDATE,
        "color_light": "#7c3aed",
        "color_dark": "#c084fc",
        "icon": "◬",
        "label": "VALIDATING INVARIANTS",
    },
    AdaptiveWheelState.EVOLUTION_COMPLETE: {
        "sector": AdaptiveWheelSector.DEPLOY,
        "color_light": "#059669",
        "color_dark": "#00ff88",
        "icon": "✦",
        "label": "EVOLUTION VALIDATED",
    },
    AdaptiveWheelState.ROLLBACK: {
        "sector": AdaptiveWheelSector.LEARN,
        "color_light": "#dc2626",
        "color_dark": "#ff3366",
        "icon": "↺",
        "label": "ATOMIC ROLLBACK ENGAGED",
    },
    AdaptiveWheelState.HALTED: {
        "sector": AdaptiveWheelSector.OBSERVE,
        "color_light": "#dc2626",
        "color_dark": "#ff3366",
        "icon": "⏹",
        "label": "SAFETY CIRCUIT HALTED",
    },
}

STATE_DIR = os.environ.get("KAIROS_STATE_DIR") or (
    "/run/kairos" if os.getuid() == 0 else os.path.join(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"), "kairos")
)
WHEEL_STATE_FILE = os.path.join(STATE_DIR, "adaptive_wheel_state.json")

class AdaptiveWheel:
    """
    State machine and renderer for the KAIROS Adaptive Wheel reticle.
    """

    def __init__(self, state_file: Optional[str] = None):
        self.state_file = state_file or WHEEL_STATE_FILE
        self.state: AdaptiveWheelState = AdaptiveWheelState.IDLE
        self.current_angle: int = 0
        self.last_transition_ts: float = time.time()
        self.evolution_count: int = 0
        self.last_reason: str = "System calibration baseline"
        self._load_state()

    def _load_state(self):
        if self.state_file and os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.state = AdaptiveWheelState(data.get("state", "IDLE"))
                    self.current_angle = int(data.get("current_angle", 0)) % 360
                    self.last_transition_ts = float(data.get("last_transition_ts", time.time()))
                    self.evolution_count = int(data.get("evolution_count", 0))
                    self.last_reason = data.get("last_reason", self.last_reason)
            except Exception:
                pass

    def save_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            payload = {
                "state": self.state.value,
                "current_angle": self.current_angle,
                "active_sector": STATE_SPECS[self.state]["sector"].value,
                "last_transition_ts": self.last_transition_ts,
                "evolution_count": self.evolution_count,
                "last_reason": self.last_reason,
                "badge": self.get_waybar_badge(),
            }
            temp_file = f"{self.state_file}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(temp_file, self.state_file)
        except Exception:
            pass

    def transition_to(self, new_state: AdaptiveWheelState, reason: str = "", notify: bool = False) -> int:
        """
        Advances the wheel state and computes stepped escapement angle.
        Returns new angle in degrees.
        """
        old_state = self.state
        self.state = new_state
        self.last_transition_ts = time.time()
        if reason:
            self.last_reason = reason

        # Discrete escapement rotation rule:
        # Rotates ONLY on actual adaptive events.
        target_sector = STATE_SPECS[new_state]["sector"]
        self.current_angle = SECTOR_ANGLES[target_sector]

        if new_state == AdaptiveWheelState.EVOLUTION_COMPLETE and old_state != AdaptiveWheelState.EVOLUTION_COMPLETE:
            self.evolution_count += 1
            if notify:
                self.send_desktop_notification(
                    "✦ KAIROS Adaptive Wheel - Evolution Validated",
                    f"Candidate accepted: {self.last_reason}\nRotation: 60° escapement to DEPLOY sector."
                )
        elif new_state == AdaptiveWheelState.ROLLBACK and old_state != AdaptiveWheelState.ROLLBACK:
            if notify:
                self.send_desktop_notification(
                    "↺ KAIROS Adaptive Wheel - Rollback Engaged",
                    f"Reverted to baseline: {self.last_reason}\nEscapement: Reverted to LEARN memory."
                )

        self.save_state()
        return self.current_angle

    def send_desktop_notification(self, title: str, body: str):
        """Sends a discreet, non-intrusive desktop notification via notify-send if present."""
        try:
            subprocess.Popen(
                ["notify-send", "-a", "KAIROS Adaptive Wheel", "-u", "normal", "-i", "dialog-information", title, body],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def get_waybar_badge(self) -> Dict[str, Any]:
        """Formats the module state for Waybar status bar."""
        spec = STATE_SPECS[self.state]
        sector = spec["sector"].value
        return {
            "text": f"{spec['icon']} AEI: [{sector}]",
            "tooltip": f"KAIROS Adaptive Wheel\nState: {self.state.value} ({spec['label']})\nActive Sector: {sector} ({self.current_angle}°)\nEvolutions: {self.evolution_count}\nReason: {self.last_reason}",
            "class": self.state.value.lower(),
            "percentage": int((self.current_angle / 360.0) * 100),
        }

    def render_ansi_reticle(self) -> str:
        """
        Renders a precision mechanical caliper dial in ANSI/Unicode terminal text.
        """
        spec = STATE_SPECS[self.state]
        sector = spec["sector"].value
        angle = self.current_angle

        # 6 sector indicator symbols
        s_obs = "●" if sector == "OBSERVE" else "○"
        s_diag = "●" if sector == "DIAGNOSE" else "○"
        s_adapt = "●" if sector == "ADAPT" else "○"
        s_val = "●" if sector == "VALIDATE" else "○"
        s_dep = "●" if sector == "DEPLOY" else "○"
        s_learn = "●" if sector == "LEARN" else "○"

        lines = [
            f"             0° [OBSERVE] {s_obs}",
            f"                  ││",
            f"   300° [LEARN]  ╭──┼──╮  [DIAGNOSE] 60°",
            f"       {s_learn}         │  │  │         {s_diag}",
            f"             ───┼──⎊──┼───",
            f"       {s_dep}         │  │  │         {s_adapt}",
            f"   240° [DEPLOY] ╰──┼──╯  [ADAPT] 120°",
            f"                  ││",
            f"            180° [VALIDATE] {s_val}",
            f"",
            f"  ◈ RETICLE STATE   : {self.state.value} ({spec['label']})",
            f"  ◈ ACTIVE SECTOR   : {sector} ({angle:03d}° Escapement)",
            f"  ◈ STIPPLE LATTICE : {'PULSING / SETTLING' if self.state in (AdaptiveWheelState.VALIDATING, AdaptiveWheelState.EVOLUTION_COMPLETE) else 'QUIESCENT'}",
            f"  ◈ EVOLUTIONS      : {self.evolution_count}",
            f"  ◈ EVENT DIAGNOSIS : {self.last_reason}",
        ]
        return "\n".join(lines)

    def generate_svg(self, mode: str = "light") -> str:
        """
        Generates clean, original, minimal SVG vector markup of the mechanical caliper wheel.
        """
        spec = STATE_SPECS[self.state]
        color = spec["color_light"] if mode == "light" else spec["color_dark"]
        stroke_color = "#0f172a" if mode == "light" else "#e0e6ed"
        bg_subtle = "rgba(2, 132, 199, 0.05)" if mode == "light" else "rgba(0, 240, 255, 0.04)"
        active_angle = self.current_angle

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <!-- Subtle Stipple Lattice Grain Filter & Pattern -->
    <pattern id="stippleLattice" width="8" height="8" patternUnits="userSpaceOnUse">
      <circle cx="4" cy="4" r="0.8" fill="{color}" opacity="0.25" />
    </pattern>
    <style>
      .caliper-hub {{ fill: none; stroke: {stroke_color}; stroke-width: 1.5; opacity: 0.35; }}
      .caliper-track {{ fill: none; stroke: {stroke_color}; stroke-width: 2; opacity: 0.6; }}
      .vernier-tick {{ stroke: {stroke_color}; stroke-width: 1.5; opacity: 0.5; }}
      .vernier-major {{ stroke: {stroke_color}; stroke-width: 2.5; opacity: 0.85; }}
      .stage-notch {{ fill: {color}; transition: all 0.35s cubic-bezier(0.25, 1, 0.5, 1); }}
      .pointer-needle {{ stroke: {color}; stroke-width: 2.5; stroke-linecap: round; transition: transform 0.35s cubic-bezier(0.25, 1, 0.5, 1); }}
      .stipple-ring {{ fill: url(#stippleLattice); opacity: 0.9; }}
      .label-text {{ font-family: 'JetBrains Mono', 'Roboto Mono', monospace; font-size: 11px; font-weight: 600; fill: {stroke_color}; text-anchor: middle; }}
      .active-label {{ fill: {color}; font-weight: 700; }}
    </style>
  </defs>

  <!-- Central Axis & Vernier Calibration Reticle -->
  <circle cx="256" cy="256" r="236" class="caliper-hub" />
  <circle cx="256" cy="256" r="190" class="stipple-ring" />
  <circle cx="256" cy="256" r="190" class="caliper-track" />
  <circle cx="256" cy="256" r="140" class="caliper-hub" stroke-dasharray="2 6" />
  <circle cx="256" cy="256" r="54" class="caliper-hub" />
  <circle cx="256" cy="256" r="12" fill="{color}" />

  <!-- 6 Discrete Stage Escapement Notches (0°, 60°, 120°, 180°, 240°, 300°) -->
  <!-- 0°: OBSERVE -->
  <circle cx="256" cy="66" r="6" class="stage-notch" opacity="{1.0 if active_angle == 0 else 0.3}" />
  <text x="256" y="50" class="label-text {('active-label' if active_angle == 0 else '')}">OBSERVE</text>

  <!-- 60°: DIAGNOSE -->
  <circle cx="420" cy="161" r="6" class="stage-notch" opacity="{1.0 if active_angle == 60 else 0.3}" />
  <text x="444" y="165" class="label-text {('active-label' if active_angle == 60 else '')}">DIAGNOSE</text>

  <!-- 120°: ADAPT -->
  <circle cx="420" cy="351" r="6" class="stage-notch" opacity="{1.0 if active_angle == 120 else 0.3}" />
  <text x="435" y="375" class="label-text {('active-label' if active_angle == 120 else '')}">ADAPT</text>

  <!-- 180°: VALIDATE -->
  <circle cx="256" cy="446" r="6" class="stage-notch" opacity="{1.0 if active_angle == 180 else 0.3}" />
  <text x="256" y="475" class="label-text {('active-label' if active_angle == 180 else '')}">VALIDATE</text>

  <!-- 240°: DEPLOY -->
  <circle cx="92" cy="351" r="6" class="stage-notch" opacity="{1.0 if active_angle == 240 else 0.3}" />
  <text x="76" y="375" class="label-text {('active-label' if active_angle == 240 else '')}">DEPLOY</text>

  <!-- 300°: LEARN -->
  <circle cx="92" cy="161" r="6" class="stage-notch" opacity="{1.0 if active_angle == 300 else 0.3}" />
  <text x="68" y="165" class="label-text {('active-label' if active_angle == 300 else '')}">LEARN</text>

  <!-- Precision Hairline Crosshair Reticle -->
  <line x1="256" y1="20" x2="256" y2="492" class="caliper-hub" />
  <line x1="20" y1="256" x2="492" y2="256" class="caliper-hub" />

  <!-- Stepped Mechanical Escapement Indicator Hand -->
  <g transform="rotate({active_angle} 256 256)">
    <line x1="256" y1="256" x2="256" y2="76" class="pointer-needle" />
    <polygon points="256,66 251,76 261,76" fill="{color}" />
  </g>
</svg>
"""
        return svg

# Singleton engine instance
_wheel_instance: Optional[AdaptiveWheel] = None

def get_adaptive_wheel() -> AdaptiveWheel:
    global _wheel_instance
    if _wheel_instance is None:
        _wheel_instance = AdaptiveWheel()
    return _wheel_instance
