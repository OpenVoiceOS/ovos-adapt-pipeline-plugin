# Copyright 2020 Mycroft AI Inc.
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
"""An intent parsing service using the Adapt parser."""
from functools import lru_cache
from threading import Lock
from typing import List, Optional, Iterable, Union, Dict

from langcodes import closest_match
from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
from ovos_bus_client.session import SessionManager
from ovos_bus_client.util import get_message_lang
from ovos_config.config import Configuration
from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch, ConfidenceMatcherPipeline
from ovos_utils import flatten_list
from ovos_utils.fakebus import FakeBus
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.log import LOG
from ovos_workshop.intents import open_intent_envelope

from ovos_adapt.engine import IntentDeterminationEngine


def _entity_skill_id(skill_id):
    """Helper converting a skill id to the format used in entities.

    Arguments:
        skill_id (str): skill identifier

    Returns:
        (str) skill id on the format used by skill entities
    """
    skill_id = skill_id[:-1]
    skill_id = skill_id.replace('.', '_')
    skill_id = skill_id.replace('-', '_')
    return skill_id


class AdaptPipeline(ConfidenceMatcherPipeline):
    """Intent service wrapping the Adapt intent Parser."""

    def __init__(self, bus: Optional[Union[MessageBusClient, FakeBus]] = None,
                 config: Optional[Dict] = None):
        core_config = Configuration()
        config = config or core_config.get("context", {})  # legacy mycroft-core path
        super().__init__(bus, config)
        self.lang = standardize_lang_tag(core_config.get("lang", "en-US"))
        langs = core_config.get('secondary_langs') or []
        if self.lang not in langs:
            langs.append(self.lang)
        langs = [standardize_lang_tag(l) for l in langs]
        self.engines = {lang: IntentDeterminationEngine()
                        for lang in langs}

        self.lock = Lock()
        self.registered_vocab = []
        self.max_words = 50  # if an utterance contains more words than this, don't attempt to match

        # TODO sanitize config option
        self.conf_high = self.config.get("conf_high") or 0.65
        self.conf_med = self.config.get("conf_med") or 0.45
        self.conf_low = self.config.get("conf_low") or 0.25

        self.bus.on('register_vocab', self.handle_register_vocab)
        self.bus.on('register_intent', self.handle_register_intent)
        self.bus.on('detach_intent', self.handle_detach_intent)
        self.bus.on('detach_skill', self.handle_detach_skill)

        self.bus.on('intent.service.adapt.get', self.handle_get_adapt)
        self.bus.on('intent.service.adapt.manifest.get', self.handle_adapt_manifest)
        self.bus.on('intent.service.adapt.vocab.manifest.get', self.handle_vocab_manifest)

    def update_context(self, intent):
        """Updates context with keyword from the intent.

        NOTE: This method currently won't handle one_of intent keywords
              since it's not using quite the same format as other intent
              keywords. This is under investigation in adapt, PR pending.

        Args:
            intent: Intent to scan for keywords
        """
        LOG.warning("update_context has been deprecated, use Session.context.update_context instead")
        sess = SessionManager.get()
        ents = [tag['entities'][0] for tag in intent['__tags__'] if 'entities' in tag]
        sess.context.update_context(ents)

    def match_high(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]:
        """Intent matcher for high confidence.

        Args:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
        """
        match = self.match_intent(tuple(utterances), lang, message.serialize())
        if match and match.intent_data.get("confidence", 0.0) >= self.conf_high:
            return match
        return None

    def match_medium(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]:
        """Intent matcher for medium confidence.

        Args:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
        """
        match = self.match_intent(tuple(utterances), lang, message.serialize())
        if match and match.intent_data.get("confidence", 0.0) >= self.conf_med:
            return match
        return None

    def match_low(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]:
        """Intent matcher for low confidence.

        Args:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
        """
        match = self.match_intent(tuple(utterances), lang, message.serialize())
        if match and match.intent_data.get("confidence", 0.0) >= self.conf_low:
            return match
        return None

    @lru_cache(maxsize=3)  # NOTE - message is a string because of this
    def match_intent(self, utterances: Iterable[str],
                     lang: Optional[str] = None,
                     message: Optional[str] = None):
        """Run the Adapt engine to search for an matching intent.

        Args:
            utterances (iterable): utterances for consideration in intent 
                    matching. As a practical matter, a single utterance will 
                    be passed in most cases. But there are instances, such as
                    streaming STT that could pass multiple. Each utterance is 
                    represented as a tuple containing the raw, normalized, and
                    possibly other variations of the utterance.
            limit (float): confidence threshold for intent matching
            lang (str): language to use for intent matching
            message (Message): message to use for context

        Returns:
            Intent structure, or None if no match was found.
        """

        if message:
            message = Message.deserialize(message)
        sess = SessionManager.get(message)

        # we call flatten in case someone is sending the old style list of tuples
        utterances = flatten_list(utterances)

        utterances = [u for u in utterances if len(u.split()) < self.max_words]
        if not utterances:
            LOG.error(f"utterance exceeds max size of {self.max_words} words, skipping adapt match")
            return None

        lang = self._get_closest_lang(lang)
        if lang is None:  # no intents registered for this lang
            return None

        best_intent = {}

        def take_best(intent, utt):
            nonlocal best_intent
            best = best_intent.get('confidence', 0.0) if best_intent else 0.0
            conf = intent.get('confidence', 0.0)
            skill = intent['intent_type'].split(":")[0]
            if best < conf and intent["intent_type"] not in sess.blacklisted_intents \
                    and skill not in sess.blacklisted_skills:
                best_intent = intent
                # TODO - Shouldn't Adapt do this?
                best_intent['utterance'] = utt

        for utt in utterances:
            try:
                intents = [i for i in self.engines[lang].determine_intent(
                    utt, 100,
                    include_tags=True,
                    context_manager=sess.context)]
                if intents:
                    utt_best = max(
                        intents, key=lambda x: x.get('confidence', 0.0)
                    )
                    take_best(utt_best, utt)

            except Exception as err:
                LOG.exception(err)

        if best_intent:
            ents = [tag['entities'][0] for tag in best_intent['__tags__'] if 'entities' in tag]

            sess.context.update_context(ents)

            skill_id = best_intent['intent_type'].split(":")[0]
            ret = IntentHandlerMatch(
                match_type=best_intent['intent_type'],
                match_data=best_intent, skill_id=skill_id,
                utterance=best_intent['utterance']
            )
        else:
            ret = None
        return ret

    def _get_closest_lang(self, lang: str) -> Optional[str]:
        if self.engines:
            lang = standardize_lang_tag(lang)
            closest, score = closest_match(lang, list(self.engines.keys()))
            # https://langcodes-hickford.readthedocs.io/en/sphinx/index.html#distance-values
            # 0 -> These codes represent the same language, possibly after filling in values and normalizing.
            # 1- 3 -> These codes indicate a minor regional difference.
            # 4 - 10 -> These codes indicate a significant but unproblematic regional difference.
            if score < 10:
                return closest
        return None

    def register_vocabulary(self, entity_value: str, entity_type: str,
                            alias_of: str, regex_str: str, lang: str):
        """Register skill vocabulary as adapt entity.

        This will handle both regex registration and registration of normal
        keywords. if the "regex_str" argument is set all other arguments will
        be ignored.

        Argument:
            entity_value: the natural langauge word
            entity_type: the type/tag of an entity instance
            alias_of: entity this is an alternative for
        """
        lang = standardize_lang_tag(lang)
        if lang in self.engines:
            with self.lock:
                if regex_str:
                    self.engines[lang].register_regex_entity(regex_str)
                else:
                    self.engines[lang].register_entity(
                        entity_value, entity_type, alias_of=alias_of)

    def register_intent(self, intent):
        """Register new intent with adapt engine.

        Args:
            intent (IntentParser): IntentParser to register
        """
        for lang in self.engines:
            with self.lock:
                self.engines[lang].register_intent_parser(intent)

    def detach_skill(self, skill_id):
        """Remove all intents for skill.

        Args:
            skill_id (str): skill to process
        """
        with self.lock:
            for lang in self.engines:
                skill_parsers = [
                    p.name for p in self.engines[lang].intent_parsers if
                    p.name.startswith(skill_id)
                ]
                self.engines[lang].drop_intent_parser(skill_parsers)
            self._detach_skill_keywords(skill_id)
            self._detach_skill_regexes(skill_id)

    def _detach_skill_keywords(self, skill_id):
        """Detach all keywords registered with a particular skill.

        Arguments:
            skill_id (str): skill identifier
        """
        skill_id = _entity_skill_id(skill_id)

        def match_skill_entities(data):
            return data and data[1].startswith(skill_id)

        for lang in self.engines:
            self.engines[lang].drop_entity(match_func=match_skill_entities)

    def _detach_skill_regexes(self, skill_id):
        """Detach all regexes registered with a particular skill.

        Arguments:
            skill_id (str): skill identifier
        """
        skill_id = _entity_skill_id(skill_id)

        def match_skill_regexes(regexp):
            return any([r.startswith(skill_id)
                        for r in regexp.groupindex.keys()])

        for lang in self.engines:
            self.engines[lang].drop_regex_entity(match_func=match_skill_regexes)

    def detach_intent(self, intent_name):
        """Detatch a single intent

        Args:
            intent_name (str): Identifier for intent to remove.
        """
        for lang in self.engines:
            new_parsers = [
                p for p in self.engines[lang].intent_parsers if p.name != intent_name
            ]
            self.engines[lang].intent_parsers = new_parsers

    def shutdown(self):
        for lang in self.engines:
            parsers = self.engines[lang].intent_parsers
            self.engines[lang].drop_intent_parser(parsers)

    @property
    def registered_intents(self):
        lang = get_message_lang()
        return [parser.__dict__ for parser in self.engines[lang].intent_parsers]

    def handle_register_vocab(self, message):
        """Register adapt vocabulary.

        Args:
            message (Message): message containing vocab info
        """
        entity_value = message.data.get('entity_value')
        entity_type = message.data.get('entity_type')
        regex_str = message.data.get('regex')
        alias_of = message.data.get('alias_of')
        lang = get_message_lang(message)
        self.register_vocabulary(entity_value, entity_type,
                                 alias_of, regex_str, lang)
        self.registered_vocab.append(message.data)

    def handle_register_intent(self, message):
        """Register adapt intent.

        Args:
            message (Message): message containing intent info
        """
        intent = open_intent_envelope(message)
        self.register_intent(intent)

    def handle_detach_intent(self, message):
        """Remover adapt intent.

        Args:
            message (Message): message containing intent info
        """
        intent_name = message.data.get('intent_name')
        self.detach_intent(intent_name)

    def handle_detach_skill(self, message):
        """Remove all intents registered for a specific skill.

        Args:
            message (Message): message containing intent info
        """
        skill_id = message.data.get('skill_id')
        self.detach_skill(skill_id)

    def handle_get_adapt(self, message: Message):
        """handler getting the adapt response for an utterance.

        Args:
            message (Message): message containing utterance
        """
        utterance = message.data["utterance"]
        lang = get_message_lang(message)
        intent = self.match_intent((utterance,), lang, message.serialize())
        intent_data = intent.match_data if intent else None
        self.bus.emit(message.reply("intent.service.adapt.reply",
                                    {"intent": intent_data}))

    def handle_adapt_manifest(self, message):
        """Send adapt intent manifest to caller.

        Argument:
            message: query message to reply to.
        """
        self.bus.emit(message.reply("intent.service.adapt.manifest",
                                    {"intents": self.registered_intents}))

    def handle_vocab_manifest(self, message):
        """Send adapt vocabulary manifest to caller.

        Argument:
            message: query message to reply to.
        """
        self.bus.emit(message.reply("intent.service.adapt.vocab.manifest",
                                    {"vocab": self.registered_vocab}))
