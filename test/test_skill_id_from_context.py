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
"""OVOS-INTENT-4 §3.2: a §§5-8 message acts on its payload ``skill_id``.

The spec handlers take the target from the payload and never substitute
``context.skill_id`` for it, so a message that names another skill acts on
that skill. The legacy handlers keep the context, which is the only identity
the legacy wire carries.
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_spec_tools import SpecMessage

from ovos_bus_client.session import SessionManager

from ovos_adapt.opm import AdaptPipeline, LOG


def _warnings(mock_warning):
    return [call.args[0] if call.args else "" for call in mock_warning.call_args_list]


def _match(pipeline, utterance, lang="en-US"):
    msg = Message("intent.service.adapt.get",
                  data={"utterance": utterance, "lang": lang})
    pipeline.handle_get_adapt(msg)
    return pipeline.bus.emit.call_args[0][0].data["intent"]


class TestDetachSkillTakesSkillIdFromContext(TestCase):
    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())
        self.pipeline.bus.on(
            "register_vocab",
            lambda m: self.pipeline.handle_register_vocab(m))
        self.pipeline.register_vocabulary("play", "PlayKeyword", None, None,
                                          "en-US", skill_id="music.skill")
        from ovos_adapt.intent import IntentBuilder
        self.pipeline.register_intent(
            IntentBuilder("music.skill:play").require("PlayKeyword").build())

    def test_differing_payload_skill_id_is_ignored(self):
        msg = Message("detach_intent",
                      {"skill_id": "attacker.skill"},
                      {"skill_id": "music.skill"})
        with mock.patch.object(LOG, "warning") as warn:
            self.pipeline.handle_detach_skill(msg)
        self.assertIsNone(_match(self.pipeline, "play"))
        self.assertTrue(any("differs from" in w for w in _warnings(warn)))

    def test_missing_context_skill_id_is_dropped(self):
        msg = Message("detach_intent", {"skill_id": "music.skill"}, {})
        with mock.patch.object(LOG, "warning") as warn:
            self.pipeline.handle_detach_skill(msg)
        self.assertIsNotNone(_match(self.pipeline, "play"))
        self.assertTrue(any("missing" in w for w in _warnings(warn)))

    def test_matching_payload_detaches_as_before(self):
        msg = Message("detach_intent",
                      {"skill_id": "music.skill"},
                      {"skill_id": "music.skill"})
        self.pipeline.handle_detach_skill(msg)
        self.assertIsNone(_match(self.pipeline, "play"))


class TestSpecHandlersTakeSkillIdFromPayload(TestCase):
    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())

    def _register_keyword(self, skill_id, intent_name, sample, context_skill_id=None):
        payload = {"skill_id": skill_id, "intent_name": intent_name,
                  "lang": "en-US", "required": [{"name": "playKw",
                                                   "samples": [sample]}]}
        msg = Message(SpecMessage.INTENT_REGISTER_KEYWORD, payload,
                      {"skill_id": context_skill_id
                       if context_skill_id is not None else skill_id})
        self.pipeline.handle_spec_register_keyword(msg)

    def test_register_keyword_indexes_under_the_payload_skill(self):
        # a provisioning tool registering on another skill's behalf
        self._register_keyword("music.skill", "play_music", "play",
                                context_skill_id="admin.skill")
        match = _match(self.pipeline, "play")
        self.assertIsNotNone(match)
        self.assertEqual(match["intent_type"], "music.skill:play_music")

    def test_register_keyword_missing_context_registers(self):
        msg = Message(SpecMessage.INTENT_REGISTER_KEYWORD,
                      {"skill_id": "music.skill", "intent_name": "play_music",
                       "lang": "en-US", "required": [{"name": "playKw",
                                                        "samples": ["play"]}]},
                      {})
        self.pipeline.handle_spec_register_keyword(msg)
        match = _match(self.pipeline, "play")
        self.assertIsNotNone(match)
        self.assertEqual(match["intent_type"], "music.skill:play_music")

    def test_register_keyword_missing_payload_is_dropped(self):
        msg = Message(SpecMessage.INTENT_REGISTER_KEYWORD,
                      {"intent_name": "play_music", "lang": "en-US",
                       "required": [{"name": "playKw", "samples": ["play"]}]},
                      {"skill_id": "admin.skill"})
        with mock.patch.object(LOG, "warning") as warn:
            self.pipeline.handle_spec_register_keyword(msg)
        self.assertIsNone(_match(self.pipeline, "play"))
        self.assertTrue(any("missing skill_id" in w for w in _warnings(warn)))

    def test_register_keyword_matching_payload_registers_as_before(self):
        self._register_keyword("music.skill", "play_music", "play")
        self.assertIsNotNone(_match(self.pipeline, "play"))

    def test_skill_deregister_removes_the_named_skill_not_the_sender(self):
        self._register_keyword("music.skill", "play_music", "play")
        self._register_keyword("admin.skill", "shutdown", "shut down")
        msg = Message(SpecMessage.SKILL_DEREGISTER,
                      {"skill_id": "music.skill"},
                      {"skill_id": "admin.skill"})
        self.pipeline.handle_spec_deregister_skill(msg)
        self.assertIsNone(_match(self.pipeline, "play"))
        surviving = _match(self.pipeline, "shut down")
        self.assertIsNotNone(surviving)
        self.assertEqual(surviving["intent_type"], "admin.skill:shutdown")

    def test_skill_deregister_missing_context_removes_the_payload_skill(self):
        self._register_keyword("music.skill", "play_music", "play")
        msg = Message(SpecMessage.SKILL_DEREGISTER, {"skill_id": "music.skill"}, {})
        self.pipeline.handle_spec_deregister_skill(msg)
        self.assertIsNone(_match(self.pipeline, "play"))

    def test_skill_deregister_missing_payload_is_dropped(self):
        self._register_keyword("music.skill", "play_music", "play")
        msg = Message(SpecMessage.SKILL_DEREGISTER, {}, {"skill_id": "music.skill"})
        with mock.patch.object(LOG, "warning") as warn:
            self.pipeline.handle_spec_deregister_skill(msg)
        self.assertIsNotNone(_match(self.pipeline, "play"))
        self.assertTrue(any("missing skill_id" in w for w in _warnings(warn)))


class TestRegisterVocabTakesSkillIdFromContext(TestCase):
    """OVOS-INTENT-4 §3.1/§3.2: a registration without a context skill_id
    is malformed. Registering it anyway with owner None means
    ``detach_skill`` can never remove it, so the word outlives the skill's
    detach and leaks into any later, unrelated intent that requires the
    same entity_type."""

    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())

    def _register_vocab(self, entity_value, entity_type, *, skill_id=None):
        data = {"entity_value": entity_value, "entity_type": entity_type}
        context = {"skill_id": skill_id} if skill_id else {}
        self.pipeline.handle_register_vocab(
            Message("register_vocab", data, context))

    def test_missing_context_skill_id_is_dropped_with_warning(self):
        with mock.patch.object(LOG, "warning") as warn:
            self._register_vocab("apple", "Fruit")
        self.assertEqual(self.pipeline.registered_vocab, [])
        self.assertTrue(any("missing" in w for w in _warnings(warn)))

    def test_matching_context_registers_as_before(self):
        self._register_vocab("apple", "Fruit", skill_id="skill_a")
        self.assertEqual(len(self.pipeline.registered_vocab), 1)

    def test_ownerless_vocab_does_not_leak_into_a_later_unrelated_skill(self):
        from ovos_adapt.intent import IntentBuilder

        # skill_a registers "Fruit" WITHOUT a context skill_id (malformed).
        self._register_vocab("apple", "Fruit")

        # skill_a is detached; an ownerless entry cannot be scoped to it,
        # so this must not matter to the outcome below either way.
        self.pipeline.handle_detach_skill(
            Message("detach_skill", {"skill_id": "skill_a"},
                    {"skill_id": "skill_a"}))

        # skill_b registers an unrelated intent requiring "Fruit".
        self.pipeline.register_intent(
            IntentBuilder("skill_b:pick").require("Fruit").build())

        msg = Message("intent.service.adapt.get",
                      data={"utterance": "apple", "lang": "en-US"})
        self.pipeline.handle_get_adapt(msg)
        reply = self.pipeline.bus.emit.call_args[0][0]
        self.assertIsNone(
            reply.data["intent"],
            "a vocab registration rejected for missing context.skill_id "
            "must not silently leak into an unrelated skill's intent")


class TestEnableDisableAreExemptFromContextIdentity(TestCase):
    """OVOS-INTENT-4 §3.2 exempts ``ovos.intent.enable``/``ovos.intent.disable``
    from the identity check: they are control messages, not ownership
    claims. The payload skill_id names the TARGET intent's skill, while
    context.skill_id names the SOURCE issuing the control, and the two MAY
    differ (cross-skill control, e.g. an admin UI or a conflict-resolving
    skill suppressing another skill's intent)."""

    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())
        SessionManager.default_session.blacklisted_intents = []

    def tearDown(self):
        SessionManager.default_session.blacklisted_intents = []

    def test_cross_skill_disable_and_enable(self):
        target = "music.skill:play_music"

        disable = Message(SpecMessage.INTENT_DISABLE,
                          {"skill_id": "music.skill", "intent_name": "play_music"},
                          {"skill_id": "controller.skill"})
        self.pipeline.handle_spec_disable_intent(disable)
        sess = SessionManager.get(disable)
        self.assertIn(target, sess.blacklisted_intents or [])

        enable = Message(SpecMessage.INTENT_ENABLE,
                         {"skill_id": "music.skill", "intent_name": "play_music"},
                         {"skill_id": "controller.skill"})
        self.pipeline.handle_spec_enable_intent(enable)
        sess = SessionManager.get(enable)
        self.assertNotIn(target, sess.blacklisted_intents or [])
