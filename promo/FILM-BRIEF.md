# Kalam Intro Video: Project Summary and Handoff

## 1. The task

Make a short vertical (9:16) video that introduces **Kalam**, the private, on-device Arabic and English voice-to-text app for Mac ("Write less, speak more." / "اشرح بلا حدود").

Pipeline: **still images first → storyboard → image-to-video.**
One location, one person, one computer setup. Minimal. It should look like a film still, with grain.

## 2. Story (about 26 seconds)

A man works at a laptop. He types, mistypes and stalls. He finds Kalam, holds Right Option ⌥, speaks, releases, and the text appears. Then a short beat per feature, then freeze cuts where the person changes in exactly the same frame.

Features to show (all from the README):
- Say as much as you want, with no need to type it all
- Hold one key, speak, let go
- "Scratch that / no wait" corrections
- Private: speech is processed on the Mac, nothing is uploaded
- Free: no account, no subscription
- Bilingual, with dialects: Arabic (Gulf, Omani, Egyptian, Levantine) and English

I avoided claiming anything specific about "light" on memory or CPU, since the README doesn't say it. "Stays out of your way" is the safer caption.

## 3. The settled look (final)

**Plate B: high-key silhouette on the brand gradient.**

| Item | Locked value |
|---|---|
| Frame | Vertical 9:16, mid shot, 70mm full-frame-equivalent lens look, about 1.5 m behind the man, about 20 cm above seated head height, looking slightly down |
| Angle | Back shot, 35° off the line from the laptop through his back. We see mostly his back and the back of his head, and the screen at about 35° from face-on |
| Backdrop | Seamless vertical gradient: pale sky blue #C9D7E6 → near-white #F4F0EE → pale peach-blush #F6DDD3, bright and airy, fine grain. No glow, no bands |
| Man | Late 20s, short black hair, short trimmed beard, rendered as a near-total ink-navy (#14212E) silhouette, about 3 stops underexposed, **no fill light**, thin soft edge light on headwear and shoulder |
| Headwear (Omani) | **Massar**: dark charcoal wool turban, horizontal pleated layers around a kumma base, short frayed tail behind the left ear. This was changed by edit from the original embroidered kumma |
| Garment | Loose long-sleeved charcoal-navy dishdasha, plain round neckline, **exactly one furakha** at the front of the neck, hidden from this angle. Nothing else hangs on the garment |
| Chair | Matte black steel desk chair, slim flat backrest between the camera and his lower back, flat seat, four thin round legs, no wheels or armrests |
| Laptop | 13-inch silver aluminium, thin black bezel, black keyboard, lid about 110°, no logo, pale screen with one small orange-coral (#EE7A4A) accent, no legible text |
| Desk | Plain matte black powder-coated steel slab, 3 cm thick, cropped cleanly at the right edge, one plain square leg, no hardware |
| Foreground | Out-of-focus dark-teal plant (#1F5A66) in the bottom-right corner, about 85% opacity, never touching the desk leg or his thigh |
| Cards | **Removed.** Floating frosted UI cards are added in post when needed. The gradient above the laptop is kept empty for them |

### Positions (% across, % down, measured from the approved render)

| Element | Position |
|---|---|
| Empty gradient above head | 0–40% down |
| Headwear | 25–48% across, 40–48% down |
| Back and shoulder | Bleeds off the left edge from about 58% down |
| Hands | 57–77% across, 73–77% down |
| Laptop | 67–94% across, 64–79% down |
| Desk top | From about 49% across to beyond the right edge, top surface 75–87% down; leg at 76–81% across |
| Chair backrest | 8–42% across, 82–92% down |
| Foreground plant | 58–100% across, 84–100% down |

Positions come from the render at the time of approval. Re-check them against your edited massar version.

## 4. Tools

| Stage | Tool |
|---|---|
| Image model | **Google Nano Banana 2**, used inside **Magnific** |
| Image workflow | Generate the master plate once (done and approved), then do everything else with **Magnific's edit feature** (mask → edit prompt), so the camera, laptop, desk, chair and backdrop never drift |
| Video | Image-to-video from each approved still (Magnific video models; one camera move per clip) |
| Post | Composite the real Kalam UI on the screen, add the pop-up cards, captions and the end card |
| Brand assets | In the project files: `logo_1-100.jpg`, `Asset_*.jpg` banners, `bgs.pdf` gradients, the palette image, and the app screenshots |

**Reference guides used:** the focal-length guide (framing → focal length → what must stay visible → action → camera movement; dolly vs. zoom) and the style library (Looks 3, 4 and 5 were considered before the high-key silhouette was chosen).

## 5. Magnific connection status (what is still open)

**The goal is to run the whole set through the Magnific MCP.** As of the last attempt it was not connected:

- The connector directory search for "Magnific" and "Freepik" returned nothing in that chat.
- The Claude in Chrome extension was not reachable as a fallback.

To continue, either:
1. Attach the Magnific connector to the chat (Settings → Connectors → make sure it is on for the conversation), or
2. Install and sign in to the Claude in Chrome extension and open the Magnific generation with the approved plate in a tab: https://chromewebstore.google.com/detail/fcoeoabgfenejglbffodgkkbkcdhcgfn

Each generation uses credits, so confirm the count before the run.

## 6. Images to generate

**Total: 9 new images** (8 if you skip the Wi-Fi insert), plus the approved plate. That makes 10 stills in the sequence.

| # | Beat | Type | New image? | Mask | Motion |
|---|---|---|---|---|---|
| 1 | Typing | Approved plate (massar version) | Already done | none | Slow dolly in |
| 2 | Stall, hands lift | Edit | **Yes** | hands, forearms | Locked |
| 3 | Finds Kalam, screen glows | Edit | **Yes** | screen, right hand | Locked |
| 4 | Presses Right ⌥ (macro finger) | New generation, plate as reference | **Yes** | none | Locked |
| 5 | Releases, text fills the screen | Edit | **Yes** | screen, hands, upper torso | Locked |
| 6 | "Scratch that" | Reuse #5, change the screen in post | No | n/a | Slow dolly in |
| 7 | Private: Wi-Fi off, still dictating | New insert (optional, or composite the real icon) | **Yes** | none | Static |
| 8 | Free, relaxed | Edit | **Yes** | torso, arms | Slow dolly back |
| 9a | Khaliji | Person swap of #1 | **Yes** | person only | Same slow scale-in on all four cuts |
| 9b | Levantine | Person swap of #1 | **Yes** | person only | (same) |
| 9c | English | Person swap of #1 | **Yes** | person only | (same) |
| 9d | Omani | The approved plate itself | No | n/a | (same) |
| 10 | End card | Brand banner or logo art | No | n/a | none |

Count: edits #2, #3, #5, #8 = 4; new generations #4 and #7 = 2; swaps = 3. Total 9.

## 7. Prompts

### 7.1 Lock line (add to the end of every edit)

```
Keep the camera position, height and 35-degree angle, the framing, the black steel desk chair, the silver 13-inch laptop, the matte black desk slab with its single leg, the blurred teal plant in the bottom-right corner, the gradient backdrop, the headwear, the dishdasha and the silhouette exposure exactly as they are. Change only what is described above. No fill light on the person. The furakha appears once, at the neck, on the Omani look only. Do not add or replace any objects.
```

### 7.2 Master plate prompt (to regenerate if needed)

Use the Omani headwear below as the massar, matching the edited version.

```
Clean high-key editorial photograph, full-frame digital camera, soft diffused light, low contrast, fine film grain. Vertical 9:16. Medium shot with a 70mm full-frame-equivalent lens look, shot from behind: the camera is about 1.5 m behind the man and about 20 cm above his seated head height, looking slightly down, positioned 35 degrees off the line that runs from the laptop through his back. We see mostly his back and the back of his head, with his shoulders turned about 35 degrees toward the laptop. One consistent perspective for the man, chair, laptop and desk. The top 40% of the frame is empty gradient.

A man in his late twenties with short black hair and a short trimmed beard sits at the left of the frame, facing right toward a laptop. His headwear sits at about 25 to 48% across and 40 to 48% down. His back and shoulder bleed off the left edge from about 58% down. Only the dark contour of his cheek and beard shows at the inner edge of his head, with no readable facial features.

He is a deep ink-navy (#14212E) near-total silhouette, strongly backlit and underexposed by about three stops with no fill light on him: no readable skin tone, a soft tonal falloff from slightly lifted charcoal-navy at the upper shoulder to near-black at the lap, faint fabric folds only, and a thin soft edge of light tracing his headwear, hair line and shoulder.

HEADWEAR: a dark charcoal wool massar, a turban wrapped in horizontal pleated layers around a kumma base, with a short frayed tail hanging behind the left ear.

DISHDASHA: a loose long-sleeved charcoal-navy dishdasha with a plain round collarless neckline and exactly one furakha, a short black cord tassel about 12 cm long attached at the front of the neckline and hanging on his chest, hidden from this rear angle apart from at most a tiny black tip beside his jaw. No cord, tassel, button, pocket or trim appears anywhere else on the garment.

CHAIR: he sits on a minimal desk chair in matte black powder-coated steel. From our rear view, its slim flat backrest panel, 4 cm thick, about 30 cm wide and 22 cm tall, stands between the camera and his lower back, partly covering the small of his back and hips, at about 8 to 42% across and 82 to 92% down. It is held on two thin vertical posts and has a flat seat beneath him and four thin 2 cm round-tube legs, two of which are visible at the bottom of the frame at about 52 to 60% across. No wheels, armrests, headrest or swivel base. A thin soft rim of light runs along the top edge of the backrest.

LAPTOP: both his hands rest on the keyboard of a 13-inch silver aluminium laptop with a thin black bezel and a black keyboard, lid open about 110 degrees, no visible logo, the hands at about 57 to 77% across and 73 to 77% down and the laptop at about 67 to 94% across and 64 to 79% down. The laptop sits farther from the camera than the man, with its screen facing him, so we see the front of the screen at about 35 degrees from face-on, never the back of the lid. The screen is a pale window with one small orange-coral (#EE7A4A) accent and no legible text.

DESK: a plain rectangular slab of matte black powder-coated steel, 3 cm thick, seen from slightly above, with its top surface at about 75 to 87% down, running from beneath his forearm at about 49% across to beyond the right edge of the frame, where it is cropped cleanly, supported by one plain square 5 cm leg at about 76 to 81% across from the underside of the slab to the bottom edge. No brackets, hardware, drawers or cable trays are visible.

FOREGROUND: in the bottom-right corner only, a leafy dark-teal plant (#1F5A66) sits very close to the camera, so heavily out of focus that it reads only as a soft dark-teal shape with a hint of leaf edge, no veins and no sharp edges, at about 85% opacity, covering about 58 to 100% across and 84 to 100% down, never touching the desk leg or his thigh. The man and laptop stay sharp.

BACKDROP: a seamless smooth vertical gradient with no horizon, wall or floor line: pale sky blue (#C9D7E6) at the top, melting through near-white (#F4F0EE) in the middle into pale peach-blush (#F6DDD3) at the bottom, bright and airy and slightly overexposed, very fine grain, no glow and no diagonal bands.

Nothing else in frame: no cards, objects, text, decor, logos or other people. Quiet, still, no CGI look.
```

### 7.3 Edit prompts (mask as listed, then add the lock line)

**Shot 2, stall (mask hands and forearms)**
```
Both of his hands have lifted about 5 cm above the keyboard and hover over it, fingers slightly curled, as if he has stopped mid-thought. His head tilts down by about 3 degrees. His shoulders drop slightly. The screen stays a pale window with the small orange-coral accent. Keep his torso position unchanged.
```

**Shot 3, discovery (mask screen and right hand)**
```
His right hand has moved to the trackpad, and his left hand rests beside the keyboard. The laptop screen glows slightly brighter, with a small rounded pale window open in its centre and the orange-coral accent larger, about three times its previous size, no legible text. A thin warm coral edge of light touches the knuckles of the hand on the trackpad. Keep his torso position unchanged.
```

**Shot 5, release (mask screen, hands and upper torso)**
```
He has just let go of the keyboard: both hands hover about 8 cm above it, palms down and relaxed, and his upper body leans back by about 5 degrees, with his head slightly raised. The laptop screen is now filled with several pale horizontal lines of soft grey bars, like a block of text, no legible words, with the small orange-coral accent at the bottom edge. Keep his seat position unchanged.
```

**Shot 8, free and relaxed (mask torso and arms)**
```
He leans back into the chair with both hands clasped behind his head, elbows out. The backrest of the chair stays visible, the laptop screen stays as a pale window with the small orange-coral accent, and the silhouette exposure stays the same. Keep the seat position unchanged.
```

### 7.4 New generations (attach the approved plate as a reference)

**Shot 4, the finger on Right Option (macro)**
```
Extreme close-up, low-angle macro photograph, 100mm macro full-frame-equivalent lens look, camera at desk height about 15 cm from the keys, looking along the keyboard from the front right with a 20 degree tilt. Frame the tip and last joint of the right index finger pressing the key immediately left of the arrow-key cluster, one key to the right of the right command key, on the bottom row of a black laptop keyboard. Keep the whole fingertip and the whole pressed key visible, plus the keys on either side of it. The key is pressed down about 2 mm and glows soft orange-coral (#EE7A4A) from beneath, with keycap legends too small to read. The hand is a dark silhouette in warm brown skin, backlit, with a thin soft edge of light along the finger and no fill light on it. A cuff of charcoal-navy dishdasha is just visible at the edge of the frame. The silver aluminium edge of the 13-inch laptop is visible at the bottom. Shallow depth of field: the key and fingertip sharp, everything else softly blurred. Behind the keyboard, the laptop screen is a pale blurred window, and beyond it the seamless gradient backdrop, pale sky blue (#C9D7E6) at the top melting through near-white into pale peach-blush (#F6DDD3). Fine film grain, bright and airy, soft low-contrast light. Nothing else in frame: no face, no text, no logos. Quiet, still, no CGI look.
```

**Shot 7, private insert (optional; or composite the real Wi-Fi-off icon in post)**
```
Close-up from behind and slightly above, 135mm full-frame-equivalent lens look, of the open laptop screen filling most of the frame. At the left edge, his dark silhouetted shoulder and the edge of his massar are out of focus. The screen is a pale window with a slim system bar along its top edge showing small icons, one of which is a wireless symbol crossed by a diagonal slash, and a slim dark pill with a few small vertical bars at the bottom centre, no legible text. The backdrop beyond is the same pale sky-blue to peach-blush gradient. Fine film grain, bright, soft light.
```

### 7.5 Person swaps (edit the approved plate, mask the person only)

Start every swap with:
```
Replace the man with [LOOK]. Keep his exact pose and position, both hands on the keyboard, the chair, desk, laptop, plant and backdrop unchanged. Keep the silhouette exposure: no fill light, near-total deep ink-navy, thin edge light on the headwear and shoulder. No furakha on this look.
```

| Look | `[LOOK]` | Screen line (suggested; have a native speaker check the dialect) |
|---|---|---|
| Omani (the plate itself) | n/a | `وين إنت؟ أنا جاي الحين` |
| Khaliji | a man in a dark charcoal ghutra with a black agal and a dark charcoal kandura, short trimmed beard | `وينك؟ أنا جاي الحين` |
| Levantine | a man with dark wavy hair, light stubble and a dark charcoal wool crewneck, no headwear | `وينك؟ أنا جاي هلأ` |
| English | a man with short light-brown hair, clean-shaven, in a dark navy collared shirt, no headwear | `Running ten minutes late, start without me.` |

Clothing is kept dark so the silhouette holds against the gradient. A white ghutra would disappear into the near-white middle of the backdrop. The swaps follow the focal-length guide's rule of changing only one thing: same camera, same position, same pose, so only the person changes.

### 7.6 Motion prompts (image to video)

Use one move per clip. Dolly is a physical camera move, not a zoom.

**Locked (shots 2, 3, 4, 5 and the swaps)**
```
Medium shot from behind, 70mm full-frame-equivalent lens look. Keep his head, both shoulders and both hands visible. His hands rest on the keys, then his right hand lifts toward the bottom-right corner of the keyboard. Subtle breathing. Restrained handheld movement from a fixed camera position. No zoom or camera travel.
```

**Slow dolly (shots 1 and 6)**
```
Medium shot from behind, 70mm full-frame-equivalent lens look. Slow dolly in: the camera physically moves forward about 20 cm over the clip. Keep his head, both shoulders and both hands on the keyboard in frame throughout. No zoom.
```

Shot 8 is the same dolly in reverse (slow dolly back). For the four freeze cuts, apply the same slow scale-in in post across all of them so they read as one continuous move.

## 8. Post-production

- **Screens:** composite real Kalam screen recordings or screenshots onto the laptop in shots 3, 5 and 6. For the four swap cuts, use the dialect lines above (RTL layout for the Arabic ones). Never rely on the AI to render the UI text.
- **Cards:** add the frosted pop-up cards on shots 5 and 6 in the reserved empty gradient above the laptop.
- **Captions:** *Meet Kalam.* / *Hold. Speak.* / *Let go. Done.* / *Say it your way.* / *Private. Stays on your Mac.* / *Free. No subscription.* / *Arabic. English. Every accent.*
- **End card:** brand banner or `logo_1-100.jpg` on a `bgs.pdf` gradient, with *Write less, speak more.* and the Arabic *اشرح بلا حدود*. The Arabic tagline is not a direct translation of the English one, so keep them as a pair.

## 9. Brand palette (matched by eye in the palette file; color-pick exact values from `bgs.pdf` if you need them)

Coral #EE7A4A · Amber #EDB04C · Sky #5B9BD6 · Navy #2D5A96 · Teal #2E8393 · Ink #14212E · Cream #F7F0EB · Blush #F6DDD3 · Mist #C9D7E6 · Banner top #38608F · Banner bottom #6389BC · Night #0F1D33

## 10. Rules that have to hold in every image

1. Never regenerate a shot from scratch when it can be an edit. Edits keep the camera, laptop, desk, chair and backdrop identical.
2. Mask only what changes (the person, hands, or screen).
3. Keep the silhouette exposure: no fill light on the person, with only a thin edge light.
4. One furakha, at the neck, on the Omani look only. Nothing hangs below the collar.
5. No legible text generated on any screen. Composite it in post.
6. The foreground plant stays in the bottom-right corner and does not touch the desk leg or his thigh.
7. If a pose edit makes the framing drift, mask less and describe the change in smaller steps.

## 11. Next steps

1. Connect the Magnific MCP to the chat (or install the Chrome extension) so the edits can be run directly.
2. Confirm the credit count (9 new images).
3. Run the edits in this order: 2 → 3 → 5 → 8, then the swaps, then shots 4 and 7.
4. Review each still against section 3 before animating.
5. Animate each approved still, then assemble in post.
