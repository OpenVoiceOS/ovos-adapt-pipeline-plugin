"""A vocab that carries skill_id is routed to that skill's domain, even
when it arrives before the first intent of the skill.

``handle_spec_register_keyword`` registers the samples before it builds
the intent. The domain pipelines routed such a vocab by an entity_type
prefix index that only fills on ``register_intent``, so the vocab landed
in a domain of its own and the intent never matched.
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_spec_tools import SpecMessage

from ovos_adapt.intent import IntentBuilder
from ovos_adapt.opm import DomainAdaptPipeline, HierarchicalAdaptPipeline


class _VocabBeforeIntentMixin:
    pipeline_class = DomainAdaptPipeline

    def setUp(self):
        self.pipeline = self.pipeline_class(mock.Mock())
        self.pipeline.match_intent.cache_clear()

    def _probe(self, utterance):
        msg = Message("intent.service.intent.get",
                      {"utterance": utterance, "lang": "en-US"},
                      {"session": {"session_id": "default"}})
        return self.pipeline.match_high([utterance], "en-US", msg)

    def test_spec_keyword_registration_matches(self):
        msg = Message(SpecMessage.INTENT_REGISTER_KEYWORD,
                      {"skill_id": "a.skill", "intent_name": "greet",
                       "lang": "en-US",
                       "required": [{"name": "kw", "samples": ["harnessa"]}],
                       "optional": [], "one_of": [], "excluded": []},
                      {"skill_id": "a.skill"})
        self.pipeline.handle_spec_register_keyword(msg)

        engine = self.pipeline.engines["en-US"]
        self.assertEqual(list(engine.domains), ["a.skill"],
                         "the vocab must land in the skill's domain")
        match = self._probe("harnessa")
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, "a.skill:greet")

    def test_legacy_vocab_before_intent_matches(self):
        keyword = "a_skillGreetKeyword"
        self.pipeline.handle_register_vocab(
            Message("register_vocab",
                    {"entity_value": "harnessa", "entity_type": keyword},
                    {"skill_id": "a.skill"}))
        intent = IntentBuilder("a.skill:greet").require(keyword)
        self.pipeline.handle_register_intent(
            Message("register_intent", intent.__dict__, {"skill_id": "a.skill"}))

        engine = self.pipeline.engines["en-US"]
        self.assertEqual(list(engine.domains), ["a.skill"])
        match = self._probe("harnessa")
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, "a.skill:greet")

    def test_vocab_without_skill_id_still_routes_by_prefix(self):
        """The prefix fallback stays for emitters that send no skill_id."""
        keyword = "a_skillGreetKeyword"
        intent = IntentBuilder("a.skill:greet").require(keyword)
        self.pipeline.handle_register_intent(
            Message("register_intent", intent.__dict__, {"skill_id": "a.skill"}))
        self.pipeline.register_vocabulary("harnessa", keyword, None, None, "en-US")

        engine = self.pipeline.engines["en-US"]
        self.assertEqual(list(engine.domains), ["a.skill"])
        self.assertIsNotNone(self._probe("harnessa"))


class TestDomainVocabBeforeIntent(_VocabBeforeIntentMixin, TestCase):
    pipeline_class = DomainAdaptPipeline


class TestHierarchicalVocabBeforeIntent(_VocabBeforeIntentMixin, TestCase):
    pipeline_class = HierarchicalAdaptPipeline
