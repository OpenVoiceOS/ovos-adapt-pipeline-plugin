"""
Keyword-intent benchmark dataset for the Adapt engine.

Used to compare the flat ``IntentDeterminationEngine`` against the
``DomainIntentDeterminationEngine`` on identical vocabulary and intents.

Structure
---------
VOCAB
    entity_type → list of entity_value strings that belong to that slot.
    These are the words a skill would register via ``register_vocab``.

INTENTS
    intent_name → {"required": [entity_type, ...], "optional": [entity_type, ...]}
    Mirrors what a skill sends via ``register_intent`` (IntentBuilder).

DOMAINS
    domain_name → list of intent_names grouped into that domain.
    The domain engine registers each intent's parser and entities into its
    domain's isolated sub-engine (separate Trie + tagger).

TEST_CASES
    List of (utterance, expected_intent_or_None).
    Utterances are realistic natural-language phrasing that contains one or
    more of the registered keywords.  They are NOT template fills — they
    include filler words, contractions, politeness markers, and word-order
    variation that real STT output produces.

NO_MATCH_UTTERANCES
    Utterances that share surface words with intents but should NOT match any.
"""

# ── vocabulary ─────────────────────────────────────────────────────────────

VOCAB = {
    # media
    "PlayKeyword":      ["play", "put on", "start playing", "i want to hear",
                         "listen to", "get some", "chuck on", "stick on"],
    "StopKeyword":      ["stop", "pause", "halt", "cancel"],
    "MusicKeyword":     ["music", "song", "track", "tunes", "playlist"],
    "NextKeyword":      ["next", "skip", "forward"],
    "VolumeKeyword":    ["volume", "louder", "quieter", "turn up", "turn down",
                         "crank up", "ease off"],

    # timers & alarms
    "TimerKeyword":     ["timer", "countdown", "count down"],
    "AlarmKeyword":     ["alarm", "wake me up", "wake me", "get me up"],
    "SetKeyword":       ["set", "start", "create", "make"],
    "CancelKeyword":    ["cancel", "delete", "remove", "stop", "turn off",
                         "forget", "kill", "get rid of"],
    "RemindKeyword":    ["remind me", "reminder", "don't let me forget",
                         "nudge me", "don't forget", "put a reminder",
                         "set a reminder", "i need to be reminded",
                         "need to be reminded"],

    # weather
    "WeatherKeyword":   ["weather", "forecast", "temperature", "rain",
                         "umbrella", "raining", "sunny", "cold", "hot", "warm",
                         "conditions", "jacket", "coat"],

    # smart home — lights
    "LightKeyword":     ["light", "lights", "lighting"],
    "OnKeyword":        ["on", "brighten", "turn on", "switch on", "flick on"],
    "OffKeyword":       ["off", "turn off", "switch off", "dim", "flick off",
                         "kill", "go dark", "lights out"],

    # smart home — thermostat
    "ThermostatKeyword": ["thermostat", "temperature", "heating", "heat",
                          "cooling", "cool", "degrees"],
    "HeatKeyword":      ["warmer", "warm", "hotter", "hot", "heat up",
                         "turn up", "crank up", "freeze", "freezing"],
    "CoolKeyword":      ["cooler", "cool", "cold", "cool down", "turn down",
                         "boiling", "too hot"],

    # communication
    "CallKeyword":      ["call", "phone", "ring", "dial", "get on the line"],
    "MessageKeyword":   ["message", "text", "send", "drop", "ping",
                         "send a message", "shoot"],
    "NoteKeyword":      ["note", "write", "jot", "take a note", "write down",
                         "make a note", "note down"],

    # shopping
    "ShoppingKeyword":  ["shopping list", "shopping", "buy", "need",
                         "add to the list", "put on the list", "out of",
                         "running low on", "pick up", "running out"],
    "ItemKeyword":      ["item", "product", "thing", "stuff"],

    # information
    "TimeKeyword":      ["time", "what time", "what's the time", "current time",
                         "time check", "how late", "what hour"],
    "DateKeyword":      ["date", "day", "today", "what day", "what month",
                         "day of the week", "what's today"],
    "SearchKeyword":    ["search", "look up", "google", "find", "search for",
                         "what is", "what are"],

    # navigation
    "NavigateKeyword":  ["navigate", "directions", "route", "take me to",
                         "drive to", "get me to", "how do i get to",
                         "find a route", "direct me"],

    # system
    "HelpKeyword":      ["help", "what can you do", "capabilities",
                         "list your skills", "what do you know", "commands"],
    "StopCancelKeyword": ["stop", "cancel", "abort", "never mind", "forget it",
                          "leave it", "don't bother", "scrap that"],
}

