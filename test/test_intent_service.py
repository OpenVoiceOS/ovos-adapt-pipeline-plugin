# Copyright 2017 Mycroft AI Inc.
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
from unittest import TestCase, mock

from ovos_bus_client.message import Message
from ovos_workshop.intents import IntentBuilder, Intent as AdaptIntent

from ovos_adapt.opm import AdaptPipeline


def create_vocab_msg(keyword, value):
    """Create a message for registering an adapt keyword."""
    return Message('register_vocab',
                   {'entity_value': value, 'entity_type': keyword})


def get_last_message(bus):
    """Get last sent message on mock bus."""
    last = bus.emit.call_args
    print(666, last)
    return last[0][0]


class TestPipeline(TestCase):
    def setUp(self):
        self.adapt_pipeline = AdaptPipeline(mock.Mock())
        self.setup_simple_adapt_intent()

    def setup_simple_adapt_intent(self,
                                  msg=create_vocab_msg('testKeyword', 'test')):
        self.adapt_pipeline.handle_register_vocab(msg)

        intent = IntentBuilder('skill:testIntent').require('testKeyword')
        msg = Message('register_intent', intent.__dict__)
        self.adapt_pipeline.handle_register_intent(msg)

    def test_get_adapt_intent(self):
        # Check that the intent is returned
        msg = Message('intent.service.adapt.get',
                      data={'utterance': 'test'})
        self.adapt_pipeline.handle_get_adapt(msg)

        reply = get_last_message(self.adapt_pipeline.bus)
        self.assertEqual(reply.data['intent']['intent_type'],
                         'skill:testIntent')

    def test_get_adapt_intent_no_match(self):
        """Check that if the intent doesn't match at all None is returned."""
        # Check that no intent is matched
        msg = Message('intent.service.adapt.get',
                      data={'utterance': 'five'})
        self.adapt_pipeline.handle_get_adapt(msg)
        reply = get_last_message(self.adapt_pipeline.bus)
        self.assertEqual(reply.data['intent'], None)

    def test_get_adapt_intent_manifest(self):
        """Make sure the manifest returns a list of Intent Parser objects."""
        msg = Message('intent.service.adapt.manifest.get')
        self.adapt_pipeline.handle_adapt_manifest(msg)
        reply = get_last_message(self.adapt_pipeline.bus)
        self.assertEqual(reply.data['intents'][0]['name'],
                         'skill:testIntent')

    def test_get_adapt_vocab_manifest(self):
        msg = Message('intent.service.adapt.vocab.manifest.get')
        self.adapt_pipeline.handle_vocab_manifest(msg)
        reply = get_last_message(self.adapt_pipeline.bus)
        value = reply.data['vocab'][0]['entity_value']
        keyword = reply.data['vocab'][0]['entity_type']
        self.assertEqual(keyword, 'testKeyword')
        self.assertEqual(value, 'test')

    def test_get_no_match_after_detach(self):
        """Check that a removed intent doesn't match."""
        # Check that no intent is matched
        msg = Message('detach_intent',
                      data={'intent_name': 'skill:testIntent'})
        self.adapt_pipeline.handle_detach_intent(msg)
        msg = Message('intent.service.adapt.get', data={'utterance': 'test'})
        self.adapt_pipeline.handle_get_adapt(msg)
        reply = get_last_message(self.adapt_pipeline.bus)
        self.assertEqual(reply.data['intent'], None)

    def test_get_no_match_after_detach_skill(self):
        """Check that a removed skill's intent doesn't match."""
        # Check that no intent is matched
        msg = Message('detach_intent',
                      data={'skill_id': 'skill'})
        self.adapt_pipeline.handle_detach_skill(msg)
        msg = Message('intent.service.adapt.get', data={'utterance': 'test'})
        self.adapt_pipeline.handle_get_adapt(msg)
        reply = get_last_message(self.adapt_pipeline.bus)
        self.assertEqual(reply.data['intent'], None)


class TestAdaptIntent(TestCase):
    """Test the AdaptIntent wrapper."""

    def test_named_intent(self):
        intent = AdaptIntent("CallEaglesIntent")
        self.assertEqual(intent.name, "CallEaglesIntent")

    def test_unnamed_intent(self):
        intent = AdaptIntent()
        self.assertEqual(intent.name, "")
