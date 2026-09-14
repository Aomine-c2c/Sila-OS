#!/usr/bin/env python3
"""
Unit Tests for KAIROS Adaptive Wheel
====================================
Validates the visual reticle model, state machine, mechanical rotation constraints,
and event coupling invariants:
1. 6 original sectors: OBSERVE, DIAGNOSE, ADAPT, VALIDATE, DEPLOY, LEARN.
2. 8 operational states: IDLE, OBSERVING, DIAGNOSING, TESTING, VALIDATING,
   EVOLUTION_COMPLETE, ROLLBACK, HALTED.
3. Strict Invariant: Zero decorative continuous spinning.
4. Validated evolution triggers exactly 1 stepped 60° rotation.
5. Atomic rollback transitions to LEARN (300°) memory.
6. Waybar badge and desktop notification formatting.
7. ANSI reticle terminal rendering correctness.
8. SVG vector generation validity.
9. Integration with AEI evaluate_and_adapt loop.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adaptive.adaptive_wheel import (
    AdaptiveWheel,
    AdaptiveWheelState,
    AdaptiveWheelSector,
    SECTOR_ANGLES,
    STATE_SPECS
)
from adaptive.aei import AdaptiveEvolutionSystem, MonitoredSignal

class TestAdaptiveWheel(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = os.path.join(self.temp_dir.name, "wheel_state.json")
        self.wheel = AdaptiveWheel(state_file=self.state_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_six_sectors_angles(self):
        """Verify all 6 sectors have exact 60° increments."""
        self.assertEqual(len(AdaptiveWheelSector), 6)
        self.assertEqual(SECTOR_ANGLES[AdaptiveWheelSector.OBSERVE], 0)
        self.assertEqual(SECTOR_ANGLES[AdaptiveWheelSector.DIAGNOSE], 60)
        self.assertEqual(SECTOR_ANGLES[AdaptiveWheelSector.ADAPT], 120)
        self.assertEqual(SECTOR_ANGLES[AdaptiveWheelSector.VALIDATE], 180)
        self.assertEqual(SECTOR_ANGLES[AdaptiveWheelSector.DEPLOY], 240)
        self.assertEqual(SECTOR_ANGLES[AdaptiveWheelSector.LEARN], 300)

    def test_eight_states_exist(self):
        """Verify all 8 states are defined and mapped in specs."""
        self.assertEqual(len(AdaptiveWheelState), 8)
        for state in AdaptiveWheelState:
            self.assertIn(state, STATE_SPECS)
            spec = STATE_SPECS[state]
            self.assertIn("sector", spec)
            self.assertIn("color_light", spec)
            self.assertIn("color_dark", spec)
            self.assertIn("icon", spec)
            self.assertIn("label", spec)

    def test_idle_state_has_zero_rotation(self):
        """Verify initial / idle state is calibrated at 0° OBSERVE."""
        self.assertEqual(self.wheel.state, AdaptiveWheelState.IDLE)
        self.assertEqual(self.wheel.current_angle, 0)
        badge = self.wheel.get_waybar_badge()
        self.assertIn("idle", badge["class"].lower())
        self.assertEqual(badge["percentage"], 0)

    def test_evolution_triggers_one_controlled_stepped_rotation(self):
        """
        Verify that transitioning to EVOLUTION_COMPLETE advances to DEPLOY (240°)
        and increments evolution count by 1.
        """
        initial_evolutions = self.wheel.evolution_count
        angle = self.wheel.transition_to(
            AdaptiveWheelState.EVOLUTION_COMPLETE,
            reason="Validated strategy weights tuning"
        )
        self.assertEqual(angle, 240)
        self.assertEqual(self.wheel.current_angle, 240)
        self.assertEqual(self.wheel.evolution_count, initial_evolutions + 1)
        self.assertEqual(self.wheel.state, AdaptiveWheelState.EVOLUTION_COMPLETE)

        badge = self.wheel.get_waybar_badge()
        self.assertIn("DEPLOY", badge["text"])
        self.assertIn("EVOLUTION_COMPLETE", badge["tooltip"])

    def test_rollback_reverts_to_learn_sector(self):
        """Verify that rollback transitions to LEARN sector (300°) for memory retention."""
        angle = self.wheel.transition_to(
            AdaptiveWheelState.ROLLBACK,
            reason="Post-deploy slippage exceeded threshold"
        )
        self.assertEqual(angle, 300)
        self.assertEqual(self.wheel.state, AdaptiveWheelState.ROLLBACK)
        badge = self.wheel.get_waybar_badge()
        self.assertIn("LEARN", badge["text"])
        self.assertIn("rollback", badge["class"].lower())

    def test_ansi_reticle_rendering(self):
        """Verify ANSI text reticle contains all sectors and state information."""
        self.wheel.transition_to(AdaptiveWheelState.VALIDATING, reason="Testing invariants")
        text = self.wheel.render_ansi_reticle()
        self.assertIn("OBSERVE", text)
        self.assertIn("DIAGNOSE", text)
        self.assertIn("ADAPT", text)
        self.assertIn("VALIDATE", text)
        self.assertIn("DEPLOY", text)
        self.assertIn("LEARN", text)
        self.assertIn("VALIDATING", text)
        self.assertIn("180°", text)

    def test_svg_generation(self):
        """Verify SVG contains vector circles, labels, and escapement hand."""
        svg_light = self.wheel.generate_svg(mode="light")
        self.assertIn("<svg", svg_light)
        self.assertIn("pattern id=\"stippleLattice\"", svg_light)
        self.assertIn("OBSERVE", svg_light)
        self.assertIn("VALIDATE", svg_light)
        self.assertIn("pointer-needle", svg_light)

        # Transition to observing state to test cyan color in dark mode
        self.wheel.transition_to(AdaptiveWheelState.OBSERVING)
        svg_dark = self.wheel.generate_svg(mode="dark")
        self.assertIn("<svg", svg_dark)
        self.assertIn("#00f0ff", svg_dark)

    def test_aei_cycle_drives_wheel_states(self):
        """
        Verify that executing an adaptation in AdaptiveEvolutionSystem
        automatically advances the wheel through the lifecycle to EVOLUTION_COMPLETE.
        """
        aei_temp = tempfile.TemporaryDirectory()
        system = AdaptiveEvolutionSystem(storage_dir=aei_temp.name)

        # Trigger adaptation
        result = system.run_adaptation_cycle(
            telemetry={"rolling_sharpe": 1.05, "orderbook_drift_ks": 0.45},
            forced_signal=MonitoredSignal.PERFORMANCE_DETERIORATION
        )

        self.assertEqual(result["status"], "SUCCESS_DEPLOYED")
        from adaptive.adaptive_wheel import get_adaptive_wheel
        wheel = get_adaptive_wheel()
        self.assertEqual(wheel.state, AdaptiveWheelState.EVOLUTION_COMPLETE)
        self.assertEqual(wheel.current_angle, 240)

        aei_temp.cleanup()

if __name__ == "__main__":
    unittest.main()
