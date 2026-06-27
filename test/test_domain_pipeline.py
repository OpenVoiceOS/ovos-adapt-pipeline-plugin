# Copyright 2026 Open Voice OS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
"""Tests for the per-domain Adapt pipeline.

These tests ensure that ``DomainAdaptPipeline`` registers each skill's
intents into a dedicated sub-engine (a "domain") and that
``match_intent`` picks the correct skill regardless of how many domains
are registered.
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_adapt.intent import IntentBuilder

from ovos_adapt.engine import DomainIntentDeterminationEngine
from ovos_adapt.opm import DomainAdaptPipeline


def _vocab_msg(keyword, value):
    return Message('register_vocab',
                   {'entity_value': value, 'entity_type': keyword})


class TestDomainAdaptPipeline(TestCase):

    def setUp(self):
        self.pipeline = DomainAdaptPipeline(mock.Mock())

        # Skill A: weather
        intent_a = (IntentBuilder('weather.skill:WeatherIntent')
                    .require('weather_skillWeatherKeyword'))
        # Skill B: music
        intent_b = (IntentBuilder('music.skill:PlayIntent')
                    .require('music_skillPlayKeyword'))

        # Register intents first so the entity_type prefix index is
        # populated before vocab arrives.
        self.pipeline.handle_register_intent(
            Message('register_intent', intent_a.__dict__))
        self.pipeline.handle_register_intent(
            Message('register_intent', intent_b.__dict__))

        self.pipeline.handle_register_vocab(
            _vocab_msg('weather_skillWeatherKeyword', 'weather'))
        self.pipeline.handle_register_vocab(
            _vocab_msg('music_skillPlayKeyword', 'play'))

    def test_engine_is_domain_engine(self):
        for engine in self.pipeline.engines.values():
            self.assertIsInstance(engine, DomainIntentDeterminationEngine)

    def test_two_domains_registered(self):
        lang = self.pipeline.lang
        engine = self.pipeline.engines[lang]
        self.assertIn('weather.skill', engine.domains)
        self.assertIn('music.skill', engine.domains)
        # Each domain only owns its own intent parser.
        weather_names = [p.name for p in
                         engine.domains['weather.skill'].intent_parsers]
        music_names = [p.name for p in
                       engine.domains['music.skill'].intent_parsers]
        self.assertEqual(weather_names, ['weather.skill:WeatherIntent'])
        self.assertEqual(music_names, ['music.skill:PlayIntent'])

    def test_match_routes_to_weather_domain(self):
        match = self.pipeline.match_intent(('weather',), self.pipeline.lang, None)
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, 'weather.skill:WeatherIntent')
        self.assertEqual(match.skill_id, 'weather.skill')

    def test_match_routes_to_music_domain(self):
        match = self.pipeline.match_intent(('play',), self.pipeline.lang, None)
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, 'music.skill:PlayIntent')
        self.assertEqual(match.skill_id, 'music.skill')

    def test_detach_skill_drops_domain(self):
        self.pipeline.detach_skill('weather.skill')
        engine = self.pipeline.engines[self.pipeline.lang]
        self.assertNotIn('weather.skill', engine.domains)
        # The other domain is untouched.
        self.assertIn('music.skill', engine.domains)

    def test_detach_intent_removes_only_that_intent(self):
        self.pipeline.detach_intent('weather.skill:WeatherIntent')
        engine = self.pipeline.engines[self.pipeline.lang]
        names = [p.name for p in
                 engine.domains['weather.skill'].intent_parsers]
        self.assertEqual(names, [])
