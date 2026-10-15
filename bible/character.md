# Maaran Thatha – Character Bible

This file is the single source of truth for the character. Every script and every video must match it.

## Look (locked to the owner's 2D cartoon art in `assets/2d/source/`: `01_front.png` and the head, hands, poses,
turnaround and sitting sheets; flat 2D cartoon style with clean dark outlines and soft shading)

| Element | Detail |
|---|---|
| Age | Around 70 |
| Hair | Thick white hair, combed back |
| Face | Warm brown skin, bushy white eyebrows, big kind eyes, curled white moustache, full white beard |
| Shirt | Cream/off-white half-sleeve cotton shirt, one chest pocket, buttons down the front |
| Towel | Green cotton "thundu" on his LEFT shoulder, white stripes and fringe at the end |
| Veshti | White veshti with a thin green border |
| Footwear | Brown leather slippers |
| Prop | Wooden walking stick, always in his RIGHT hand |

Never change his outfit within a series. Seasonal extras (e.g. a head towel for the hot sun) are only added if the script says so.

## Personality

- A real farmer with 50+ years in the soil, not a TV presenter.
- Warm, funny and a little mischievous, like the thatha who teases you and then teaches you.
- Proud of farming and respectful of the land ("Mannu thaan namba saami").
- Patient: he explains the "why", not just the "what".
- Honest: if something can go wrong in farming, he says so. He never exaggerates.
- He talks directly to the viewer as if they were his grandchild ("kanna", "raasa", "en peran/peththi").

## How he talks (Tanglish in the scripts)

- Short, spoken sentences. No textbook words when a village word exists.
- Rural North Tamil Nadu flavour that everyone in Tamil Nadu understands.
- Favourite words and fillers: "Paaru kanna", "Enna theriyuma?", "Adhu thaan vishayame!", "Aiyo", "Saami", "Seri seri", "Hmm…", "Ennaanga!".
- He asks the viewer questions, then answers them with a twist.
- Comedy comes from village life: the crow that steals seeds, his own knee pain, the neighbour who always copies him, etc.
- Numbers are said the farmer's way first ("oru adi idaivelai"), then the exact value if needed ("30 centimetre").

## Catchphrases (use where it fits, not in every episode)

- **Opening:** "Vaanga vaanga! Ennoda peru Maaran Thatha… iniku namba ena pana porom nah…!"
- **Wisdom line:** "Mannu pesaadhu kanna… aana paathu purinjikittaa, ellaam sollum."
- **Sign-off:** "Adutha episode la paappom… poitu vaanga!"

## Voice (locked)

- Reference: `assets/voice/thatha_ref.wav`, one 12-second clip the owner made in Google AI Studio (Gemini TTS, "Charon" voice; prompt in `assets/voice/README.md`).
- Engine: AI4Bharat IndicF5 (MIT, free), which speaks every new line in the reference voice: `tools/f5_voice.py`. No post-processing.
- The same reference for every episode. Never change it mid-series.
- Expression comes from the reference clip and punctuation: "..." gives a pause, "?" and "!" lift the line. Stage directions like *(chuckles)* are not spoken by the engine; for real chuckles or whispers, use a short extra reference clip in the same Charon voice for that line.
- Talking scenes are animated from the voice (Wan 2.2 S2V), so he lip-syncs to every line.

## Golden rules

1. Farming information must be correct. Every fact in a script is checked against TNAU (Tamil Nadu Agricultural University) or Government of Tamil Nadu sources and listed in the episode's fact-check section.
2. No fake miracle claims, no fake medical claims.
3. Every episode opens with a hook in the first 3 seconds and ends with a cliffhanger into the next one.
4. No on-screen text in the videos.
