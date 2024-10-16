# Copyright 2018 Mycroft AI Inc.
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

import unittest
from ovos_adapt.engine import DomainIntentDeterminationEngine
from ovos_adapt.intent import IntentBuilder
from ovos_adapt.entity_tagger import EntityTagger
from ovos_adapt.tools.text.tokenizer import EnglishTokenizer
from ovos_adapt.tools.text.trie import Trie

__author__ = 'seanfitz'


class TokenizerTests(unittest.TestCase):
    """All tests related to the DomainIntentDeterminationEngine."""

    def setUp(self):
        """Setting up testing env."""
        self.engine = DomainIntentDeterminationEngine()

    def test_tokenizer_property(self):
        """Test the tokenizer property is working."""
        self.assertIsInstance(self.engine.tokenizer, EnglishTokenizer)


class TrieTests(unittest.TestCase):
    """All tests related to the DomainIntentDeterminationEngine."""

    def setUp(self):
        """Setting up testing env."""
        self.engine = DomainIntentDeterminationEngine()

    def test_trie_property(self):
        """Test the trie property is working."""
        self.assertIsInstance(self.engine.trie, Trie)


class TaggerTests(unittest.TestCase):
    """All tests related to the DomainIntentDeterminationEngine."""

    def setUp(self):
        """Setting up testing env."""
        self.engine = DomainIntentDeterminationEngine()

    def test_tagger_property(self):
        """Test the tagger property is working."""
        self.assertIsInstance(self.engine.tagger, EntityTagger)


class IntentParsersTests(unittest.TestCase):
    """All tests related to the DomainIntentDeterminationEngine."""

    def setUp(self):
        """Setting up testing env."""
        self.engine = DomainIntentDeterminationEngine()

    def test_intent_parsers_property(self):
        """Test the intent_parsers property is working."""
        self.assertEqual(self.engine.intent_parsers, [])


class RegexStringsTests(unittest.TestCase):
    """All tests related to the DomainIntentDeterminationEngine."""

    def setUp(self):
        """Setting up testing env."""
        self.engine = DomainIntentDeterminationEngine()

    def test__regex_strings_property(self):
        """Test the _regex_strings property is working."""
        self.assertEqual(self.engine._regex_strings, set())


class RegularExpressionsEntitiesTests(unittest.TestCase):
    """All tests related to the DomainIntentDeterminationEngine."""

    def setUp(self):
        """Setting up testing env."""
        self.engine = DomainIntentDeterminationEngine()

    def test_regular_expressions_entities_property(self):
        """Test the regular_expressions_entities property is working."""
        self.assertEqual(self.engine.regular_expressions_entities, [])


class RegisterIntentParserTests(unittest.TestCase):
    """All tests related to the DomainIntentDeterminationEngine."""

    def setUp(self):
        """Setting up testing env."""
        self.engine = DomainIntentDeterminationEngine()

    def test_register_intent_parser(self):
        """Test to make sure that intent parser is working with correct data."""
        parser = IntentBuilder("Intent").build()
        self.engine.register_intent_parser(parser)
        self.assertEqual(len(self.engine.intent_parsers), 1)

    def test_register_intent_parser_defult_is_empty(self):
        """Test to make sure that the intent parser is empty when first created."""
        assert len(self.engine.intent_parsers) == 0

    def test_register_intent_parser_throws_error_if_not_intent_parsers(self):
        """
        Test register_intent_parser throws error if IntentBuilder object is not passed in.
        This should throw a ValueError.
        """
        with self.assertRaises(ValueError):
            self.engine.register_intent_parser("NOTAPARSER")


class RegisterRegexEntityTests(unittest.TestCase):
    """All tests related to the DomainIntentDeterminationEngine."""

    def setUp(self):
        """Setting up testing env."""
        self.engine = DomainIntentDeterminationEngine()

    def test_register_regex_entity(self):
        """Test to make sure a regex entity can be registered."""
        self.engine.register_regex_entity(".*")
        self.assertEqual(len(self.engine._regex_strings), 1)
        self.assertEqual(len(self.engine.regular_expressions_entities), 1)

    def test_register_regex_entity_default_is_empty(self):
        """Test to make sure that regex entity is empty by default."""
        self.assertEqual(len(self.engine._regex_strings), 0)
        self.assertEqual(len(self.engine.regular_expressions_entities), 0)