# ── intent definitions ─────────────────────────────────────────────────────

INTENTS = {
    "play_music": {
        "required": ["PlayKeyword"],
        "optional": ["MusicKeyword"],
    },
    "pause_music": {
        "required": ["StopKeyword", "MusicKeyword"],
        "optional": [],
    },
    "next_track": {
        "required": ["NextKeyword"],
        "optional": ["MusicKeyword"],
    },
    "set_volume": {
        "required": ["VolumeKeyword"],
        "optional": [],
    },
    "set_timer": {
        "required": ["SetKeyword", "TimerKeyword"],
        "optional": [],
    },
    "set_alarm": {
        "required": ["AlarmKeyword"],
        "optional": ["SetKeyword"],
    },
    "cancel_timer": {
        "required": ["CancelKeyword", "TimerKeyword"],
        "optional": [],
    },
    "weather_query": {
        "required": ["WeatherKeyword"],
        "optional": [],
    },
    "lights_on": {
        "required": ["LightKeyword", "OnKeyword"],
        "optional": [],
    },
    "lights_off": {
        "required": ["LightKeyword", "OffKeyword"],
        "optional": [],
    },
    "thermostat_set": {
        "required": ["ThermostatKeyword"],
        "optional": ["HeatKeyword", "CoolKeyword"],
    },
    "call_contact": {
        "required": ["CallKeyword"],
        "optional": [],
    },
    "send_message": {
        "required": ["MessageKeyword"],
        "optional": [],
    },
    "add_note": {
        "required": ["NoteKeyword"],
        "optional": [],
    },
    "add_shopping": {
        "required": ["ShoppingKeyword"],
        "optional": [],
    },
    "time_query": {
        "required": ["TimeKeyword"],
        "optional": [],
    },
    "date_query": {
        "required": ["DateKeyword"],
        "optional": [],
    },
    "search_query": {
        "required": ["SearchKeyword"],
        "optional": [],
    },
    "navigate_to": {
        "required": ["NavigateKeyword"],
        "optional": [],
    },
    "help": {
        "required": ["HelpKeyword"],
        "optional": [],
    },
    "stop": {
        "required": ["StopCancelKeyword"],
        "optional": [],
    },
    "add_reminder": {
        "required": ["RemindKeyword"],
        "optional": [],
    },
}

# ── domain grouping ────────────────────────────────────────────────────────
# Semantically related intents grouped into domains. The domain engine gives
# each domain its own isolated sub-engine (separate Trie + entity tagger).

DOMAINS = {
    "media":         ["play_music", "pause_music", "next_track", "set_volume"],
    "timers_alarms": ["set_timer", "set_alarm", "cancel_timer", "add_reminder"],
    "weather":       ["weather_query"],
    "lights":        ["lights_on", "lights_off"],
    "climate":       ["thermostat_set"],
    "communication": ["call_contact", "send_message", "add_note"],
    "shopping":      ["add_shopping"],
    "information":   ["time_query", "date_query", "search_query"],
    "navigation":    ["navigate_to"],
    "system":        ["help", "stop"],
}

# ── labelled test utterances ───────────────────────────────────────────────

