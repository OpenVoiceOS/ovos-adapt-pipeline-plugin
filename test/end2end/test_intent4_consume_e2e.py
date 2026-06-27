"""OVOS-INTENT-4 *consumer* end-to-end tests for the Adapt pipeline.

Where ``test/test_ovoscope_e2e.py`` proves adapt matches intents registered via
the **legacy** ``register_vocab`` / ``register_intent`` bus events, this suite
proves adapt *consumes the INTENT-4 spec registration topics* and then matches —
the bus-level contract of OVOS-INTENT-4 (``ovos-intent-4.md``).

Adapt is a **keyword** engine, so it consumes ``ovos.intent.register.keyword``
(§5) and explicitly NOT ``ovos.intent.register.template`` (§11). Each test boots
a real ``MiniCroft`` pinned to the adapt pipeline (via ``E2EPipelineHarness``),
emits the spec registration message on the wire, sends a matching utterance, and
asserts the intent dispatches ``<skill_id>:<intent_name>`` — proving the
registration was consumed off the spec topic, not the legacy path.

xfail discipline (mirrors the cross-repo ``ovos-test-harness`` conformance
suite): a clause the engine does not yet honour per the spec letter is
``@pytest.mark.xfail(strict=False, reason=...)`` quoting the clause and what the
engine actually does, so it flips to a pass once the impl converges.
"""
import unittest

import pytest

ovoscope = pytest.importorskip(
    "ovoscope", reason="ovoscope not installed; skipping E2E tests"
)

from ovoscope import (  # noqa: E402
    E2EPipelineHarness,
    make_session,
)
from ovos_bus_client.message import Message  # noqa: E402
from ovos_spec_tools import SpecMessage  # noqa: E402

from ovos_adapt.opm import AdaptPipeline  # noqa: E402

PIPELINE_ID = "ovos-adapt-pipeline-plugin"
CONFIG_KEY = "adapt"

# Spec topics (resolve to the ovos.intent.* / ovos.entity.* strings on the wire).
REGISTER_KEYWORD = str(SpecMessage.INTENT_REGISTER_KEYWORD)
REGISTER_TEMPLATE = str(SpecMessage.INTENT_REGISTER_TEMPLATE)
INTENT_DEREGISTER = str(SpecMessage.INTENT_DEREGISTER)
SKILL_DEREGISTER = str(SpecMessage.SKILL_DEREGISTER)
INTENT_DISABLE = str(SpecMessage.INTENT_DISABLE)
INTENT_ENABLE = str(SpecMessage.INTENT_ENABLE)


class _Intent4AdaptHarness(E2EPipelineHarness):
    PIPELINE_ID = PIPELINE_ID
    CONFIG_KEY = CONFIG_KEY
    PLUGIN_CONFIG = {}
    SKILL_ID = "intent4_adapt.skill"

    pipeline: AdaptPipeline  # type: ignore[assignment]

    def setUp(self):
        super().setUp()
        # Adapt realises §8.5 disable by mutating the *session* blacklist, and
        # the no-session path resolves to the shared SessionManager.default_
        # session singleton — its blacklist leaks across tests. Reset it so a
        # prior disable test cannot suppress a later match.
        from ovos_bus_client.session import SessionManager
        SessionManager.default_session.blacklisted_intents = []
        SessionManager.default_session.blacklisted_skills = []

    def _register_keyword(self, intent_name, required, *, optional=None,
                          one_of=None, excluded=None, lang="en-US", settle=1.0):
        """Emit a §5 ``ovos.intent.register.keyword`` payload on the bus.

        ``required`` etc. are ``{name: [samples]}`` dicts; this builds the
        shape-stable four-key payload the spec mandates (§5.2).
        """
        import time

        def _descs(d):
            return [{"name": n, "samples": s} for n, s in (d or {}).items()]

        payload = {
            "skill_id": self.SKILL_ID,
            "intent_name": intent_name,
            "lang": lang,
            "required": _descs(required),
            "optional": _descs(optional),
            "one_of": [_descs(g) for g in (one_of or [])],
            "excluded": _descs(excluded),
        }
        self.bus.emit(Message(REGISTER_KEYWORD, payload,
                              {"skill_id": self.SKILL_ID}))
        time.sleep(settle)

    def _emit(self, topic, intent_name=None, settle=0.5, **extra):
        import time
        data = {"skill_id": self.SKILL_ID, "lang": "en-US"}
        if intent_name is not None:
            data["intent_name"] = intent_name
        data.update(extra)
        self.bus.emit(Message(topic, data, {"skill_id": self.SKILL_ID}))
        time.sleep(settle)


