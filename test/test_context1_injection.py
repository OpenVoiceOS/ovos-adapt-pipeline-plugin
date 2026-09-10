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
"""OVOS-CONTEXT-1 §7 pre-match context injection for the adapt keyword engine.

A live non-null string entry in ``session.intent_context`` is injected as a
candidate keyword for the vocabulary of the same name **before** matching, so
an intent requiring that keyword can match even when the utterance lacks it.
An utterance-produced value for the same keyword wins over the injected one,
and a flag entry (``value=null``) is never injected -- it only gates (see the
requires_context gating contract).
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session

from ovos_adapt.intent import IntentBuilder
from ovos_adapt.opm import AdaptPipeline

SKILL_ID = "bio.skill"
INTENT = f"{SKILL_ID}:height_query"


class TestContext1Injection(TestCase):
    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())
        # A keyword intent requiring a `tall_query` phrase and a `person`
        # keyword; `person` names both a required vocabulary and the reported
        # slot. The utterance "how tall is he" never fills `person`.
        self.pipeline.register_vocabulary("how tall is", "tall_query",
                                          None, None, "en-US")
        self.pipeline.register_vocabulary("bob", "person", None, None, "en-US")
        self.pipeline.register_vocabulary("alice", "person", None, None,
                                          "en-US")
        intent = IntentBuilder(INTENT).require("tall_query").require(
            "person").build()
        self.pipeline.register_intent(intent)

    def _match(self, utterance, intent_context=None):
        sess = Session("sess")
        sess.intent_context = intent_context or {}
        msg = Message("intent.service.adapt.get",
                      data={"utterance": utterance, "lang": "en-US"},
                      context={"session": sess.serialize()})
        self.pipeline.handle_get_adapt(msg)
        return self.pipeline.bus.emit.call_args[0][0].data["intent"]

    def test_no_context_no_match(self):
        """Without a live `person` entry the person keyword stays unfilled."""
        self.assertIsNone(self._match("how tall is he"))

    def test_shared_context_injected_as_keyword(self):
        """A live shared {person: Bob} fills the person keyword and slot."""
        ctx = {"person": {"value": "Bob"}}
        intent = self._match("how tall is he", intent_context=ctx)
        self.assertIsNotNone(intent)
        self.assertEqual(intent["intent_type"], INTENT)
        self.assertEqual(intent["person"], "Bob")

    def test_private_owner_context_injected(self):
        """A live private <skill_id>:person entry fills the owner's keyword."""
        ctx = {f"{SKILL_ID}:person": {"value": "Bob"}}
        intent = self._match("how tall is he", intent_context=ctx)
        self.assertIsNotNone(intent)
        self.assertEqual(intent["person"], "Bob")

    def test_utterance_value_wins_over_context(self):
        """A person keyword in the utterance beats the injected candidate."""
        ctx = {"person": {"value": "Alice"}}
        intent = self._match("how tall is bob", intent_context=ctx)
        self.assertIsNotNone(intent)
        # adapt normalizes registered vocabulary to lowercase; the point is
        # the utterance value ("bob"), not the injected context ("Alice").
        self.assertEqual(intent["person"], "bob")

    def test_flag_entry_not_injected(self):
        """A null-valued (flag) entry gates only -- it is never injected."""
        ctx = {"person": {"value": None}}
        self.assertIsNone(self._match("how tall is he", intent_context=ctx))

    def test_expired_entry_not_injected(self):
        """A dead entry (turns_remaining<=0) is not injected."""
        ctx = {"person": {"value": "Bob", "turns_remaining": 0}}
        self.assertIsNone(self._match("how tall is he", intent_context=ctx))
