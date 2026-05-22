"""
Keyword-intent benchmark dataset for the Adapt engine.

Used to compare three engine topologies on identical vocabulary and intents:
the flat ``IntentDeterminationEngine``, the parallel
``DomainIntentDeterminationEngine``, and a two-stage hierarchical router.

Design
------
Intents are mostly **two-slot** — an ACTION keyword plus an OBJECT keyword —
so a single stray keyword does not trigger an intent on its own. OBJECT
vocabularies are domain-distinctive (``thermostat`` only ever appears in
*climate*, ``playlist`` only in *media*), which lets a domain classifier
route reliably. ACTION vocabularies are deliberately shared across domains
(``turn up`` is both a volume and a heating action), so disambiguation
depends on the object — the case that separates the engine topologies.

A handful of intents are genuinely single-trigger (``weather_query``,
``get_help``, ``navigate_to``) and stay one-slot.

Structure
---------
VOCAB       entity_type -> [entity_value, ...]   (ACTION_* and OBJ_* groups)
INTENTS     intent_name -> {"required": [...], "optional": [...]}
DOMAINS     domain_name -> [intent_name, ...]
TEST_CASES  [(utterance, expected_intent), ...]
NO_MATCH_UTTERANCES   [utterance, ...]   (should match nothing)
"""

# ── action vocabulary (shared across domains) ──────────────────────────────

VOCAB = {
    "ACTION_PLAY":   ["play", "put on", "queue"],
    "ACTION_STOP":   ["stop", "pause", "halt"],
    "ACTION_SKIP":   ["next", "skip"],
    "ACTION_RAISE":  ["turn up", "crank up", "raise", "increase"],
    "ACTION_LOWER":  ["turn down", "lower", "decrease"],
    "ACTION_ON":     ["turn on", "switch on", "enable"],
    "ACTION_OFF":    ["turn off", "switch off", "disable"],
    "ACTION_SET":    ["set", "create", "make", "schedule", "start"],
    "ACTION_CANCEL": ["cancel", "delete", "remove", "clear"],
    "ACTION_ASK":    ["what", "how", "tell me", "check", "give me"],
    "ACTION_SEND":   ["send", "write", "jot down", "leave", "draft"],
    "ACTION_GO":     ["navigate to", "take me to", "drive to",
                      "directions to", "get me to"],

    # ── object vocabulary (domain-distinctive) ─────────────────────────────
    "OBJ_AUDIO":     ["volume", "sound", "music", "song", "stereo"],
    "OBJ_MUSIC":     ["music", "song", "track", "playlist", "album",
                      "podcast", "tune"],
    "OBJ_LIGHT":     ["light", "lights", "lamp", "bulb", "lighting"],
    "OBJ_HVAC":      ["thermostat", "heating", "heater", "radiator",
                      "air conditioning", "temperature"],
    "OBJ_ROOM":      ["bedroom", "kitchen", "living room", "bathroom",
                      "hallway", "office", "garage"],
    "OBJ_TIMER":     ["timer", "countdown"],
    "OBJ_ALARM":     ["alarm"],
    "OBJ_WEATHER":   ["weather", "forecast", "rain", "umbrella",
                      "temperature", "snow"],
    "OBJ_REMINDER":  ["reminder", "remind me"],
    "OBJ_PHONE":     ["call", "phone", "dial", "ring"],
    "OBJ_MESSAGE":   ["message", "text", "email"],
    "OBJ_NOTE":      ["note", "memo"],
    "OBJ_SHOPPING":  ["shopping list", "groceries", "shopping"],
    "OBJ_TIME":      ["time", "clock"],
    "OBJ_DATE":      ["date", "today", "what day"],
    "OBJ_SEARCH":    ["search", "look up", "google"],
    "OBJ_HELP":      ["help", "commands"],
    "OBJ_HALT":      ["stop", "cancel", "abort", "never mind"],
}

# ── intent definitions ─────────────────────────────────────────────────────