class TestSpecKeywordConsumed(_Intent4AdaptHarness):
    """§5: a keyword intent registered on the spec topic becomes matchable."""

    def test_spec_keyword_registration_is_matchable(self):
        """Registering via ``ovos.intent.register.keyword`` makes the intent
        matchable (§5) — proving adapt consumed the spec topic, not legacy."""
        self._register_keyword(
            "lights_off",
            required={"TurnOff": ["off", "disable", "shutdown"],
                      "Light": ["light", "lights", "lamp"]},
        )
        msg = self.send_and_capture(
            "turn off the lights",
            expected_types=[f"{self.SKILL_ID}:lights_off"],
        )
        self.assertIsNotNone(msg, "expected intent match from spec registration")
        self.assertEqual(msg.msg_type, f"{self.SKILL_ID}:lights_off")
        self.assertEqual(msg.data.get("utterance"), "turn off the lights")

    def test_spec_one_of_group(self):
        """A ``one_of`` group member satisfies the group (§5.2)."""
        self._register_keyword(
            "lights",
            required={"Light": ["light", "lights"]},
            one_of=[{"TurnOn": ["on", "enable"], "TurnOff": ["off", "disable"]}],
        )
        msg = self.send_and_capture(
            "turn on lights", expected_types=[f"{self.SKILL_ID}:lights"]
        )
        self.assertIsNotNone(msg, "one_of group member should satisfy the group")

    def test_spec_excluded_suppresses_match(self):
        """An ``excluded`` keyword blocks the match (§5.2)."""
        self._register_keyword(
            "lights_off",
            required={"TurnOff": ["off"], "Light": ["lights"]},
            excluded={"Question": ["what", "how"]},
        )
        self.expect_no_match("what turns off the lights", timeout=3.0)


class TestLegacyStillConsumed(_Intent4AdaptHarness):
    """Back-compat: the legacy ``register_vocab`` / ``register_intent`` path
    still matches alongside the spec topic (memory: handlers run *in addition*)."""

    def test_legacy_keyword_registration_still_matches(self):
        from ovoscope import register_adapt_intent, register_adapt_vocab
        from ovos_workshop.intents import IntentBuilder

        register_adapt_vocab(self.bus, f"{self.SKILL_ID}:TurnOff", ["off"])
        register_adapt_vocab(self.bus, f"{self.SKILL_ID}:Light", ["lights"])
        register_adapt_intent(
            self.bus,
            IntentBuilder(f"{self.SKILL_ID}:lights_off")
            .require(f"{self.SKILL_ID}:TurnOff")
            .require(f"{self.SKILL_ID}:Light"),
        )
        msg = self.send_and_capture(
            "turn off the lights",
            expected_types=[f"{self.SKILL_ID}:lights_off"],
        )
        self.assertIsNotNone(msg, "legacy registration must still match")


