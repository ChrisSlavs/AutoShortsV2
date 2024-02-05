import re

regex = {"EMOJI": re.compile(u'([\U00002600-\U000027BF])|([\U0001f300-\U0001f64F])|([\U0001f680-\U0001f6FF])'),
         "ALPHANUMERIC": re.compile(r'\W+'),
         "NON_ASCII": re.compile(r'[^\x00-\x7F]+')}

elevenlabs_api = { "url"    : "https://api.elevenlabs.io/v1/text-to-speech/",
                   "voices" : {"Alex": "hKULXlJp90RYPLVAaOJI"}, 
                   "headers" : {"Accept":"audio/mpeg",
                              "Content-Type":"application/json",
                              "xi-api-key":""},
                    "data"  : {"model_id": "eleven_monolingual_v1",
                               "text": "",
                               "voice_settings": {
                               "stability": 0.82,
                               "similarity_boost": 0.75,
                               "style": 0.0,
                               "speaker_boost": False}},}