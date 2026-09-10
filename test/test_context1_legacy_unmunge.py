# Copyright 2026 OpenVoiceOS
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
"""GH #66 regression: legacy-registered adapt intents mixing a vocab
``require()`` with a context-only ``require()`` were permanently
unmatchable when the skill wrote ``session.intent_context`` via the raw
``SessionManager.get(msg).set_intent_context(name, value, scope="shared")``
API (verified against ovos-bus-client dev ``session.py``: shared scope
stores the bare, un-munged ``key``) -- writing the PLAIN vocabulary name
with a real value, while ``_live_context_value`` only ever probed the
munged name derived from the keyword's ``entity_type``. This is
days-in-history's ``prev_dialog`` gate. Fixed by additionally probing the
un-munged plain name (private- then shared-scope) alongside the already
-munged one.

Naptime's ``sleeping_state`` gate is NOT this bug: ``handle_add_context``
in released ovos-core (verified 2.6.3a1, also present on dev
``service.py``) stores ``{"value": word or context}`` -- so
``OVOSSkill.set_context(context, word='')``'s default empty word yields a
NON-empty stored value (the munged context token itself), and the munged
key already matched the keyword's munged ``entity_type`` on unmodified
dev. An earlier version of this fix additionally accepted empty-string
context values, reasoning (wrongly) that naptime's flow produced one --
that premise didn't survive a live check against the real
``handle_add_context`` producer, so it is dropped; the empty-value
rejection is restored to dev's behaviour. The naptime deployment break
described in the issue is release-vintage: released
``ovos-adapt-parser`` 1.6.2a1 predates the §7 injection machinery
entirely, fixed simply by shipping this repo's dev (which already has §7)
together with a core release carrying the word-or-context coercion.
"""
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session

from ovos_adapt.intent import IntentBuilder
from ovos_adapt.opm import AdaptPipeline


def _msg(sess, utterance):
    return Message("intent.service.adapt.get",
                   data={"utterance": utterance, "lang": "en-US"},
                   context={"session": sess.serialize()})


# -- naptime: GUARD, not a bug fix -- pins already-working dev behaviour --

NAPTIME_SKILL_ID = "ovos-skill-naptime.openvoiceos"
# to_alnum(NAPTIME_SKILL_ID), mirroring workshop's munge_intent_parser /
# OVOSSkill.alphanumeric_skill_id transform: non-alphanumeric -> '_'.
NAPTIME_MUNGE_PREFIX = "ovos_skill_naptime_openvoiceos"
NAPTIME_KEYWORD = "sleeping_state"
NAPTIME_MUNGED_ENTITY_TYPE = NAPTIME_MUNGE_PREFIX + NAPTIME_KEYWORD
NAPTIME_INTENT_NAME = f"{NAPTIME_SKILL_ID}:WakeUpIntent"


def _set_context_via_real_producer(sess: Session, skill_id: str, context: str,
                                   word: str = ""):
    """Reproduce ovos-core's real ``handle_add_context`` (verified against
    both the released 2.6.3a1 wheel and dev ``service.py``): the stored
    entry is ``{"value": word or context}`` -- so the caller's default
    empty ``word`` still yields a NON-empty value, the munged context
    token itself. The key is munged exactly as
    ``_AdaptIntentApi.to_alnum``/``OVOSSkill.alphanumeric_skill_id`` do,
    matching what ``OVOSSkill.set_context`` sends over ``add_context``."""
    prefix = ''.join(c if c.isalnum() else '_' for c in str(skill_id))
    munged_context = prefix + context
    sess.intent_context = sess.intent_context or {}
    sess.intent_context[munged_context] = {"value": word or munged_context}


class TestNaptimeMungedContextGuard(TestCase):
    """GUARD (not a bug fix): pins the naptime two-turn sleep/wake flow that
    already works correctly on unmodified dev, using ovos-core's real
    ``handle_add_context`` entry shape. This is NOT the days-in-history bug
    this PR fixes -- it exists so a future change to
    ``_live_context_value``'s value-acceptance rules cannot silently break
    this already-working case without a red test."""

    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())
        self.pipeline.register_vocabulary(
            "wake up", NAPTIME_MUNGE_PREFIX + "wake_up", None, None, "en-US")
        intent = IntentBuilder(NAPTIME_INTENT_NAME).require(
            NAPTIME_MUNGE_PREFIX + "wake_up").require(
            NAPTIME_MUNGED_ENTITY_TYPE).build()
        self.pipeline.register_intent(intent)

    def _match(self, utterance, sess):
        self.pipeline.handle_get_adapt(_msg(sess, utterance))
        return self.pipeline.bus.emit.call_args[0][0].data["intent"]

    def test_context_absent_no_match(self):
        """Negative control: awake (no context entry at all) never matches."""
        self.assertIsNone(self._match("wake up", Session("sess")))

    def test_two_turn_sleep_then_wake_flow(self):
        """Turn 1 (simulated): naptime calls set_context("sleeping_state")
        with the default empty word; ovos-core's real handle_add_context
        stores a non-empty value (word-or-context coercion). Turn 2: "wake
        up" must match WakeUpIntent -- this already works on dev."""
        sess = Session("sess")
        _set_context_via_real_producer(sess, NAPTIME_SKILL_ID, NAPTIME_KEYWORD,
                                       word="")

        intent = self._match("wake up", sess)

        self.assertIsNotNone(intent)
        self.assertEqual(intent["intent_type"], NAPTIME_INTENT_NAME)


