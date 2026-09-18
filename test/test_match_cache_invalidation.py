"""The match cache must not outlive the registrations it was built from.

``AdaptPipeline.match_intent`` caches by (utterances, lang, serialized
message) so the high, medium and low tiers share one engine run per
round. A registration change makes every cached entry stale: a detached
skill kept matching ``intent.service.intent.get`` on a live core after
every manifest had dropped it.
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_spec_tools import SpecMessage

from ovos_adapt.intent import IntentBuilder

from ovos_adapt.opm import AdaptPipeline, DomainAdaptPipeline, HierarchicalAdaptPipeline


class _CacheInvalidationMixin:
    pipeline_class = AdaptPipeline

    def setUp(self):
        self.pipeline = self.pipeline_class(mock.Mock())
        self.pipeline.match_intent.cache_clear()

    def _register(self, skill_id, intent_name, sample):
        # the legacy path, intent first so the domain classes route the
        # vocab to the intent's domain
        keyword = f"{skill_id.replace('.', '_')}{intent_name}Keyword"
        intent = IntentBuilder(f"{skill_id}:{intent_name}").require(keyword)
        self.pipeline.handle_register_intent(
            Message("register_intent", intent.__dict__, {"skill_id": skill_id}))
        self.pipeline.handle_register_vocab(
            Message("register_vocab",
                    {"entity_value": sample, "entity_type": keyword},
                    {"skill_id": skill_id}))

    def _probe(self, utterance):
        # the same message every time, as a repeated bus probe sends it
        msg = Message("intent.service.intent.get",
                      {"utterance": utterance, "lang": "en-US"},
                      {"session": {"session_id": "default"}})
        return self.pipeline.match_high([utterance], "en-US", msg)

    def test_detach_skill_drops_the_cached_match(self):
        self._register("a.skill", "greet", "harnessa")
        first = self._probe("harnessa")
        self.assertIsNotNone(first)
        self.assertEqual(first.match_type, "a.skill:greet")

        self.pipeline.detach_skill("a.skill")

        self.assertIsNone(self._probe("harnessa"),
                          "a detached skill must not match from the cache")

    def test_detach_intent_drops_the_cached_match(self):
        self._register("a.skill", "greet", "harnessa")
        self.assertIsNotNone(self._probe("harnessa"))

        self.pipeline.detach_intent("a.skill:greet")

        self.assertIsNone(self._probe("harnessa"))

    def test_spec_deregister_skill_drops_the_cached_match(self):
        self._register("a.skill", "greet", "harnessa")
        self.assertIsNotNone(self._probe("harnessa"))

        self.pipeline.handle_spec_deregister_skill(
            Message(SpecMessage.SKILL_DEREGISTER, {"skill_id": "a.skill"},
                    {"skill_id": "a.skill"}))

        self.assertIsNone(self._probe("harnessa"))

    def test_register_after_a_miss_drops_the_cached_miss(self):
        self.assertIsNone(self._probe("harnessa"))

        self._register("a.skill", "greet", "harnessa")

        match = self._probe("harnessa")
        self.assertIsNotNone(match, "a cached miss must not hide a new intent")
        self.assertEqual(match.match_type, "a.skill:greet")

    def test_shutdown_drops_the_cached_match(self):
        self._register("a.skill", "greet", "harnessa")
        self.assertIsNotNone(self._probe("harnessa"))

        self.pipeline.shutdown()

        self.assertIsNone(self._probe("harnessa"))


class TestFlatPipelineCacheInvalidation(_CacheInvalidationMixin, TestCase):
    pipeline_class = AdaptPipeline


class TestDomainPipelineCacheInvalidation(_CacheInvalidationMixin, TestCase):
    pipeline_class = DomainAdaptPipeline


class TestHierarchicalPipelineCacheInvalidation(_CacheInvalidationMixin, TestCase):
    pipeline_class = HierarchicalAdaptPipeline