TEST_CASES = [
    # play_music
    ("play some jazz please",               "play_music"),
    ("put on some background music",        "play_music"),
    ("i want to hear something calm",       "play_music"),
    ("can you play the beatles",            "play_music"),
    ("chuck on a playlist",                 "play_music"),
    ("start playing something upbeat",      "play_music"),
    ("stick on some tunes",                 "play_music"),
    ("get some lo-fi going",                "play_music"),
    ("listen to pink floyd",                "play_music"),
    ("play that song i like",               "play_music"),

    # pause_music
    ("pause the music",                     "pause_music"),
    ("stop the track",                      "pause_music"),
    ("pause that song for a moment",        "pause_music"),
    ("can you stop the music please",       "pause_music"),
    ("halt the music",                      "pause_music"),

    # next_track
    ("next track please",                   "next_track"),
    ("skip this song",                      "next_track"),
    ("skip to the next one",                "next_track"),
    ("next please",                         "next_track"),
    ("skip forward a track",                "next_track"),

    # set_volume
    ("volume up please",                    "set_volume"),
    ("make it louder",                      "set_volume"),
    ("turn it down a bit",                  "set_volume"),
    ("could you turn the volume down",      "set_volume"),
    ("crank up the volume",                 "set_volume"),
    ("volume quieter please",               "set_volume"),

    # set_timer
    ("set a timer please",                  "set_timer"),
    ("can you set a timer for five minutes", "set_timer"),
    ("start a countdown",                   "set_timer"),
    ("make a ten minute timer",             "set_timer"),
    ("create a timer for half an hour",     "set_timer"),

    # set_alarm
    ("wake me up at seven",                 "set_alarm"),
    ("set an alarm for six thirty",         "set_alarm"),
    ("i need an alarm",                     "set_alarm"),
    ("wake me tomorrow morning",            "set_alarm"),
    ("get me up at six",                    "set_alarm"),

    # cancel_timer
    ("cancel the timer",                    "cancel_timer"),
    ("stop the timer",                      "cancel_timer"),
    ("delete the countdown",                "cancel_timer"),
    ("get rid of the timer",                "cancel_timer"),
    ("turn off the timer",                  "cancel_timer"),

    # weather_query
    ("what's the weather like today",       "weather_query"),
    ("do i need an umbrella",               "weather_query"),
    ("is it going to rain",                 "weather_query"),
    ("should i bring a coat",               "weather_query"),
    ("how cold is it outside",              "weather_query"),
    ("what's the forecast",                 "weather_query"),
    ("is it sunny today",                   "weather_query"),
    ("what's the temperature",              "weather_query"),

    # lights_on
    ("turn the lights on please",           "lights_on"),
    ("lights on",                           "lights_on"),
    ("switch on the lights",                "lights_on"),
    ("can you flick on the lights",         "lights_on"),
    ("brighten the lights up",              "lights_on"),

    # lights_off
    ("turn the lights off",                 "lights_off"),
    ("lights off please",                   "lights_off"),
    ("switch off the lights",               "lights_off"),
    ("dim the lights",                      "lights_off"),
    ("go dark",                             "lights_off"),
    ("kill the lights",                     "lights_off"),

    # thermostat_set
    ("set the thermostat",                  "thermostat_set"),
    ("adjust the heating",                  "thermostat_set"),
    ("it's freezing turn the heating up",   "thermostat_set"),
    ("can you cool it down",                "thermostat_set"),
    ("make it warmer in here",              "thermostat_set"),
    ("change the temperature please",       "thermostat_set"),

    # call_contact
    ("call alice please",                   "call_contact"),
    ("ring dad",                            "call_contact"),
    ("phone the office",                    "call_contact"),
    ("dial charlie",                        "call_contact"),
    ("can you get sarah on the line",       "call_contact"),

    # send_message
    ("send a message to alice",             "send_message"),
    ("text john please",                    "send_message"),
    ("drop bob a message",                  "send_message"),
    ("ping sarah",                          "send_message"),
    ("shoot charlie a text",                "send_message"),

    # add_note
    ("take a note",                         "add_note"),
    ("write this down",                     "add_note"),
    ("make a note of that",                 "add_note"),
    ("jot this down please",                "add_note"),
    ("note that the meeting moved",         "add_note"),

    # add_shopping
    ("add milk to the shopping list",       "add_shopping"),
    ("put bread on the shopping list",      "add_shopping"),
    ("we need to buy coffee",               "add_shopping"),
    ("running low on eggs",                 "add_shopping"),
    ("pick up some cheese",                 "add_shopping"),
    ("out of washing up liquid",            "add_shopping"),

    # time_query
    ("what time is it",                     "time_query"),
    ("what's the time",                     "time_query"),
    ("current time please",                 "time_query"),
    ("time check",                          "time_query"),
    ("how late is it",                      "time_query"),
    ("what hour is it",                     "time_query"),

    # date_query
    ("what day is it today",                "date_query"),
    ("what's today's date",                 "date_query"),
    ("what month are we in",                "date_query"),
    ("what day of the week is it",          "date_query"),
    ("is today a monday",                   "date_query"),

    # search_query
    ("search for the nearest pharmacy",     "search_query"),
    ("look up sourdough recipe",            "search_query"),
    ("google how to fix a leak",            "search_query"),
    ("find a good pizza place",             "search_query"),
    ("what is photosynthesis",              "search_query"),
    ("what are the symptoms of a cold",     "search_query"),

    # navigate_to
    ("navigate to the airport",             "navigate_to"),
    ("get directions to the hospital",      "navigate_to"),
    ("take me to the station",              "navigate_to"),
    ("how do i get to the city centre",     "navigate_to"),
    ("find a route to the supermarket",     "navigate_to"),
    ("get me to work please",               "navigate_to"),

    # help
    ("help",                                "help"),
    ("what can you do",                     "help"),
    ("list your skills please",             "help"),
    ("show me your capabilities",           "help"),
    ("what commands do you know",           "help"),

    # stop
    ("stop",                                "stop"),
    ("cancel that",                         "stop"),
    ("never mind",                          "stop"),
    ("forget it",                           "stop"),
    ("abort",                               "stop"),
    ("scrap that",                          "stop"),
    ("leave it",                            "stop"),
    ("don't bother",                        "stop"),

    # ── harder cases: keyword present but embedded in longer phrasing ──────
    ("can you turn the volume up a bit please",      "set_volume"),
    ("it is way too loud in here turn it down",      "set_volume"),
    ("do me a favour and ring my dad",               "call_contact"),
    ("go ahead and navigate me to the supermarket",  "navigate_to"),
    ("i think we need to buy some milk actually",    "add_shopping"),
    ("can you just search for the nearest chemist",  "search_query"),
    ("set a ten minute timer would you",             "set_timer"),
    ("could you wake me up at half six tomorrow",    "set_alarm"),
    ("what's the weather going to be like tomorrow", "weather_query"),
    ("can someone tell me what time it is",          "time_query"),
    ("go on then cancel the timer",                  "cancel_timer"),
    ("lights please turn them on",                   "lights_on"),
    ("flip the lights off would you",                "lights_off"),
    ("can you look up what the capital of france is","search_query"),
    ("dial my brother's number",                     "call_contact"),
    ("drop sarah a quick text saying i'm on my way", "send_message"),
    ("jot this down the meeting is at three",        "add_note"),
    ("add bananas and milk to the shopping please",  "add_shopping"),
    ("get directions to the nearest hospital",       "navigate_to"),
    ("give me a hand what day is it today",          "date_query"),

    # ── ambiguous phrasing (correct intent requires keyword disambiguation) ─
    ("the temperature please",                       "weather_query"),
    ("it's really cold outside",                     "weather_query"),
    ("turn the heating up a few degrees",            "thermostat_set"),
    ("skip to the next track please",                "next_track"),
    ("i need to be reminded to call the dentist",    "add_reminder"),
    ("put a reminder on for my doctor's appointment","add_reminder"),

    # ── short utterances (1–3 words) ──────────────────────────────────────
    ("play",                    "play_music"),
    ("pause the music",             "pause_music"),
    ("next",                    "next_track"),
    ("louder",                  "set_volume"),
    ("quieter",                 "set_volume"),
    ("timer",                   "set_timer"),
    ("cancel",                  "stop"),
    ("navigate",                "navigate_to"),
    ("search",                  "search_query"),
    ("lights on",               "lights_on"),
    ("lights off",              "lights_off"),
    ("time please",             "time_query"),
    ("what day",                "date_query"),
    ("call mum",                "call_contact"),
    ("text alice",              "send_message"),
    ("write this",              "add_note"),
    ("buy milk",                "add_shopping"),
    ("wake me",                 "set_alarm"),
    ("the weather",             "weather_query"),

    # ── medium utterances (4–8 words) ────────────────────────────────────
    ("skip this i don't like it",                   "next_track"),
    ("how warm is it today",                        "weather_query"),
    ("remind me about the meeting",                 "add_reminder"),
    ("send bob a quick message",                    "send_message"),
    ("turn up the volume a bit",                    "set_volume"),
    ("what time does the sun set",                  "time_query"),
    ("look up the bus timetable",                   "search_query"),
    ("put a timer on for lunch",                    "set_timer"),
    ("phone my sister in law",                      "call_contact"),
    ("write down eggs butter flour",                "add_note"),
    ("get directions to the station",               "navigate_to"),
    ("turn the heating down a bit",                 "thermostat_set"),
    ("add bread to shopping list",                  "add_shopping"),
    ("set an alarm for six am",                     "set_alarm"),
    ("switch the bathroom light on",                "lights_on"),
    ("can you stop the current song",               "pause_music"),

    # ── long utterances (9–14 words) ─────────────────────────────────────
    ("i was wondering if you could look up how to make pasta carbonara",   "search_query"),
    ("do you think you could turn the music down just a little bit please","set_volume"),
    ("i need you to set a reminder so i don't forget to take my tablets",  "add_reminder"),
    ("could you get directions to the nearest petrol station from here",   "navigate_to"),
    ("i'd really appreciate it if you could turn the lights off in here",  "lights_off"),
    ("before i go to bed can you set an alarm for half past six tomorrow", "set_alarm"),
    ("actually you know what just cancel that ignore everything i said",   "stop"),
    ("is it going to be warm enough to go outside without a coat today",   "weather_query"),
    ("can you put oat milk and a dozen eggs on the shopping list for me",  "add_shopping"),
    ("i need to call the doctor's surgery can you dial them for me please","call_contact"),
    ("write this down i owe sarah twenty quid for the cinema last night",  "add_note"),
    ("set a five minute countdown so i know when to take the pasta off",   "set_timer"),
    ("let me know what time it is i've completely lost track of the day",  "time_query"),
    ("is there any chance you could bump the thermostat up a few degrees", "thermostat_set"),
    ("can you skip this track i've heard it about a hundred times already","next_track"),

    # ── very long utterances (15+ words) ─────────────────────────────────
    ("i know this is a bit of a long one but could you please navigate me to the shopping centre on the high street", "navigate_to"),
    ("i'm running a bit late and i was wondering if you could send a message to alice letting her know i'll be there in about twenty minutes", "send_message"),
    ("look i really don't want to forget this so could you please write it down somewhere the pin for my new card is one two three four", "add_note"),
    ("i've been trying to remember all morning what time my dentist appointment is and i just cannot work it out can you look it up for me", "search_query"),
    ("the music is absolutely lovely but honestly it is just a tiny little bit too loud for me right now so could you turn it down please", "set_volume"),
    ("it's been a really long week and i just want to relax so could you put on something calm and peaceful to listen to in the background", "play_music"),
    ("i need to be up early tomorrow for a really important meeting so could you set an alarm for six o'clock in the morning without fail please", "set_alarm"),
    ("before we head out i want to make sure the lights are all switched off so could you please go ahead and turn them all off right now", "lights_off"),

    # ── multi-intent queries: two intents' keywords both present ──────────
    # The labelled intent is the one a parser should prefer (higher coverage /
    # more required slots matched).  These stress-test disambiguation logic.
    ("stop the music and cancel my alarm",
     "pause_music"),       # StopKeyword+MusicKeyword outranks cancel alone
    ("turn off the lights and set a timer for ten minutes",
     "set_timer"),         # primary intent is setting a timer
    ("skip this song and turn it up",
     "next_track"),        # next_track keyword more specific than volume alone
    ("call alice and remind her about the meeting",
     "call_contact"),      # CallKeyword direct; remind surfaces as optional
    ("what time is it and what's the weather like",
     "time_query"),        # time_query slots dominate in this ordering
    ("search for pizza places and navigate to the best one",
     "navigate_to"),       # navigate has stronger required-keyword coverage
    ("set a timer and remind me to check it",
     "add_reminder"),      # remind slot wins; set+timer covered but remind more specific
    ("send a message to bob and add milk to the shopping list",
     "send_message"),      # MessageKeyword direct match wins
    ("cancel the alarm and never mind the timer",
     "stop"),              # StopCancelKeyword matches "never mind"; cancel alone fires stop
    ("pause the music and turn down the volume",
     "set_volume"),        # VolumeKeyword+DirectionKeyword outranks pause_music coverage

    # ── entity-overlap cases ──────────────────────────────────────────────
    # Each utterance contains a word registered under two or more entity
    # types spanning two or more domains. The correct intent is decided by
    # the *other* keywords present. These stress whether per-domain trie
    # isolation changes the matched intent versus a shared trie.

    # "turn up" / "turn down" / "crank up" — VolumeKeyword (media)
    #                                        ∩ Heat/CoolKeyword (climate)
    ("turn up the music a bit",             "set_volume"),
    ("turn up the volume now",              "set_volume"),
    ("crank up the tunes",                  "set_volume"),
    ("turn down the music",                 "set_volume"),
    ("turn down the volume a little",       "set_volume"),
    ("ease off the volume",                 "set_volume"),
    ("turn up the heating",                 "thermostat_set"),
    ("crank up the heating please",         "thermostat_set"),
    ("turn down the heating",               "thermostat_set"),
    ("turn down the thermostat",            "thermostat_set"),
    ("turn up the heat in here",            "thermostat_set"),

    # "temperature" / "hot" / "cold" / "warm" — WeatherKeyword (weather)
    #                          ∩ Thermostat/Heat/CoolKeyword (climate)
    ("what's the temperature outside",      "weather_query"),
    ("is it hot out today",                 "weather_query"),
    ("is it cold out",                      "weather_query"),
    ("is it warm out there",                "weather_query"),
    ("set the thermostat temperature",      "thermostat_set"),
    ("check the thermostat",                "thermostat_set"),
    ("lower the thermostat",                "thermostat_set"),
    ("drop it a couple of degrees",         "thermostat_set"),
    ("bump it up a few degrees",            "thermostat_set"),

    # "stop" / "pause" / "halt" / "cancel" — StopKeyword (media)
    #                  ∩ Cancel/StopCancelKeyword (timers / system)
    ("stop the music",                      "pause_music"),
    ("pause the track",                     "pause_music"),
    ("halt the song",                       "pause_music"),
    ("cancel the timer right now",          "cancel_timer"),
    ("stop the countdown",                  "cancel_timer"),
    ("delete the timer",                    "cancel_timer"),
    ("abort the whole thing",               "stop"),
    ("never mind cancel it",                "stop"),

    # "kill" — CancelKeyword (timers) ∩ OffKeyword (lights)
    ("kill the timer",                      "cancel_timer"),
    ("kill the bedroom lights",             "lights_off"),

    # "start" / "make" — SetKeyword (timers)
    ("start a timer for me",                "set_timer"),
    ("make a quick timer",                  "set_timer"),
]

