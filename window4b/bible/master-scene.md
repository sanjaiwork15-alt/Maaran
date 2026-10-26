# Window 4B – Master Scene (permanent reference)

**Locked image:** `window4b/assets/master/window4b_master_v1.png` (1672 × 941, 16:9, golden hour, made on seaart.ai).
Every episode uses this exact camera, window, bridge, river, buildings, roads and foreground objects.
Only weather, environment, lighting and world conditions change. No zoom, pan, tilt or perspective change.

This file **replaces the "world" section of `channel-bible.md`** (that section describes an older street/opposite-building
design – see "Conflicts with the channel bible" below).

## Composition

**A. Foreground – inside Flat 4B:** wide wooden sill across the bottom; leafy potted plant far left; plain ceramic mug
beside it; small stack of books far right; thick wooden frame with curtains on both sides.
*Purpose: small, intimate changes as time passes.*

**B. Middle ground – riverfront and bridge:** broad river across the scene; large concrete bridge left to right; two-way
road lower left; trees, pavement, benches, bus shelter and streetlights along the river; a few vehicles on road and bridge.
*Purpose: main action area (flooding, abandoned traffic, overgrowth, snow…).*

**C. Background – skyline:** many office towers of varied heights; smaller buildings in the gaps; prominent glass office
building on the right edge; distant skyline to the horizon; wide sky with layered clouds and a low setting sun.
*Purpose: big-city feel and a canvas for long-term change.*

## Landmark map (fixed positions)

Approximate boxes measured on the v1 image, as % of width (x) and height (y) from the top-left. Use them to place
change layers and to check that a regenerated master still matches.

| Landmark | x % | y % | Storytelling use |
|---|---|---|---|
| Window frame + curtains | 0–13 and 96–100 | full height | Identifies the channel instantly |
| Sill | 0–100 | 79–100 | Snow, dust, water on the sill |
| Potted plant | 0–16 | 59–88 | Wilting, growing, freezing, flooding |
| Ceramic mug | 18–26 | 76–89 | Fills with rain, dust or snow |
| Books | 75–93 | 87–100 | Water damage, dust, decay |
| Near-left balcony building | 10–19 | 3–79 | (in image, not in spec) |
| Bridge deck / piers | 18–64 | 44–49 / to 55 | Traffic, flooding, decay, vegetation |
| River | 29–86 | 51–74 | Rising, freezing, drying, overflowing |
| Riverside trees | 22–64 | 52–80 | Seasons, overgrowth |
| Road | 25–47 | 61–81 | Abandoned vehicles, vegetation, water |
| Bus shelter | 43–50 | 68–77 | Flood-depth marker, overgrowth |
| Glass office tower | 86–96 | 0–79 | Lights out, damage, vines |
| Distant skyline | 18–86 | 5–45 | Weather, darkness, city-wide change |
| Sun | 76–80 | 31–36 | Day/night, endless dark, extreme weather |

Also present but not in the spec: a chair back at the bottom left (4–35 %, 88–100 %), a second small plant and a
pen holder at the bottom right (86–100 %, 67–97 %). Decide whether they are permanent too.

## Layers

1. Sky, sun, clouds · 2. Distant skyline · 3. Near and opposite buildings · 4. River, bridge, reflections ·
5. Road, vehicles, trees, street furniture · 6. Window frame, curtains, sill · 7. Plant, mug, books ·
8. Optional characters/animals · 9. Weather effects, time counter, captions

## Making scenarios readable

Each scenario must change at least two or three big areas, not tiny details:
- **Endless rain:** river rises, riverside goes under, bridge piers submerge, lower floors flood.
- **Everyone disappears:** traffic stops, bridge empties, plants take the road, vines cover the glass tower.
- **One year of snow:** snow builds on roofs, bridge, riverbank and the sill.
- **Electricity never returns:** towers and streetlights go dark, bridge lights out, a few candlelit windows.

## Art direction

- 2D illustration, clean outlines, simple shapes, soft shading.
- Golden-hour sunset is the base lighting; each episode may move to its own lighting.
- Fixed camera from inside Flat 4B. Never move landmarks; change them through separate layers.
- Bridge, river, nearby buildings and road must be big enough that changes read on a phone.
- Characters optional and secondary; the landscape is the subject.
- Large shapes and strong silhouettes over tiny windows, vehicles and decoration.

