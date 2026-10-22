"""adapt's engine must accept Intents built outside adapt — e.g. the bare
ovos-spec-tools Intent that ovos-workshop re-exports via IntentBuilder — by
coercing them to an adapt Intent at registration. Skills registering over the
bus already get this via open_intent_envelope; this covers direct in-process
registration (library use / test harnesses)."""
import unittest

from ovos_adapt.engine import IntentDeterminationEngine
from ovos_adapt.intent import IntentBuilder as AdaptBuilder
from ovos_spec_tools.intent import IntentBuilder as SpecBuilder


class TestRegisterForeignIntent(unittest.TestCase):
    def test_spec_tools_intent_is_coerced(self):
        engine = IntentDeterminationEngine()
        foreign = SpecBuilder("LightIntent").require("LightKeyword").build()
        # the bare spec-tools Intent lacks adapt's matching API
        self.assertFalse(hasattr(foreign, "validate_with_tags"))
        engine.register_intent_parser(foreign)  # must not raise
        self.assertEqual(len(engine.intent_parsers), 1)
        # rebuilt as an adapt Intent — now matchable
        self.assertTrue(hasattr(engine.intent_parsers[0], "validate_with_tags"))

    def test_foreign_intent_matches(self):
        engine = IntentDeterminationEngine()
        engine.register_entity("light", "LightKeyword")
        engine.register_entity("on", "OnKeyword")
        foreign = (SpecBuilder("LightIntent")
                   .require("OnKeyword").require("LightKeyword").build())
        engine.register_intent_parser(foreign)
        intents = list(engine.determine_intent("turn on the light"))
        self.assertTrue(intents)
        self.assertEqual(intents[0].get("intent_type"), "LightIntent")

    def test_native_adapt_intent_passes_through_unchanged(self):
        engine = IntentDeterminationEngine()
        native = AdaptBuilder("NativeIntent").require("LightKeyword").build()
        engine.register_intent_parser(native)
        self.assertIs(engine.intent_parsers[0], native)

    def test_non_intent_still_rejected(self):
        engine = IntentDeterminationEngine()
        with self.assertRaises(ValueError):
            engine.register_intent_parser("NOTAPARSER")


if __name__ == "__main__":
    unittest.main()
