# Groundnut long-form: "From Seed to Snack"

`groundnut_longform.mp4` is 1920x1080, 25 fps and 6:44 long. It is stored at crf 25 so it stays under GitHub's 100 MB limit. For a full-quality master, re-run the compile.

Build:
`python tools/compile_longform.py series/01-groundnut/longform/cuts.json OUT.mp4` (about 1 min; episode pieces are cached in `.pieces/`).

Order:
- Hook (new voice H1–H2) over the Ep 9 bowl shot, the Ep 10 pot close-up and the field view.
- Title card.
- Eps 1–10, each with its original voice and sound.
- Closing (new voice C1–C2) over the farm view.
- End card.

Cuts (exact ranges in `cuts.json`):
- Repeated "Pona episode-la…" recaps: Eps 3, 5, 6 and 7.
- Every "Adutha episode-la…" teaser.
- Ep 6's closing question, which Ep 7's opening repeats.
- Ep 10's "Vanakkam", subscribe line and goodbye, which the new closing replaces.
- The leading silences.

No music (owner's rule): nature bed only.

Publishing: credit the CC BY nature sounds (`assets/sound/nature/CREDITS.md`) and the voice reference (`assets/voice/CREDITS.md`).