## Master prompt (for recreating / refining the base art)

> **WINDOW 4B — MASTER ENVIRONMENT REFERENCE**
>
> Create a highly detailed, hand-drawn 2D animated cityscape viewed from inside a spacious apartment through one very
> large, wide wooden window.
>
> **Composition:** A panoramic modern city at golden hour, with tall office skyscrapers, layered residential buildings,
> a broad reflective river, a prominent concrete bridge crossing the river, and a tree-lined riverside road with
> benches, streetlights and a bus shelter.
>
> **Foreground:** A large wooden window sill across the bottom, a leafy potted plant on the left, a plain ceramic mug
> near the left-centre, and a small stack of books on the right. Simple curtains and a thick wooden window frame
> surround the scene. No text or labels on any objects.
>
> **Middle ground:** The river and bridge are large, clearly visible, and close enough to the viewer that future
> environmental changes will be easy to see. The road, trees, bridge supports and riverbank have distinct shapes and
> clear outlines.
>
> **Background:** Numerous tall glass office towers of varied heights, smaller buildings between them, a warm
> orange-pink sky, layered clouds and a setting sun. A prominent modern glass building stands at the right edge.
>
> **Art direction:** Beautiful, polished 2D animation background, clean outlines, readable silhouettes, soft painterly
> shading, warm sunset lighting, rich but controlled colours, detailed yet uncluttered composition.
>
> **Production requirements:** Fixed camera, stable geometry, no extreme perspective distortion, no close-up
> characters, no crowded foreground, no logos, no text, no watermarks. Design the artwork as a reusable master
> environment for future episodes in which weather, water levels, vegetation, lighting and the condition of buildings
> can change while the camera and landmark positions remain identical.
>
> **Canvas:** 3840 × 2160, 16:9. Keep the major environmental landmarks in the central composition so a vertical 9:16
> crop can be produced from the same artwork.

## Open issues with v1 (found on review, 26 Oct 2026)

1. **9:16 centre crop loses the channel identity.** A centred 9:16 crop keeps only x 34–66 %
   (`v1_centre_crop_916_check.png`): no window frame, no plant, no mug, no books, no glass tower, no sun. The lower
   fifth is an empty sill. Options: (a) a separate vertical master drawn from the same viewpoint, (b) recompose the
   16:9 master with the landmarks pulled toward the centre, or (c) an off-centre or panned crop – but (c) breaks the
   "no pan" rule.
2. **Resolution:** v1 is 1672 × 941, not 3840 × 2160. Upscale (Real-ESRGAN) or regenerate at full size before
   drawing change layers on top, or every layer will be built on a soft base.
3. **Sun has a notch** cut out of its lower edge (AI artifact) – fix when cleaning up.
4. **Flattened image, no layers.** The layer list above has to be cut out by hand or regenerated per layer.
5. **Licence:** confirm seaart.ai's terms allow commercial use on a monetised channel.

## Conflicts with the channel bible (`channel-bible.md`) – decide which wins

| Bible says | Master scene shows |
|---|---|
| Street below with tea/snack stall, lamp post, big tree, parked **yellow car** | Riverfront road; no stall, no yellow car |
| Building opposite with windows **2A, 2B, 3A, 3B** and a rooftop water tank | Skyline and towers far away; no readable neighbour windows |
| Residents Mr Bose (2A), Kim family (3B), Tara (stall) | Nowhere to place them at a readable size |
| Sill: plant, **cracked** mug, **wall calendar** | Plant, **plain** mug, books; no calendar |
| "Calm and cosy" flat 2D, soft colours, simple shapes | Highly detailed, painterly, busy skyline |
| Mix of Asian and Western details ("placeless") | Reads as a Western downtown |
| Tiny "4B" easter egg and hidden cat each episode | No place defined yet |

The residents and the yellow car were the bible's main differentiators against AI-template channels; the master scene
spec makes characters optional. That is the biggest decision to confirm.