INTENTS = {
    # media
    "play_music":    {"required": ["ACTION_PLAY", "OBJ_MUSIC"], "optional": []},
    "pause_music":   {"required": ["ACTION_STOP", "OBJ_MUSIC"], "optional": []},
    "next_track":    {"required": ["ACTION_SKIP"], "optional": ["OBJ_MUSIC"]},
    "volume_up":     {"required": ["ACTION_RAISE", "OBJ_AUDIO"], "optional": []},
    "volume_down":   {"required": ["ACTION_LOWER", "OBJ_AUDIO"], "optional": []},
    # lights
    "lights_on":     {"required": ["ACTION_ON", "OBJ_LIGHT"],
                      "optional": ["OBJ_ROOM"]},
    "lights_off":    {"required": ["ACTION_OFF", "OBJ_LIGHT"],
                      "optional": ["OBJ_ROOM"]},
    # climate
    "heating_up":    {"required": ["ACTION_RAISE", "OBJ_HVAC"],
                      "optional": ["OBJ_ROOM"]},
    "heating_down":  {"required": ["ACTION_LOWER", "OBJ_HVAC"],
                      "optional": ["OBJ_ROOM"]},
    "check_hvac":    {"required": ["ACTION_ASK", "OBJ_HVAC"], "optional": []},
    # timers & alarms
    "set_timer":     {"required": ["ACTION_SET", "OBJ_TIMER"], "optional": []},
    "cancel_timer":  {"required": ["ACTION_CANCEL", "OBJ_TIMER"], "optional": []},
    "set_alarm":     {"required": ["ACTION_SET", "OBJ_ALARM"], "optional": []},
    "cancel_alarm":  {"required": ["ACTION_CANCEL", "OBJ_ALARM"], "optional": []},
    # weather
    "weather_query": {"required": ["OBJ_WEATHER"], "optional": []},
    # reminders
    "add_reminder":  {"required": ["OBJ_REMINDER"], "optional": []},
    # communication
    "call_contact":  {"required": ["OBJ_PHONE"], "optional": []},
    "send_message":  {"required": ["ACTION_SEND", "OBJ_MESSAGE"], "optional": []},
    "add_note":      {"required": ["ACTION_SEND", "OBJ_NOTE"], "optional": []},
    # shopping
    "add_shopping":  {"required": ["OBJ_SHOPPING"], "optional": []},
    # information
    "time_query":    {"required": ["ACTION_ASK", "OBJ_TIME"], "optional": []},
    "date_query":    {"required": ["ACTION_ASK", "OBJ_DATE"], "optional": []},
    "search_query":  {"required": ["OBJ_SEARCH"], "optional": []},
    # navigation
    "navigate_to":   {"required": ["ACTION_GO"], "optional": []},
    # system
    "get_help":      {"required": ["OBJ_HELP"], "optional": []},
    "stop_all":      {"required": ["OBJ_HALT"], "optional": []},
}

# ── domain grouping ────────────────────────────────────────────────────────

DOMAINS = {
    "media":         ["play_music", "pause_music", "next_track",
                      "volume_up", "volume_down"],
    "lights":        ["lights_on", "lights_off"],
    "climate":       ["heating_up", "heating_down", "check_hvac"],
    "timers":        ["set_timer", "cancel_timer", "set_alarm", "cancel_alarm"],
    "weather":       ["weather_query"],
    "reminders":     ["add_reminder"],
    "communication": ["call_contact", "send_message", "add_note"],
    "shopping":      ["add_shopping"],
    "information":   ["time_query", "date_query", "search_query"],
    "navigation":    ["navigate_to"],
    "system":        ["get_help", "stop_all"],
}

# ── labelled test utterances ───────────────────────────────────────────────

