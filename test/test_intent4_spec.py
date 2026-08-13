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

from ovos_adapt.opm import AdaptPipeline, _entity_skill_id


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
        from ovos_adapt.intent import IntentBuilder
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


class TestEntitySkillIdNoTruncation(TestCase):
    """Regression coverage for the ``_entity_skill_id`` off-by-one bug.

    ``_entity_skill_id`` used to strip the skill_id's final character (a
    leftover from a legacy convention where skill_ids ended with a
    trailing dot). Modern skill_ids don't carry that trailing dot, so the
    truncation silently ate the last real character of every skill_id.
    Because both registration and detach derived their keys from the same
    truncating helper, two skill_ids differing only in their final
    character (e.g. ``"test.skillA"`` / ``"test.skillB"``) collapsed to
    the *same* normalized id -- so detaching one skill would also delete
    the other skill's entities via ``str.startswith``.
    """

    def test_helper_does_not_truncate_final_character(self):
        """The normalized form must preserve every character of skill_id."""
        # only '.' and '-' are rewritten to '_'; everything else, including
        # the final character, must survive untouched.
        self.assertEqual(_entity_skill_id("test.skillA"), "test_skillA")
        self.assertEqual(_entity_skill_id("test.skillB"), "test_skillB")

    def test_helper_is_injective_for_ids_differing_only_in_last_char(self):
        """Two distinct skill_ids must never normalize to the same string."""
        self.assertNotEqual(_entity_skill_id("test.skillA"),
                             _entity_skill_id("test.skillB"))
        # and neither may be a prefix of the other, since detach uses
        # str.startswith() against this normalized id
        a, b = _entity_skill_id("test.skillA"), _entity_skill_id("test.skillB")
        self.assertFalse(a.startswith(b))
        self.assertFalse(b.startswith(a))

    def test_detach_does_not_remove_other_skills_colliding_entities(self):
        """Detaching skill A must not remove skill B's entities.

        Before the fix, skill_id ``"test.skillA"`` and ``"test.skillB"``
        both normalized to ``"test_skill"`` (the trailing 'A'/'B' was
        truncated away), so detaching A also wiped B's vocabulary.
        """
        pipeline = AdaptPipeline(mock.Mock())

        def register(skill_id, intent_name, sample):
            msg = Message(SpecMessage.INTENT_REGISTER_KEYWORD,
                          {"skill_id": skill_id,
                           "intent_name": intent_name,
                           "lang": "en-US",
                           "required": [{"name": "greeting",
                                         "samples": [sample]}],
                           "optional": [], "one_of": [], "excluded": []},
                          {"skill_id": skill_id})
            pipeline.handle_spec_register_keyword(msg)

        def match(utterance):
            pipeline.match_intent.cache_clear()
            msg = Message("intent.service.adapt.get",
                          data={"utterance": utterance, "lang": "en-US"})
            pipeline.handle_get_adapt(msg)
            return pipeline.bus.emit.call_args[0][0].data["intent"]

        register("test.skillA", "greetA", "hello")
        register("test.skillB", "greetB", "howdy")

        self.assertIsNotNone(match("hello"))
        self.assertIsNotNone(match("howdy"))

        pipeline.detach_skill("test.skillA")

        self.assertIsNone(match("hello"),
                           "skill A's entity should be gone after its own detach")
        self.assertIsNotNone(match("howdy"),
                              "skill B's entity must survive skill A's detach")