# ── no-match utterances ────────────────────────────────────────────────────
# Includes both easy (no keyword overlap) and hard (surface keyword present
# but not a command) cases to stress-test false-positive rate.

NO_MATCH_UTTERANCES = [
    # ── easy: conversational / off-topic — no keyword overlap ────────────────
    "um yeah so anyway",
    "right okay then",
    "hmm not sure about that",
    "oh interesting",
    "fair enough",
    "the dog ate my homework",
    "i've been thinking about getting a new sofa",
    "did you see the match last night",
    "my knee's been giving me trouble",
    "i went to the dentist yesterday",
    "what a lovely afternoon it is",
    "i really fancy a cup of tea",
    "the cat's been acting strange all week",
    "that film last night was brilliant",
    "i can't believe how fast the year's gone",
    "my back's been killing me since tuesday",

    # ── single keyword present but not a command ──────────────────────────────
    "my friend alice rang me earlier",             # 'ring' ∈ CallKeyword
    "the music at that restaurant was terrible",   # 'music' ∈ MusicKeyword
    "i watched a documentary about the weather",   # 'weather' ∈ WeatherKeyword
    "the lights were beautiful at the concert",    # 'lights' ∈ LightKeyword (no on/off)
    "the alarm woke the whole street",             # 'alarm' ∈ AlarmKeyword
    "my shopping bag broke",                       # 'shopping' ∈ ShoppingKeyword
    "the timer on the oven is broken",             # 'timer' ∈ TimerKeyword
    "i always stop for coffee in the morning",     # 'stop' ∈ StopKeyword
    "she left me a note on the table",             # 'note' ∈ NoteKeyword
    "the day was long",                            # 'day' ∈ DateKeyword
    "he could navigate by the stars",              # 'navigate' ∈ NavigateKeyword
    "she sent a text to her mum",                  # 'text'+'send' — past tense report
    "the play was set in the victorian era",       # 'set' ∈ SetKeyword
    "we need more people like her",                # 'need' ∈ ShoppingKeyword
    "the volume of complaints has gone up",        # 'volume' ∈ VolumeKeyword — noun
    "the track record speaks for itself",          # 'track' ∈ MusicKeyword — idiom
    "i find that hard to believe",                 # 'find' ∈ SearchKeyword — not a search
    "next time i'll remember",                     # 'next' ∈ NextKeyword — temporal not skip
    "the forecast was wrong again",                # 'forecast' ∈ WeatherKeyword — report
    "they called an emergency meeting",            # 'called' ∈ CallKeyword — past tense

    # ── multiple keywords present, still not a command ────────────────────────
    "the weather alarm went off at six",           # 'weather'+'alarm' — description
    "i need to buy some time",                     # 'buy'+'time' — idiom
    "call it a day",                               # 'call'+'day' — idiom
    "stop and note the temperature outside",       # many keywords — observation
    "the lights went out and the alarm sounded",   # passive, not a command
    "i sent a message about the shopping list",    # 'message'+'shopping' — past tense
    "ring the timer when the alarm goes off",      # 'ring'+'timer'+'alarm' — description
    "the forecast says it will be cold tomorrow",  # 'weather' paraphrase, not a query
    "turn it up was the band's best album",        # 'turn up' ∈ VolumeKeyword — not a command
    "she set the timer and then went to bed",      # past tense narrative
    "the note said to call him back by noon",      # 'note'+'call' — reporting, not commands
    "they found the route on an old map",          # 'found'+'route' — narrative
    "he wrote down the directions to the shop",    # 'write'+'directions' — past tense
    "we get the alarm serviced every year",        # 'alarm' in factual context
    "the shopping channel was on all night",       # 'shopping' — noun, not list command

    # ── rhetorical / hypothetical — sound like commands but aren't ───────────
    "what would you do if the lights went out",    # conditional question
    "wouldn't it be nice to skip all the boring bits", # hypothetical, not a skip command
    "who even sets an alarm on a saturday",        # rhetorical
    "can you believe they cancelled the gig",      # 'cancel' — rhetorical question
    "imagine if you could just turn down the noise", # hypothetical
    "do you think it will rain at the weekend",    # opinion question, not weather command
    "i wonder what the time is in new york",       # musing, not a time query command

    # ── third-person / reported speech — describing others' actions ───────────
    "she asked him to call her back later",        # 'call' — reported request
    "they said the music was too loud at the party", # 'music' — reported complaint
    "my mum always sets three alarms just in case", # 'alarms' — describing habit
    "the kids wanted to play something different",  # 'play' — not a media command

    # ── entity-overlap no-match: overlapping keyword present, not a command ──
    "did anything turn up at the office",          # 'turn up' ∈ Volume/Heat
    "i had to turn down the invitation",           # 'turn down' ∈ Volume/Cool
    "the music just would not stop",               # 'stop'+'music' — narrative
    "it was stone cold by then",                   # 'cold' ∈ Weather/Cool — idiom
    "the hot topic was politics all evening",      # 'hot' ∈ Weather/Heat
    "they cancel each other out",                  # 'cancel' — idiom
    "he was dead set against the idea",            # 'set' ∈ SetKeyword — idiom
    "the heating engineer came round today",       # 'heating' ∈ Thermostat
    "kill the engine before you park",             # 'kill' ∈ Cancel/Off
    "her degrees were framed on the wall",         # 'degrees' ∈ Thermostat
    "i need to cool off after that argument",      # 'cool' ∈ Thermostat/Cool
    "the temperature of the debate rose",          # 'temperature' ∈ Weather/Thermostat
    "give the new hire a warm welcome",            # 'warm' ∈ Weather/Heat

    # ── nonsense ──────────────────────────────────────────────────────────────
    "blarg wump fizz",
    "one fish two fish red fish blue fish",
    "supercalifragilistic",
    "lorem ipsum dolor sit amet",
    "the mitochondria is the powerhouse of the cell",
]