class TestSpecDeregister(_Intent4AdaptHarness):
    """§8.2 / §8.4: spec deregistration removes a spec-registered intent."""

    def test_spec_deregister_removes_intent(self):
        """After ``ovos.intent.deregister`` the spec-registered intent no longer
        matches (§8.2)."""
        self._register_keyword(
            "lights_off",
            required={"TurnOff": ["off"], "Light": ["lights"]},
        )
        self.assertIsNotNone(
            self.send_and_capture("turn off the lights",
                                  expected_types=[f"{self.SKILL_ID}:lights_off"]),
            "sanity: intent should match before deregister",
        )
        self._emit(INTENT_DEREGISTER, "lights_off")
        self.expect_no_match("turn off the lights", timeout=3.0)

    def test_spec_skill_deregister_removes_intent(self):
        """``ovos.skill.deregister`` removes the whole skill's intents (§8.4)."""
        self._register_keyword(
            "lights_off",
            required={"TurnOff": ["off"], "Light": ["lights"]},
        )
        self._emit(SKILL_DEREGISTER)
        self.expect_no_match("turn off the lights", timeout=3.0)


class TestSpecDisableEnable(_Intent4AdaptHarness):
    """§8.5: ``ovos.intent.disable`` suppresses, ``ovos.intent.enable`` re-arms.

    DIVERGENCE (real finding): unlike padatious / padacioso / nebulento /
    palavreado — which keep a *global* disabled-set keyed on the registration —
    adapt realises disable by appending the intent to the **session**
    blacklist (``SessionManager.get(message).blacklisted_intents``). It is
    therefore scoped to whichever Session the disable Message carries. These
    tests drive the *default* session (no session override on either the
    disable or the utterance), where ``SessionManager`` returns the shared
    ``default_session`` singleton, so the suppression is observable. A disable
    addressed to one session would NOT suppress an utterance in another — a
    departure from the spec's registration-scoped wording in §8.5.
    """

    def test_spec_disable_suppresses_on_default_session(self):
        self._register_keyword(
            "lights_off",
            required={"TurnOff": ["off"], "Light": ["lights"]},
        )
        self._emit(INTENT_DISABLE, "lights_off")
        # default session (no override) — same one the disable mutated
        self.expect_no_match("turn off the lights", timeout=3.0)

    def test_spec_enable_rearms_on_default_session(self):
        self._register_keyword(
            "lights_off",
            required={"TurnOff": ["off"], "Light": ["lights"]},
        )
        self._emit(INTENT_DISABLE, "lights_off")
        self._emit(INTENT_ENABLE, "lights_off")
        msg = self.send_and_capture(
            "turn off the lights",
            expected_types=[f"{self.SKILL_ID}:lights_off"],
        )
        self.assertIsNotNone(msg, "intent should match again after enable")

    @pytest.mark.xfail(
        strict=False,
        reason="INTENT-4 §8.5: 'plugins exclude it from match candidacy until "
               "it is re-enabled' — adapt scopes disable to the disable "
               "Message's Session (SessionManager.get(message).blacklisted_"
               "intents), so a disable on one session does NOT suppress a "
               "match in a different session; the others keep a global set.",
    )
    def test_spec_disable_is_global_across_sessions(self):
        """A disable with no session must suppress an utterance carrying an
        unrelated session (§8.5 is registration-scoped, not session-scoped)."""
        self._register_keyword(
            "lights_off",
            required={"TurnOff": ["off"], "Light": ["lights"]},
        )
        self._emit(INTENT_DISABLE, "lights_off")  # default session
        other = make_session("intent4-other-session")
        self.expect_no_match("turn off the lights", session=other, timeout=3.0)


class TestNegativeTemplateTopic(_Intent4AdaptHarness):
    """§11: a keyword engine MUST NOT consume the *template* topic."""

    def test_template_topic_does_not_match_on_keyword_engine(self):
        """Registering on ``ovos.intent.register.template`` must not make an
        intent matchable in adapt — adapt is a keyword engine (§11)."""
        import time
        self.bus.emit(Message(REGISTER_TEMPLATE, {
            "skill_id": self.SKILL_ID,
            "intent_name": "play_music",
            "lang": "en-US",
            "samples": ["play {query}", "put on {query}"],
        }, {"skill_id": self.SKILL_ID}))
        time.sleep(0.5)
        self.expect_no_match("play the beatles", timeout=3.0)


if __name__ == "__main__":
    unittest.main()
