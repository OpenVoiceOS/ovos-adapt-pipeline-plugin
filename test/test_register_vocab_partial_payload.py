# Copyright 2026 Open Voice OS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
"""Registration payloads with missing fields must never crash the parser.

OVOS-INTENT-4 (§5.3/§6.3): consumers skip malformed registrations with a
warning and only reject a registration outright when nothing usable remains.

Legacy ``register_vocab`` payloads come in two shapes:

- keyword: ``{"entity_value": ..., "entity_type": ...}`` (no ``regex``)
- regex:   ``{"regex": ...}`` (no ``entity_type``/``entity_value``)

The regex shape carries no ``entity_type``, so domain routing must derive
the owning skill from the regex named group instead of crashing on ``None``.
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message

from ovos_adapt.intent import IntentBuilder
from ovos_adapt.opm import (AdaptPipeline, DomainAdaptPipeline,
                            HierarchicalAdaptPipeline)


def _register_nav_intent(pipeline):
    intent = (IntentBuilder('nav.skill:NavIntent')
              .require('nav_skillGoKeyword')
              .require('nav_skillLocation'))
    pipeline.handle_register_intent(Message('register_intent', intent.__dict__))


class RegexVocabWithoutEntityTypeTest(TestCase):
    """Regex registrations (no entity_type) must register, not crash."""

    def test_domain_pipeline_regex_payload(self):
        pipeline = DomainAdaptPipeline(mock.Mock())
        _register_nav_intent(pipeline)
        # exact legacy regex payload shape: no entity_type/entity_value
        pipeline.handle_register_vocab(
            Message('register_vocab',
                    {'regex': r'to (?P<nav_skillLocation>.*)'}))
        engine = pipeline.engines[pipeline.lang]
        # routed to the owning skill's domain via the regex group name
        self.assertIn(r'to (?P<nav_skillLocation>.*)',
                      engine.domains['nav.skill']._regex_strings)

    def test_hierarchical_pipeline_regex_payload(self):
        pipeline = HierarchicalAdaptPipeline(mock.Mock())
        _register_nav_intent(pipeline)
        pipeline.handle_register_vocab(
            Message('register_vocab',
                    {'regex': r'to (?P<nav_skillLocation>.*)'}))
        engine = pipeline.engines[pipeline.lang]
        self.assertIn(r'to (?P<nav_skillLocation>.*)',
                      engine.domains['nav.skill']._regex_strings)

    def test_regex_without_named_group_falls_back(self):
        pipeline = DomainAdaptPipeline(mock.Mock())
        _register_nav_intent(pipeline)
        # no named group -> nothing to route by; still must not crash
        pipeline.handle_register_vocab(
            Message('register_vocab', {'regex': r'to .*'}))

    def test_regex_matches_end_to_end(self):
        pipeline = DomainAdaptPipeline(mock.Mock())
        _register_nav_intent(pipeline)
        pipeline.handle_register_vocab(
            Message('register_vocab',
                    {'entity_value': 'go', 'entity_type': 'nav_skillGoKeyword'}))
        pipeline.handle_register_vocab(
            Message('register_vocab',
                    {'regex': r'go to (?P<nav_skillLocation>.*)'}))
        result = pipeline.match_intent(('go to lisbon',), pipeline.lang)
        self.assertIsNotNone(result)
        self.assertEqual(result.match_type, 'nav.skill:NavIntent')


class UnusableVocabPayloadTest(TestCase):
    """Payloads with neither regex nor keyword data are skipped with a warning."""

    def _check_skipped(self, pipeline):
        before = list(pipeline.registered_vocab)
        with mock.patch('ovos_adapt.opm.LOG.warning') as warn:
            pipeline.handle_register_vocab(
                Message('register_vocab', {'alias_of': 'thing'}))
        warn.assert_called_once()
        self.assertEqual(pipeline.registered_vocab, before)

    def test_flat_pipeline_skips(self):
        self._check_skipped(AdaptPipeline(mock.Mock()))

    def test_domain_pipeline_skips(self):
        pipeline = DomainAdaptPipeline(mock.Mock())
        _register_nav_intent(pipeline)
        self._check_skipped(pipeline)

    def test_keyword_payload_missing_value_skipped(self):
        pipeline = DomainAdaptPipeline(mock.Mock())
        _register_nav_intent(pipeline)
        before = list(pipeline.registered_vocab)
        with mock.patch('ovos_adapt.opm.LOG.warning') as warn:
            pipeline.handle_register_vocab(
                Message('register_vocab', {'entity_type': 'nav_skillGoKeyword'}))
        warn.assert_called_once()
        self.assertEqual(pipeline.registered_vocab, before)
