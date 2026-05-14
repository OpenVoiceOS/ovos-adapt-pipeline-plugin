"""End-to-end tests for AdaptPipeline using ovoscope.

Built on top of ovoscope's reusable :class:`E2EPipelineHarness` so this
file only contains adapt-specific concerns (vocab + IntentBuilder
registration, slot assertions).  The harness handles MiniCroft startup,
Configuration save/restore, bus capture, and per-test skill detach.
"""
import unittest

import pytest

ovoscope = pytest.importorskip("ovoscope", reason="ovoscope not installed; skipping E2E tests")

from ovoscope import (  # noqa: E402
    E2EPipelineHarness,
    detach_intent,
    detach_skill,
    make_session,
    register_adapt_intent,
    register_adapt_vocab,
)
from ovos_workshop.intents import IntentBuilder  # noqa: E402

from ovos_adapt.opm import AdaptPipeline  # noqa: E402

PIPELINE_ID = "ovos-adapt-pipeline-plugin"
CONFIG_KEY = "adapt"


class _AdaptHarness(E2EPipelineHarness):
    PIPELINE_ID = PIPELINE_ID
    CONFIG_KEY = CONFIG_KEY
    PLUGIN_CONFIG = {}
    SKILL_ID = "test_skill_adapt"

    pipeline: AdaptPipeline  # type: ignore[assignment]

    def _vocab(self, name, words):
        register_adapt_vocab(self.bus, f"{self.SKILL_ID}:{name}", words)

    def _intent(self, builder):
        register_adapt_intent(self.bus, builder)


class TestRegisteredIntentMatch(_AdaptHarness):
    def test_all_required_keywords_present_fires_intent(self):
        self._vocab("TurnOff", ["off", "disable", "shutdown"])
        self._vocab("Light", ["light", "lights", "lamp"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light")
        )
        msg = self.send_and_capture(
            "turn off the lights", expected_types=[f"{self.SKILL_ID}:lights_off"]
        )
        self.assertIsNotNone(msg, "expected intent match on bus")
        self.assertEqual(msg.msg_type, f"{self.SKILL_ID}:lights_off")
        self.assertEqual(msg.data.get("utterance"), "turn off the lights")

    def test_missing_required_keyword_no_match(self):
        self._vocab("TurnOff", ["off", "disable"])
        self._vocab("Light", ["light", "lights"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light")
        )
        self.expect_no_match("turn on the lights")

    def test_no_match_when_no_intents_registered(self):
        self.expect_no_match("turn off the lights")

    def test_utterance_field_preserved(self):
        self._vocab("TurnOn", ["on", "enable"])
        self._vocab("Light", ["light", "lights"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_on")
            .require(f"{self.SKILL_ID}:TurnOn")
            .require(f"{self.SKILL_ID}:Light")
        )
        utterance = "turn on the lights"
        msg = self.send_and_capture(utterance, expected_types=[f"{self.SKILL_ID}:lights_on"])
        self.assertIsNotNone(msg)
        self.assertEqual(msg.data.get("utterance"), utterance)

    def test_best_intent_selected_among_multiple(self):
        self._vocab("TurnOff", ["off", "disable"])
        self._vocab("TurnOn", ["on", "enable"])
        self._vocab("Light", ["light", "lights"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light")
        )
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_on")
            .require(f"{self.SKILL_ID}:TurnOn")
            .require(f"{self.SKILL_ID}:Light")
        )
        msg = self.send_and_capture(
            "turn on the lights", expected_types=[f"{self.SKILL_ID}:lights_on"]
        )
        self.assertIsNotNone(msg)
        self.assertEqual(msg.msg_type, f"{self.SKILL_ID}:lights_on")


class TestOptionalSlots(_AdaptHarness):
    def test_optional_slot_captured_when_present(self):
        self._vocab("TurnOff", ["off"])
        self._vocab("Light", ["lights"])
        self._vocab("Room", ["kitchen", "bedroom", "bathroom"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light")
            .optionally(f"{self.SKILL_ID}:Room")
        )
        msg = self.send_and_capture(
            "turn off the bedroom lights", expected_types=[f"{self.SKILL_ID}:lights_off"]
        )
        self.assertIsNotNone(msg)

    def test_optional_slot_absent_still_fires(self):
        self._vocab("TurnOff", ["off"])
        self._vocab("Light", ["lights"])
        self._vocab("Room", ["kitchen", "bedroom"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light")
            .optionally(f"{self.SKILL_ID}:Room")
        )
        msg = self.send_and_capture(
            "turn off the lights", expected_types=[f"{self.SKILL_ID}:lights_off"]
        )
        self.assertIsNotNone(msg)


class TestDetach(_AdaptHarness):
    def test_detach_intent_prevents_match(self):
        self._vocab("TurnOff", ["off"])
        self._vocab("Light", ["lights"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light")
        )
        msg = self.send_and_capture(
            "turn off the lights", expected_types=[f"{self.SKILL_ID}:lights_off"]
        )
        self.assertIsNotNone(msg)

        detach_intent(self.bus, f"{self.SKILL_ID}:lights_off")
        self.expect_no_match("turn off the lights")

    def test_detach_skill_removes_all_its_intents(self):
        self._vocab("TurnOff", ["off"])
        self._vocab("TurnOn", ["on"])
        self._vocab("Light", ["lights"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light")
        )
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_on")
            .require(f"{self.SKILL_ID}:TurnOn")
            .require(f"{self.SKILL_ID}:Light")
        )
        register_adapt_vocab(self.bus, "skill_b_adapt:Play", ["play"])
        register_adapt_vocab(self.bus, "skill_b_adapt:Music", ["music"])
        register_adapt_intent(
            self.bus,
            IntentBuilder("skill_b_adapt:play_music")
            .require("skill_b_adapt:Play")
            .require("skill_b_adapt:Music"),
        )

        detach_skill(self.bus, self.SKILL_ID)

        self.expect_no_match("turn off the lights")
        self.expect_no_match("turn on the lights")
        msg = self.send_and_capture("play music", expected_types=["skill_b_adapt:play_music"])
        self.assertIsNotNone(msg, "skill_b intent should survive skill_a detach")
        detach_skill(self.bus, "skill_b_adapt")


class TestSessionBlacklist(_AdaptHarness):
    def test_blacklisted_intent_is_skipped(self):
        self._vocab("TurnOff", ["off"])
        self._vocab("Light", ["lights"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light")
        )
        sess = make_session(
            "bl-intent-test",
            blacklisted_intents=[f"{self.SKILL_ID}:lights_off"],
        )
        self.expect_no_match("turn off the lights", session=sess, timeout=3.0)

    def test_blacklisted_skill_is_skipped(self):
        self._vocab("TurnOff", ["off"])
        self._vocab("Light", ["lights"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light")
        )
        sess = make_session(
            "bl-skill-test",
            blacklisted_skills=[self.SKILL_ID],
        )
        self.expect_no_match("turn off the lights", session=sess, timeout=3.0)


if __name__ == "__main__":
    unittest.main()