# -- shape (b): days-in-history -- plain key, real value ------------------

DIH_SKILL_ID = "ovos-skill-days-in-history.openvoiceos"
DIH_MUNGE_PREFIX = "ovos_skill_days_in_history_openvoiceos"
DIH_KEYWORD = "prev_dialog"
DIH_MUNGED_ENTITY_TYPE = DIH_MUNGE_PREFIX + DIH_KEYWORD
DIH_INTENT_NAME = f"{DIH_SKILL_ID}:TellMeMoreIntent"


class TestDaysInHistoryPlainKeyContext(TestCase):
    """SECONDARY case: shape (b) from the issue -- the raw
    ``SessionManager.set_intent_context`` call path, real ovos-bus-client
    API (not hand-rolled), writing the PLAIN (un-munged) key."""

    def setUp(self):
        self.pipeline = AdaptPipeline(mock.Mock())
        self.pipeline.register_vocabulary(
            "tell me more", DIH_MUNGE_PREFIX + "trigger", None, None, "en-US")
        intent = IntentBuilder(DIH_INTENT_NAME).require(
            DIH_MUNGE_PREFIX + "trigger").require(
            DIH_MUNGED_ENTITY_TYPE).build()
        self.pipeline.register_intent(intent)

    def _match(self, utterance, sess):
        self.pipeline.handle_get_adapt(_msg(sess, utterance))
        return self.pipeline.bus.emit.call_args[0][0].data["intent"]

    def test_context_absent_no_match(self):
        """Negative control: no prior dialog, no context entry -> no match."""
        self.assertIsNone(self._match("tell me more", Session("sess")))

    def test_plain_key_shared_scope_matches(self):
        """Real ovos_bus_client.session.Session.set_intent_context, exactly
        as days-in-history's __init__.py calls it: plain (un-munged) key,
        shared scope, real dialog-topic value."""
        sess = Session("sess")
        sess.set_intent_context(DIH_KEYWORD, "some previous topic",
                                scope="shared")

        intent = self._match("tell me more", sess)

        self.assertIsNotNone(intent)
        self.assertEqual(intent["intent_type"], DIH_INTENT_NAME)

    def test_context_candidate_injected_for_plain_key_entry(self):
        """Unit-level: the plain-key entry must resolve via the un-munged
        fallback probe to a candidate carrying the MUNGED entity_type (so
        the matcher's vocabulary lookup for that keyword still hits)."""
        sess = Session("sess")
        sess.set_intent_context(DIH_KEYWORD, "some previous topic",
                                scope="shared")

        candidates = self.pipeline._context_candidate_entities(sess)

        matching = [c for c in candidates
                   if c["data"][0][1] == DIH_MUNGED_ENTITY_TYPE
                   and c["data"][0][0] == "some previous topic"]
        self.assertTrue(matching,
                        f"no candidate carried entity_type="
                        f"{DIH_MUNGED_ENTITY_TYPE!r}; got {candidates!r} "
                        f"(bug: only the munged name was probed, never "
                        f"the plain key the raw session API wrote)")


# -- helper unit tests ------------------------------------------------------

class TestUnmungeKeywordNameHelper(TestCase):
    def test_entity_type_without_prefix_unchanged(self):
        """A foreign/manual registration whose entity_type doesn't carry the
        skill's munge prefix is returned verbatim."""
        self.assertEqual(
            AdaptPipeline._unmunge_keyword_name("person", DIH_SKILL_ID),
            "person")

    def test_stripping_to_empty_keeps_verbatim(self):
        """If entity_type equals the prefix exactly, stripping it would
        leave an empty lookup key -- keep the entity_type verbatim."""
        self.assertEqual(
            AdaptPipeline._unmunge_keyword_name(DIH_MUNGE_PREFIX, DIH_SKILL_ID),
            DIH_MUNGE_PREFIX)

    def test_over_strip_on_prefix_matching_foreign_registration_avoided(self):
        """A foreign entity_type that happens to start with a DIFFERENT
        skill's munged skill_id must not be mis-stripped down to a
        meaningless remainder."""
        self.assertEqual(
            AdaptPipeline._unmunge_keyword_name("test_skilling", "test.skill"),
            "ing")
        # Guard against the specific over-strip regression called out in
        # review: this remainder is non-empty so the fallback probe WILL
        # fire for it, but it never wins over the munged probe (which is
        # tried first) unless a producer actually wrote that key -- it does
        # not silently collide with or replace the primary (munged) lookup.

    def test_dotted_dashed_skill_id_prefix_derivation(self):
        """The munge prefix mirrors workshop's to_alnum: non-alphanumeric
        chars (dots, dashes) in skill_id become underscores."""
        self.assertEqual(
            AdaptPipeline._unmunge_keyword_name(DIH_MUNGED_ENTITY_TYPE,
                                                DIH_SKILL_ID),
            DIH_KEYWORD)
