# Thatha action library (owner 2026-11-02)

**Update (same day): owner – "I want you to code and animate these shots".** No GPU: `tools/toon/body.py` bends the
owner's ONE front drawing with soft overlapping region weights (feet, veshti hem, free arm, head; the stick stays
rigid in his hand) and a smooth displacement field solved for the destination (fixed-point inverse) – no cut
pieces, no visible joints. First action: `walk_front` (seamless 1.1 s two-step cycle). Test:
`tests/walk_front_courtyard.mp4` (walking towards the camera in the courtyard). Lessons: bending the stick smeared
it (keep props rigid); a region mask must exclude cloth but keep the limb's outlines; big swings need the inverse
warp or the outlines ghost.

---
Original GPU plan (kept for reference):

Owner: no paid GPU, no card ("We'll create some walking, other shots once and use it for future").
Plan: spend the free GPU time (Modal Starter without a card = $1/month; Lightning AI free tier as the bigger,
no-card option) ONCE on a library of short Wan 2.2 image-to-video clips of Thatha on a plain background, cut out
per frame (rembg) and reused in every episode on any location (code backgrounds, camera moves, talk.py faces).

Priority list (5 s each, plain light background, the owner's front/turnaround art as the start frame):
1. Walk cycle, side view, left -> right – cut to a seamless 2-step loop (reused with a scrolling background).
2. Walk towards the camera (front).
3. Sit down on a step / stand up.
4. "Vanakkam" greeting / wave.
5. Pointing that moves (look over there).
6. Big laugh, hand on belly.
7. Drinking from a steel tumbler.
8. Bend down and pick something up.
9. Thinking: hand on chin, head tilt.
Each clip gets 2 seeds only if the first has hand/face glitches (check every frame, CLAUDE.md rules).
Status: waiting for MODAL_TOKEN_ID / MODAL_TOKEN_SECRET in the environment + modal.com hosts allowed.