TEST_CASES = [
    # play_music — ACTION_PLAY + OBJ_MUSIC
    ("play some music",                       "play_music"),
    ("put on a song",                         "play_music"),
    ("play my favourite playlist",            "play_music"),
    ("queue up the next album",               "play_music"),
    ("put on a podcast",                      "play_music"),
    ("play that track again please",          "play_music"),
    ("can you play some music",               "play_music"),

    # pause_music — ACTION_STOP + OBJ_MUSIC
    ("pause the music",                       "pause_music"),
    ("stop the song",                         "pause_music"),
    ("halt the playlist",                     "pause_music"),
    ("pause this track for a sec",            "pause_music"),
    ("can you stop the music please",         "pause_music"),

    # next_track — ACTION_SKIP (+ OBJ_MUSIC)
    ("next track",                            "next_track"),
    ("skip this song",                        "next_track"),
    ("skip",                                  "next_track"),
    ("next please",                           "next_track"),
    ("skip to the next track",                "next_track"),

    # volume_up — ACTION_RAISE + OBJ_AUDIO
    ("turn up the volume",                    "volume_up"),
    ("crank up the volume please",            "volume_up"),
    ("raise the volume a bit",                "volume_up"),
    ("increase the volume",                   "volume_up"),
    ("turn up the music",                     "volume_up"),

    # volume_down — ACTION_LOWER + OBJ_AUDIO
    ("turn down the volume",                  "volume_down"),
    ("lower the volume",                      "volume_down"),
    ("decrease the volume a little",          "volume_down"),
    ("turn down the music please",            "volume_down"),

    # lights_on — ACTION_ON + OBJ_LIGHT
    ("turn on the lights",                    "lights_on"),
    ("switch on the lamp",                    "lights_on"),
    ("turn on the light in here",             "lights_on"),
    ("enable the lighting",                   "lights_on"),
    ("can you turn on the lights",            "lights_on"),

    # lights_off — ACTION_OFF + OBJ_LIGHT
    ("turn off the lights",                   "lights_off"),
    ("switch off the lamp",                   "lights_off"),
    ("turn off the light please",             "lights_off"),
    ("disable the lighting",                  "lights_off"),

    # heating_up — ACTION_RAISE + OBJ_HVAC
    ("turn up the heating",                   "heating_up"),
    ("crank up the heater",                   "heating_up"),
    ("raise the thermostat",                  "heating_up"),
    ("increase the heating a bit",            "heating_up"),

    # heating_down — ACTION_LOWER + OBJ_HVAC
    ("turn down the heating",                 "heating_down"),
    ("lower the thermostat",                  "heating_down"),
    ("decrease the heating",                  "heating_down"),
    ("turn down the radiator please",         "heating_down"),

    # check_hvac — ACTION_ASK + OBJ_HVAC
    ("what's the thermostat at",              "check_hvac"),
    ("check the heating",                     "check_hvac"),
    ("tell me the thermostat setting",        "check_hvac"),
    ("how's the heating doing",               "check_hvac"),

    # set_timer — ACTION_SET + OBJ_TIMER
    ("set a timer",                           "set_timer"),
    ("create a timer for ten minutes",        "set_timer"),
    ("start a countdown",                     "set_timer"),
    ("make a timer for five minutes",         "set_timer"),

    # cancel_timer — ACTION_CANCEL + OBJ_TIMER
    ("cancel the timer",                      "cancel_timer"),
    ("delete the timer",                      "cancel_timer"),
    ("clear the countdown",                   "cancel_timer"),
    ("remove the timer please",               "cancel_timer"),

    # set_alarm — ACTION_SET + OBJ_ALARM
    ("set an alarm",                          "set_alarm"),
    ("create an alarm for seven",             "set_alarm"),
    ("make an alarm for the morning",         "set_alarm"),
    ("schedule an alarm",                     "set_alarm"),

    # cancel_alarm — ACTION_CANCEL + OBJ_ALARM
    ("cancel the alarm",                      "cancel_alarm"),
    ("delete the alarm",                      "cancel_alarm"),
    ("remove the alarm",                      "cancel_alarm"),
    ("clear the alarm please",                "cancel_alarm"),

    # weather_query — OBJ_WEATHER
    ("what's the weather",                    "weather_query"),
    ("is it going to rain",                   "weather_query"),
    ("do i need an umbrella",                 "weather_query"),
    ("what's the forecast",                   "weather_query"),
    ("is there snow coming",                  "weather_query"),
    ("is it going to snow",                   "weather_query"),

    # add_reminder — OBJ_REMINDER
    ("set a reminder",                        "add_reminder"),
    ("remind me to buy milk",                 "add_reminder"),
    ("create a reminder for the meeting",     "add_reminder"),
    ("add a reminder",                        "add_reminder"),

    # call_contact — OBJ_PHONE
    ("call mum",                              "call_contact"),
    ("phone the bank",                        "call_contact"),
    ("dial charlie",                          "call_contact"),
    ("ring my brother",                       "call_contact"),

    # send_message — ACTION_SEND + OBJ_MESSAGE
    ("send a message to bob",                 "send_message"),
    ("write a text to alice",                 "send_message"),
    ("draft an email",                        "send_message"),
    ("send a text please",                    "send_message"),

    # add_note — ACTION_SEND + OBJ_NOTE
    ("write a note",                          "add_note"),
    ("jot down a note",                       "add_note"),
    ("leave a note for sam",                  "add_note"),
    ("draft a memo",                          "add_note"),

    # add_shopping — OBJ_SHOPPING
    ("add milk to the shopping list",         "add_shopping"),
    ("i need to buy groceries",               "add_shopping"),
    ("add eggs to the shopping",              "add_shopping"),

    # time_query — ACTION_ASK + OBJ_TIME
    ("what is the time",                      "time_query"),
    ("tell me the time",                      "time_query"),
    ("check the time for me",                 "time_query"),
    ("what's the time",                       "time_query"),

    # date_query — ACTION_ASK + OBJ_DATE
    ("what's the date",                       "date_query"),
    ("tell me the date",                      "date_query"),
    ("what is today's date",                  "date_query"),
    ("what's today",                          "date_query"),

    # search_query — OBJ_SEARCH
    ("search for nearby restaurants",         "search_query"),
    ("look up the train times",               "search_query"),
    ("google italian recipes",                "search_query"),
    ("search for a plumber",                  "search_query"),

    # navigate_to — ACTION_GO
    ("navigate to the airport",               "navigate_to"),
    ("take me to the station",                "navigate_to"),
    ("drive to the office",                   "navigate_to"),
    ("directions to the hospital",            "navigate_to"),
    ("get me to work",                        "navigate_to"),

    # get_help — OBJ_HELP
    ("help",                                  "get_help"),
    ("what commands do you have",             "get_help"),
    ("i need help",                           "get_help"),

    # stop_all — OBJ_HALT
    ("stop",                                  "stop_all"),
    ("cancel",                                "stop_all"),
    ("abort",                                 "stop_all"),
    ("never mind",                            "stop_all"),

    # ── cross-domain action collision ─────────────────────────────────────
    # The ACTION keyword is shared across domains; the OBJECT decides the
    # domain. A correct engine follows the object, not the action.
    ("turn up the heating in here",           "heating_up"),
    ("turn up the volume on the stereo",      "volume_up"),
    ("crank up the radiator",                 "heating_up"),
    ("crank up the music",                    "volume_up"),
    ("switch on the kitchen lamp",            "lights_on"),
    ("pause the podcast",                     "pause_music"),
    ("set a timer for the pasta",             "set_timer"),
    ("set an alarm for the gym",              "set_alarm"),

    # ── domain-context cases ──────────────────────────────────────────────
    # The utterance's dominant intent matches cleanly on coverage, but a
    # keyword for a single-slot intent in another domain is also present
    # as a distractor. The dominant intent should still win.
    ("play the song on the radio",            "play_music"),
    ("put on a podcast about the weather",    "play_music"),
    ("turn off the lights then call mum",     "lights_off"),
    ("write a note about the shopping",       "add_note"),
    ("set a timer for the laundry",           "set_timer"),

    # ── discriminating: flat & domain win, hierarchical loses ─────────────
    # Real single-intent commands. The OBJECT keyword is unambiguous, but the
    # utterance also carries a long room/topic word that pulls the stage-1
    # coverage classifier to the wrong domain; the misroute is unrecoverable.
    # One-word commands give the classifier nothing to route on at all.
    ("play music in the living room",         "play_music"),
    ("turn up the volume in the bedroom",     "volume_up"),
    ("call mum about the heating",            "call_contact"),
    ("set a timer in the living room",        "set_timer"),
    ("look up the temperature",               "search_query"),
    ("google the heating thermostat",         "search_query"),
    ("the temperature please",                "weather_query"),
    ("stop the timer",                        "stop_all"),

    # ── discriminating: flat and domain diverge ───────────────────────────
    # Two-clause utterances carrying two intents. Labelled by the leading
    # clause. Flat scores every parser against one shared clique; domain
    # scores each clause in its own isolated sub-engine. Because adapt
    # confidence divides each intent's score by the total tag count of its
    # clique, the two topologies break the tie between clauses differently.
    ("turn off the lights and stop the music",   "lights_off"),
    ("turn up the heating and lower the volume", "heating_up"),
    ("turn on the lights and pause the music",   "lights_on"),
    ("play some music and turn on the lights",   "play_music"),
    ("lower the heating and pause the music",    "heating_down"),
    ("play a podcast and turn down the heating", "play_music"),
]