class TestDetachSkillOwnershipScoping(TestCase):
    """Regression coverage for the true prefix-collision detach bugs.

    Unlike ``TestEntitySkillIdNoTruncation`` (which covers ids differing
    only in their final character), these ids are *genuine* prefixes of
    one another (``"skill-a"`` / ``"skill-ab"``, ``"foo.bar"`` /
    ``"foo.barz"``). Before the ownership-tracking fix, ``detach_skill``
    matched parsers/entities/regexes with a bare ``str.startswith()``
    against the shorter id, so detaching the shorter-named skill also
    wiped the longer-named sibling's registrations.
    """

    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())

    def _register_keyword(self, skill_id, intent_name, sample,
                          entity_name="greeting"):
        msg = Message(SpecMessage.INTENT_REGISTER_KEYWORD,
                      {"skill_id": skill_id,
                       "intent_name": intent_name,
                       "lang": "en-US",
                       "required": [{"name": entity_name,
                                     "samples": [sample]}],
                       "optional": [], "one_of": [], "excluded": []},
                      {"skill_id": skill_id})
        self.pipeline.handle_spec_register_keyword(msg)

    def _match(self, utterance):
        self.pipeline.match_intent.cache_clear()
        msg = Message("intent.service.adapt.get",
                      data={"utterance": utterance, "lang": "en-US"})
        self.pipeline.handle_get_adapt(msg)
        return self.pipeline.bus.emit.call_args[0][0].data["intent"]

    def test_dash_prefix_siblings_survive_shorter_skill_detach(self):
        """detach_skill("skill-a") must not remove "skill-ab"'s entities/parser."""
        self._register_keyword("skill-a", "greetA", "hello")
        self._register_keyword("skill-ab", "greetAB", "howdy")

        self.assertIsNotNone(self._match("hello"))
        self.assertIsNotNone(self._match("howdy"))

        self.pipeline.detach_skill("skill-a")

        self.assertIsNone(self._match("hello"))
        self.assertIsNotNone(self._match("howdy"),
                              "skill-ab's entity/parser must survive "
                              "skill-a's detach")

    def test_dotted_prefix_siblings_survive_shorter_skill_detach(self):
        """detach_skill("foo.bar") must not remove "foo.barz"'s entities/parser."""
        self._register_keyword("foo.bar", "greetBar", "hello")
        self._register_keyword("foo.barz", "greetBarz", "howdy")

        self.assertIsNotNone(self._match("hello"))
        self.assertIsNotNone(self._match("howdy"))

        self.pipeline.detach_skill("foo.bar")

        self.assertIsNone(self._match("hello"))
        self.assertIsNotNone(self._match("howdy"),
                              "foo.barz's entity/parser must survive "
                              "foo.bar's detach")

    def test_regex_prefix_siblings_survive_shorter_skill_detach(self):
        """Regex group names that prefix-collide must not cross-detach."""
        self.pipeline.handle_register_vocab(
            Message("register_vocab",
                    {"regex": r"the (?P<skill_aColor>.*) light"},
                    {"skill_id": "skill-a"}))
        self.pipeline.handle_register_vocab(
            Message("register_vocab",
                    {"regex": r"the (?P<skill_abColor>.*) shade"},
                    {"skill_id": "skill-ab"}))

        for lang in self.pipeline.engines:
            groups = [set(r.groupindex.keys())
                      for r in self.pipeline.engines[lang].regular_expressions_entities]
            self.assertTrue(any("skill_aColor" in g for g in groups))
            self.assertTrue(any("skill_abColor" in g for g in groups))

        self.pipeline.detach_skill("skill-a")

        for lang in self.pipeline.engines:
            groups = [set(r.groupindex.keys())
                      for r in self.pipeline.engines[lang].regular_expressions_entities]
            self.assertFalse(any("skill_aColor" in g for g in groups),
                              "skill-a's regex should be gone after its own detach")
            self.assertTrue(any("skill_abColor" in g for g in groups),
                             "skill-ab's regex must survive skill-a's detach")

    def test_unknown_owner_falls_back_to_prefix_match(self):
        """register_vocabulary called with no skill_id keeps the legacy
        prefix-fallback compat path: detach still removes it by prefix.
        """
        # bypass the bus handlers entirely -- no context, no skill_id
        self.pipeline.register_vocabulary(
            "hello", "skill_unowned_greeting", None, None, "en-US")

        self.pipeline.detach_skill("skill_unowned")

        found = False
        for lang in self.pipeline.engines:
            def match_func(data):
                return data and data[1] == "skill_unowned_greeting"
            ent_tuples = self.pipeline.engines[lang].trie.scan(match_func)
            found = found or bool(ent_tuples)
        self.assertFalse(found,
                         "unowned entity_type must still be removed via "
                         "the legacy prefix fallback")
