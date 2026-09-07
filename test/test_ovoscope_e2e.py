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
    make_session,
    register_adapt_intent,
)
from ovos_adapt.intent import IntentBuilder  # noqa: E402
from ovos_bus_client.message import Message  # noqa: E402

from ovos_adapt.opm import AdaptPipeline  # noqa: E402

PIPELINE_ID = "ovos-adapt-pipeline-plugin"
CONFIG_KEY = "adapt"


class _AdaptHarness(E2EPipelineHarness):
    PIPELINE_ID = PIPELINE_ID
    CONFIG_KEY = CONFIG_KEY
    PLUGIN_CONFIG = {}
    SKILL_ID = "test_skill_adapt"

    pipeline: AdaptPipeline  # type: ignore[assignment]

    def setUp(self) -> None:
        # ovoscope.E2EPipelineHarness.setUp() emits its per-test isolation
        # "detach_skill" with no message.context["skill_id"], which
        # OVOS-INTENT-4 §3.2 requires as the authoritative attribution;
        # redo it here with the context set so isolation between tests in
        # this TestCase still works.
        self._detach_skill(self.SKILL_ID)

    def _vocab(self, name, words):
        self._register_vocab(f"{self.SKILL_ID}:{name}", words, self.SKILL_ID)

    def _intent(self, builder):
        register_adapt_intent(self.bus, builder)

    def _detach_skill(self, skill_id):
        # ovoscope.detach_skill() does not set message.context["skill_id"]
        # (OVOS-INTENT-4 §3.2), so it is bypassed here in favour of a
        # direct emit that does. Temporary until ovoscope#185 releases a
        # fixed harness.
        self.bus.emit(Message("detach_skill", {"skill_id": skill_id},
                              {"skill_id": skill_id}))

    def _register_vocab(self, entity_type, words, skill_id):
        # ovoscope.register_adapt_vocab() does not set
        # message.context["skill_id"] (OVOS-INTENT-4 §3.2), so it is
        # bypassed here in favour of a direct emit that does. Temporary
        # until ovoscope#185 releases a fixed harness.
        for word in words:
            self.bus.emit(Message("register_vocab", {
                "entity_value": word, "entity_type": entity_type,
                "lang": "en-US",
            }, {"skill_id": skill_id}))


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
        self._vocab("TurnOn", ["enable", "activate"])
        self._vocab("Light", ["light", "lights"])
        self._intent(
            IntentBuilder(f"{self.SKILL_ID}:lights_on")
            .require(f"{self.SKILL_ID}:TurnOn")
            .require(f"{self.SKILL_ID}:Light")
        )
        utterance = "enable the lights"
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
        self._register_vocab("skill_b_adapt:Play", ["play"], "skill_b_adapt")
        self._register_vocab("skill_b_adapt:Music", ["music"], "skill_b_adapt")
        register_adapt_intent(
            self.bus,
            IntentBuilder("skill_b_adapt:play_music")
            .require("skill_b_adapt:Play")
            .require("skill_b_adapt:Music"),
        )

        self._detach_skill(self.SKILL_ID)

        self.expect_no_match("turn off the lights")
        self.expect_no_match("turn on the lights")
        msg = self.send_and_capture("play music", expected_types=["skill_b_adapt:play_music"])
        self.assertIsNotNone(msg, "skill_b intent should survive skill_a detach")
        self._detach_skill("skill_b_adapt")


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