# ── no-match utterances ────────────────────────────────────────────────────
# Plausible but not commands. Many contain a keyword used outside a command
# context to stress the false-positive rate.

NO_MATCH_UTTERANCES = [
    # conversational / off-topic
    "um yeah so anyway",
    "right okay then",
    "hmm not sure about that",
    "oh that's interesting",
    "fair enough i suppose",
    "the dog ate my homework",
    "did you see the match last night",
    "my knee has been giving me trouble",
    "what a lovely afternoon",
    "i really fancy a cup of tea",
    "the cat has been acting strange",
    "that film was brilliant",
    "i can't believe how fast the year went",

    # single object keyword, no action — must not fire a two-slot intent
    "the music at the restaurant was lovely",
    "the lights looked beautiful at the concert",
    "the heating bill was enormous this month",
    "the alarm woke the whole street",
    "the timer on the oven is broken",
    "she left her phone on the table",
    "the weather has been miserable lately",
    "my shopping bag split open",
    "the thermostat is on the hallway wall",
    "the radiator needs bleeding again",
    "i love a good podcast on a long drive",

    # action keyword, no object — must not fire a two-slot intent
    "could you turn it up a bit",
    "go ahead and switch it on",
    "i need you to turn that down",
    "just put it on for me",
    "can you cancel it",

    # overlapping keyword used non-literally
    "they cancel each other out",
    "let's call it a day",
    "he was dead set against the idea",
    "give the new hire a warm welcome",
    "kill the engine before you park",
    "stop right there",
    "i had to turn down the job offer",
    "the music just would not stop",

    # rhetorical / reported speech
    "who even sets an alarm on a sunday",
    "she asked him to call her back",
    "they said the music was too loud",
    "what would you do if the lights went out",
    "imagine if you could just skip the boring bits",

    # nonsense
    "blarg wump fizz",
    "one fish two fish red fish",
    "lorem ipsum dolor sit amet",
    "the mitochondria is the powerhouse of the cell",

    # ── discriminating: hierarchical wins, flat & domain lose ─────────────
    # Not commands, but each contains a bare keyword for a single-slot intent
    # (stop_all). Flat and domain fire stop_all on the lone word. The stage-1
    # classifier routes these to a two-slot domain (media or timers) whose
    # intents need a second keyword that is absent, so nothing fires and no
    # false positive is emitted.
    "they cancel each other out",
    "they never stop arguing",
    "the bus stop was crowded",
    "cancel culture is everywhere",
    "we should cancel the trip",
    "i had to cancel my plans",
    "stop right there",
    "they would not stop talking",
    "the train made a quick stop",
    "the cancel button was greyed out",
]
