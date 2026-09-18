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
"""OVOS-CONTEXT-1 requires_context / excludes_context match-time gating.

A candidate produced by the adapt engine is admitted only when its
``requires_context`` keys are all live in ``session.intent_context`` and none
of its ``excludes_context`` keys are (OVOS-CONTEXT-1 §6/§6.1). Ungated intents
are unaffected.
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovos_spec_tools import SpecMessage

from ovos_adapt.opm import AdaptPipeline

SKILL_ID = "lighting.skill"


class TestContext1Gating(TestCase):
    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())

    def _register(self, requires_context=None, excludes_context=None):
        payload = {
            "skill_id": SKILL_ID,
            "intent_name": "lights_on",
            "lang": "en-US",
            "required": [
                {"name": "turn", "samples": ["turn on", "switch on"]},
                {"name": "lights", "samples": ["lights", "lamp"]},
            ],
            "optional": [],
            "one_of": [],
            "excluded": [],
        }
        if requires_context is not None:
            payload["requires_context"] = requires_context
        if excludes_context is not None:
            payload["excludes_context"] = excludes_context
        msg = Message(SpecMessage.INTENT_REGISTER_KEYWORD, payload,
                      {"skill_id": SKILL_ID})
        self.pipeline.handle_spec_register_keyword(msg)

    def _match(self, utterance, intent_context=None, lang="en-US"):
        sess = Session("sess")
        sess.intent_context = intent_context or {}
        msg = Message("intent.service.adapt.get",
                      data={"utterance": utterance, "lang": lang},
                      context={"session": sess.serialize()})
        self.pipeline.handle_get_adapt(msg)
        return self.pipeline.bus.emit.call_args[0][0].data["intent"]

    def test_requires_context_absent_blocks_match(self):
        """requires_context=['kitchen'] blocks the match when kitchen is not live."""
        self._register(requires_context=["kitchen"])
        # empty context -> gate fails -> no match
        self.assertIsNone(self._match("turn on lights"))

    def test_requires_context_present_allows_match(self):
        """A live private 'kitchen' entry under the skill_id satisfies the gate."""
        self._register(requires_context=["kitchen"])
        ctx = {f"{SKILL_ID}:kitchen": {"value": True}}
        intent = self._match("turn on lights", intent_context=ctx)
        self.assertIsNotNone(intent)
        self.assertEqual(intent["intent_type"], f"{SKILL_ID}:lights_on")

    def test_requires_context_wrong_scope_blocks(self):
        """A shared (bare) 'kitchen' does NOT satisfy a private-scope gate."""
        self._register(requires_context=["kitchen"])
        ctx = {"kitchen": {"value": True}}  # shared, not <skill_id>:kitchen
        self.assertIsNone(self._match("turn on lights", intent_context=ctx))

    def test_excludes_context_live_drops_match(self):
        """excludes_context=['kitchen'] drops the candidate when kitchen is live."""
        self._register(excludes_context=["kitchen"])
        ctx = {f"{SKILL_ID}:kitchen": {"value": True}}
        self.assertIsNone(self._match("turn on lights", intent_context=ctx))

    def test_excludes_context_absent_allows_match(self):
        """Without the excluded key live, an excludes-gated intent still matches."""
        self._register(excludes_context=["kitchen"])
        intent = self._match("turn on lights")
        self.assertIsNotNone(intent)
        self.assertEqual(intent["intent_type"], f"{SKILL_ID}:lights_on")

    def test_ungated_intent_unaffected(self):
        """An intent with no gate matches regardless of intent_context."""
        self._register()
        self.assertIsNotNone(self._match("turn on lights"))
        self.assertIsNotNone(
            self._match("turn on lights",
                        intent_context={f"{SKILL_ID}:kitchen": {"value": True}}))
