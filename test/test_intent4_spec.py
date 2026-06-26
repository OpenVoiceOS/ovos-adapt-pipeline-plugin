# Copyright 2024 OpenVoiceOS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Tests for OVOS-INTENT-4 keyword/entity registration consumption.

These cover the *new* spec topics (``ovos.intent.register.keyword`` et al.)
consumed alongside the legacy ``register_vocab`` / ``register_intent`` flow.
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_spec_tools import SpecMessage

from ovos_adapt.opm import AdaptPipeline


class TestIntent4KeywordRegistration(TestCase):
    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())

    def _register_keyword(self, **payload):
        msg = Message(SpecMessage.INTENT_REGISTER_KEYWORD, payload,
                      {"skill_id": payload.get("skill_id")})
        self.pipeline.handle_spec_register_keyword(msg)

    def _match(self, utterance, lang="en-US"):
        msg = Message("intent.service.adapt.get",
                      data={"utterance": utterance, "lang": lang})
        self.pipeline.handle_get_adapt(msg)
        return self.pipeline.bus.emit.call_args[0][0].data["intent"]

    def test_keyword_intent_matches_utterance(self):
        """Register via ovos.intent.register.keyword, assert an utterance matches."""
        self._register_keyword(
            skill_id="lighting.skill",
            intent_name="set_brightness",
            lang="en-US",
            required=[
                {"name": "set", "samples": ["set", "change", "adjust"]},
                {"name": "brightness", "samples": ["brightness", "light level"]},
            ],
            optional=[],
            one_of=[],
            excluded=[],
        )

        intent = self._match("set the brightness")
        self.assertIsNotNone(intent)
        self.assertEqual(intent["intent_type"], "lighting.skill:set_brightness")

    def test_one_of_group(self):
        """A one_of group requires at least one member present."""
        self._register_keyword(
            skill_id="lighting.skill",
            intent_name="set_brightness",
            lang="en-US",
            required=[{"name": "set", "samples": ["set", "change", "adjust"]}],
            optional=[],
            one_of=[[
                {"name": "up", "samples": ["up", "higher", "brighter"]},
                {"name": "down", "samples": ["down", "lower", "dimmer"]},
            ]],
            excluded=[],
        )

        self.assertIsNotNone(self._match("set it higher"))
        self.assertIsNotNone(self._match("change it lower"))
        # required "set" present but no one_of member -> no match
        self.assertIsNone(self._match("set it"))

    def test_excluded_suppresses_match(self):
        """An excluded vocabulary suppresses the match when present."""
        self._register_keyword(
            skill_id="lighting.skill",
            intent_name="set_brightness",
            lang="en-US",
            required=[{"name": "brightness", "samples": ["brightness"]}],
            optional=[],
            one_of=[],
            excluded=[{"name": "question", "samples": ["what is", "how"]}],
        )
        self.assertIsNotNone(self._match("brightness"))
        self.assertIsNone(self._match("what is the brightness"))

    def test_malformed_no_required_no_one_of_rejected(self):
        """required and one_of both empty is malformed (INTENT-4 §5.3)."""
        self._register_keyword(
            skill_id="lighting.skill",
            intent_name="bad_intent",
            lang="en-US",
            required=[],
            optional=[{"name": "x", "samples": ["x"]}],
            one_of=[],
            excluded=[],
        )
        # nothing registered -> no match
        self.assertIsNone(self._match("x"))

    def test_template_expansion_in_samples(self):
        """INTENT-1 (a|b) / [opt] template syntax in samples is expanded."""
        self._register_keyword(
            skill_id="lighting.skill",
            intent_name="lights",
            lang="en-US",
            required=[{"name": "action",
                       "samples": ["turn (on|off) the [bright] lights"]}],
            optional=[],
            one_of=[],
            excluded=[],
        )
        self.assertIsNotNone(self._match("turn off the bright lights"))
        self.assertIsNotNone(self._match("turn on the lights"))

    def test_legacy_flow_still_works(self):
        """Legacy register_vocab/register_intent path is untouched."""
        from ovos_workshop.intents import IntentBuilder
        self.pipeline.handle_register_vocab(
            Message("register_vocab",
                    {"entity_value": "test", "entity_type": "testKeyword"}))
        self.pipeline.handle_register_intent(
            Message("register_intent",
                    IntentBuilder("skill:testIntent").require("testKeyword").__dict__))
        intent = self._match("test")
        self.assertIsNotNone(intent)
        self.assertEqual(intent["intent_type"], "skill:testIntent")


class TestIntent4Deregistration(TestCase):
    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())
        self._register()

    def _register(self):
        msg = Message(SpecMessage.INTENT_REGISTER_KEYWORD,
                      {"skill_id": "lighting.skill",
                       "intent_name": "set_brightness",
                       "lang": "en-US",
                       "required": [{"name": "brightness",
                                     "samples": ["brightness"]}],
                       "optional": [], "one_of": [], "excluded": []},
                      {"skill_id": "lighting.skill"})
        self.pipeline.handle_spec_register_keyword(msg)

    def _match(self, utterance, lang="en-US"):
        # match_intent is lru_cached; clear so re-matching after a
        # deregistration re-runs the engine instead of returning a stale hit.
        self.pipeline.match_intent.cache_clear()
        msg = Message("intent.service.adapt.get",
                      data={"utterance": utterance, "lang": lang})
        self.pipeline.handle_get_adapt(msg)
        return self.pipeline.bus.emit.call_args[0][0].data["intent"]

    def test_deregister_intent(self):
        self.assertIsNotNone(self._match("brightness"))
        self.pipeline.handle_spec_deregister_intent(
            Message(SpecMessage.INTENT_DEREGISTER,
                    {"skill_id": "lighting.skill",
                     "intent_name": "set_brightness", "lang": "en-US"},
                    {"skill_id": "lighting.skill"}))
        self.assertIsNone(self._match("brightness"))

    def test_deregister_skill(self):
        self.assertIsNotNone(self._match("brightness"))
        self.pipeline.handle_spec_deregister_skill(
            Message(SpecMessage.SKILL_DEREGISTER,
                    {"skill_id": "lighting.skill"},
                    {"skill_id": "lighting.skill"}))
        self.assertIsNone(self._match("brightness"))
