# Copyright 2026 Open Voice OS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
"""Regression tests for the CodeRabbit findings on PR #63:

- FINDING 1: multi-group regexes must record every named group, not just
  the first, or extra groups fall through to the collision-prone prefix
  fallback on detach.
- FINDING 2: two skills that collide on the same entity_type (e.g. because
  their skill_ids normalize to the same string) must not have one skill's
  detach silently drop the other skill's still-live entity; a collision
  warning must be logged at register time.
- FINDING 3: ``DomainAdaptPipeline.register_vocabulary`` must route by an
  explicit ``skill_id`` when it maps to a known domain, instead of always
  falling back to the entity_type-prefix guess (which can pick the wrong
  domain when prefixes overlap).
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_adapt.intent import IntentBuilder

from ovos_adapt.opm import AdaptPipeline, DomainAdaptPipeline


class TestRegexMultiGroupOwnership(TestCase):
    """FINDING 1."""

    def test_all_named_groups_recorded(self):
        pipeline = AdaptPipeline(mock.Mock())
        lang = pipeline.lang
        regex_str = r"play (?P<Artist>.*) by (?P<Album>.*)"
        pipeline.register_vocabulary(
            entity_value=None, entity_type=None, alias_of=None,
            regex_str=regex_str, lang=lang, skill_id='music.skill')
        self.assertEqual(pipeline._regex_owners['music.skill'],
                         {'Artist', 'Album'})


class TestCrossSkillEntityOwnership(TestCase):
    """FINDING 2."""

    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())
        self.lang = self.pipeline.lang

    def _has_entity(self, value, entity_type):
        matches = list(self.pipeline.engines[self.lang].trie.lookup(value.lower()))
        return any((value, entity_type) in m['data'] for m in matches)

    def test_register_collision_logs_warning(self):
        self.pipeline.register_vocabulary(
            entity_value='rock', entity_type='sharedType', alias_of=None,
            regex_str=None, lang=self.lang, skill_id='foo-bar')
        with mock.patch('ovos_adapt.opm.LOG') as mock_log:
            self.pipeline.register_vocabulary(
                entity_value='rock', entity_type='sharedType', alias_of=None,
                regex_str=None, lang=self.lang, skill_id='foo.bar')
        mock_log.warning.assert_called_once()
        msg = mock_log.warning.call_args[0][0]
        self.assertIn('sharedType', msg)
        self.assertIn('foo-bar', msg)
        self.assertIn('foo.bar', msg)

    def test_detach_one_owner_survives_other_owner(self):
        # Two colliding skill_ids both register the same entity_type.
        self.pipeline.register_vocabulary(
            entity_value='rock', entity_type='sharedType', alias_of=None,
            regex_str=None, lang=self.lang, skill_id='foo-bar')
        self.pipeline.register_vocabulary(
            entity_value='rock', entity_type='sharedType', alias_of=None,
            regex_str=None, lang=self.lang, skill_id='foo.bar')
        self.assertTrue(self._has_entity('rock', 'sharedType'))

        # Detaching ONE owner must NOT drop the shared entity: the other
        # skill's ownership set still references it.
        self.pipeline.detach_skill('foo-bar')
        self.assertTrue(self._has_entity('rock', 'sharedType'),
                        "entity dropped while another skill still owns it")

        # Detaching the SECOND (last) owner must now drop it.
        self.pipeline.detach_skill('foo.bar')
        self.assertFalse(self._has_entity('rock', 'sharedType'),
                         "entity survived after its last owner detached")


class TestDomainVocabRoutingBySkillId(TestCase):
    """FINDING 3."""

    def setUp(self):
        self.pipeline = DomainAdaptPipeline(mock.Mock())
        self.lang = self.pipeline.lang

        # Domain "cal.skill" normalizes its entity prefix to "cal_skill".
        intent_a = (IntentBuilder('cal.skill:CalIntent')
                    .require('cal_skillTrigger'))
        # Domain "cal" normalizes its entity prefix to "cal".
        intent_b = (IntentBuilder('cal:CalIntent')
                    .require('calTrigger'))

        self.pipeline.handle_register_intent(
            Message('register_intent', intent_a.__dict__))
        self.pipeline.handle_register_intent(
            Message('register_intent', intent_b.__dict__))

    def _in_domain(self, domain, value):
        matches = list(
            self.pipeline.engines[self.lang].domains[domain].trie.lookup(
                value.lower()))
        return len(matches) > 0

    def test_explicit_skill_id_routes_to_correct_domain(self):
        # entity_type "cal_skillWord" overlaps BOTH domain prefixes
        # ("cal_skill" from cal.skill and "cal" from "cal"), with
        # "cal_skill" being the longer (winning) prefix match. But this
        # vocab is explicitly registered by skill "cal", not "cal.skill".
        self.pipeline.register_vocabulary(
            entity_value='hello', entity_type='cal_skillWord',
            alias_of=None, regex_str=None, lang=self.lang, skill_id='cal')

        # Must land in the domain actually owning the skill_id ("cal"),
        # NOT the domain _resolve_entity_domain's prefix guess would pick
        # ("cal.skill").
        self.assertTrue(self._in_domain('cal', 'hello'),
                        "vocab did not land in the skill_id-owned domain")
        self.assertFalse(self._in_domain('cal.skill', 'hello'),
                         "vocab wrongly landed in the prefix-guessed domain")

    def test_unmapped_skill_id_falls_back_to_prefix_guess(self):
        # skill_id that maps to no known domain -> falls back to
        # _resolve_entity_domain's prefix guess, same as before the fix.
        self.pipeline.register_vocabulary(
            entity_value='world', entity_type='cal_skillOther',
            alias_of=None, regex_str=None, lang=self.lang,
            skill_id='unregistered.skill')
        self.assertTrue(self._in_domain('cal.skill', 'world'))