class SelectBestIntentTests(unittest.TestCase):
    """All tests related to the DomainIntentDeterminationEngine."""

    def setUp(self):
        """Setting up testing env."""
        self.engine = DomainIntentDeterminationEngine()

    def test_select_best_intent(self):
        """
        Test to make sure that best intent is being returned.
        This test is to make sure that best intent works identicly to its counter part
        in the IntentEngine.
        """
        parser1 = IntentBuilder("Parser1").require("Entity1").build()
        self.engine.register_intent_parser(parser1)
        self.engine.register_entity("tree", "Entity1")

        utterance = "go to the tree house"
        intent = next(self.engine.determine_intent(utterance))
        assert intent
        self.assertEqual(intent['intent_type'], 'Parser1')

        parser2 = IntentBuilder("Parser2").require("Entity1").require("Entity2").build()
        self.engine.register_intent_parser(parser2)
        self.engine.register_entity("house", "Entity2")
        intent = next(self.engine.determine_intent(utterance))
        assert intent
        self.assertEqual(intent['intent_type'], 'Parser2')

    def test_select_best_intent_with_domain(self):
        """Test to make sure that best intent is working with domains."""
        self.engine.register_domain('Domain1')
        self.engine.register_domain('Domain2')

        # Creating first intent domain
        parser1 = IntentBuilder("Parser1").require("Entity1").build()
        self.engine.register_intent_parser(parser1, domain='Domain1')
        self.engine.register_entity("tree", "Entity1", domain='Domain1')

        # Creating second intent domain
        parser2 = IntentBuilder("Parser1").require("Entity2").build()
        self.engine.register_intent_parser(parser2, domain="Domain2")
        self.engine.register_entity("house", "Entity2", domain="Domain2")

        utterance = "Entity1 Entity2 go to the tree house"
        intents = self.engine.determine_intent(utterance, 2)

        intent = next(intents)
        assert intent
        self.assertEqual(intent['intent_type'], 'Parser1')

        intent = next(intents)
        assert intent
        self.assertEqual(intent['intent_type'], 'Parser1')

    def test_select_best_intent_enuse_enitities_dont_register_in_multiple_domains(self):
        """Test to make sure that 1 entity does not end up in multiple domains."""
        self.engine.register_domain('Domain1')
        self.engine.register_domain('Domain2')

        # Creating first intent domain
        parser1 = IntentBuilder("Parser1").require("Entity1").build()
        self.engine.register_intent_parser(parser1, domain='Domain1')
        self.engine.register_entity("tree", "Entity1", domain='Domain1')

        # Creating second intent domain
        parser2 = IntentBuilder("Parser2").require("Entity2").build()
        self.engine.register_intent_parser(parser2, domain="Domain2")
        self.engine.register_entity("house", "Entity2", domain="Domain2")

        utterance = "go to the house"
        intents = self.engine.determine_intent(utterance, 1)
        for intent in intents:
            self.assertNotEqual(intent['intent_type'], 'Parser1')

        utterance = "go to the tree"
        intents = self.engine.determine_intent(utterance, 1)
        for intent in intents:
            self.assertNotEqual(intent['intent_type'], 'Parser2')

    def test_drop_intent_from_domain(self):
        """Test that intent is dropped from the correct domain."""
        self.engine.register_domain('Domain1')
        self.engine.register_domain('Domain2')

        # Creating first intent domain
        parser1 = IntentBuilder("Parser1").require("Entity1").build()
        self.engine.register_intent_parser(parser1, domain='Domain1')
        self.engine.register_entity("tree", "Entity1", domain='Domain1')

        # Creating second intent domain
        parser2 = IntentBuilder("Parser2").require("Entity2").build()
        self.engine.register_intent_parser(parser2, domain="Domain2")
        self.engine.register_entity("house", "Entity2", domain="Domain2")

        self.engine.drop_intent_parser(domain="Domain2",
                                       parser_names=['Parser2'])
        self.assertEqual(len(self.engine.domains['Domain2'].intent_parsers), 0)

    def test_drop_entity_from_domain(self):
        """Test that entity is dropped from domain."""
        self.engine.register_domain('Domain1')
        self.engine.register_domain('Domain2')

        # Creating first intent domain
        parser1 = IntentBuilder("Parser1").require("Entity1").build()
        self.engine.register_intent_parser(parser1, domain='Domain1')
        self.engine.register_entity("tree", "Entity1", domain='Domain1')

        # Creating second intent domain
        parser2 = IntentBuilder("Parser2").require("Entity2").build()
        self.engine.register_intent_parser(parser2, domain="Domain2")
        self.engine.register_entity("house", "Entity2", domain="Domain2")

        self.assertTrue(self.engine.drop_entity(domain="Domain2",
                                                entity_type='Entity2'))

    def testDropRegexEntity(self):
        self.engine.register_domain("Domain1")
        self.engine.register_domain("Domain2")

        self.engine.register_regex_entity(r"the dog (?P<Dog>.*)",
                                          "Domain1")
        self.engine.register_regex_entity(r"the cat (?P<Cat>.*)",
                                          "Domain2")
        self.assertTrue(self.engine.drop_regex_entity(domain='Domain2',
                                                      entity_type='Cat'))
        self.assertFalse(self.engine.drop_regex_entity(domain='Domain1',
                                                       entity_type='Cat'))
