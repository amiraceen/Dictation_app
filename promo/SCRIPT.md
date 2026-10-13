# Kalam promo · vertical script (9:16, 60 s)

Edit anything in this file: captions, sample messages, timing or the order of shots. Then send it back and I'll update the video.
Everything shown matches `KALAM.md`. The names and messages are sample text only.

**Format:** 1080×1920, 30 fps, no voiceover. Bilingual captions, with English on top and Arabic underneath (right to left).
**Music:** upbeat but soft at 120 BPM: a round kick, shaker, rim clicks, echoing plucks and a warm pad. It's quiet for 5 s, then the groove comes in when Right ⌥ is pressed. Every scene change lands on a bar.
**Look (calm cut, `scenes-calm.html`):** minimal and clean. Scenes crossfade softly. Everything fades in while rising a little and settling out of a slight 3D tilt. Cards sway very gently in 3D and backgrounds slowly push in. Soft glows and a slow light sweep drift behind every scene for depth. No bounce, no shake.
**Backgrounds:** person writing (1), sky (2), banner blue (3), cream (4), soft sky (5), blue glow under a night tint (6), megaphone (7). The voice orb drifts blurred, at low opacity, in the background of scenes 2, 3, 4 and 6. The five app icons light up in scene 5.

---

## 1 · Hook (0:00 – 0:10) · cream, then coral

| Time | What happens on screen | English caption | Arabic caption |
|---|---|---|---|
| 0:00 | An email window ("New Message", To: Halima, Subject: Campaign brief). Someone types slowly, with a typo: **"Hi Halu" → "Hi Halima,"** | Still typing? | لين الحين تكتب؟ |
| 0:04 | A **Right ⌥ option** key glides in | | |
| 0:05 | The key presses down and a soft coral glow fills the frame. The Kalam recording bar appears in its place, with live sound levels | Hold **Right ⌥** and talk. | اضغط مطوّل على **⌥ اليمين** وتكلّم |
| 0:07.5 | Key released. The text fades into the email: **"Thanks for the update! Let's review the brief tomorrow at 10."** | Let go. It's typed. | تفكّه، وينكتب على طول |

**Sound:** soft key clicks → an airy swell → a soft thud as the groove starts → a gentle chime when the text lands.

## 2 · Any app (0:10 – 0:18) · sky blue

Four app cards fade in one after another, settling out of a slight 3D tilt. Each one shows the recording bar, then the text types in.

| Time | App | Text typed |
|---|---|---|
| 0:10 | Email · "Re: Final brief" | Attached is the final brief. Let me know what you think! |
| 0:12 | WhatsApp Web · "Mum" | واصل بعد 10 دقايق، تجهّزي |
| 0:15 | Slack · "#marketing" | New captions are up in the shared folder. |
| 0:17 | Notes · "Friday shoot" | Ideas: launch reel, client brief, behind the scenes. |

Caption: **Works in any app.** / **يشتغل في أي تطبيق**

## 3 · Arabic + English (0:18 – 0:26) · deep blue

| Time | What happens on screen |
|---|---|
| 0:19 | Recording bar. A language switch (English · العربية) lands on **العربية** |
| 0:20 | Chat bubble, tagged "Arabic · عربي": **شحالش؟ نتلاقى الساعة 4 في الكوفي؟** |
| 0:21 | Recording bar again. The switch slides to **English** |
| 0:22.5 | Chat bubble, tagged "English · إنجليزي": **Perfect, see you at 4!** |
| 0:23 | Dialect chips fade in: **خليجي Gulf** and **عُماني Omani** (highlighted), then **فصحى MSA**, **مصري Egyptian** and **شامي Levantine** |

Caption: **Arabic or English. It just knows.** / **عربي أو إنجليزي، يعرف بروحه**

## 4 · Smart touches (0:26 – 0:38) · warm sun

**4a (0:26 – 0:30)**: Changed your mind mid speaking? / غيّرت رأيك وانت تتكلم؟
- Big words fade in on the beat: **"Meet at / 3, no wait, / 4"**
- "3, no wait," gets struck through, then **✓ Meet at 4.** fades in

**4b (0:30 – 0:34)**: Say a shortcut. / قول الاختصار
- The real Kalam Shortcuts screen, slowly pushing in on the row **sign off → Best regards,**
- "YOU SAY · تقول: **"sign off"**" → **✓ Best regards,**

**4c (0:34 – 0:38)**: No ums. No uhs. / بلا «إمم» ولا «آه»
- **"Um, the brief is, uh, ready"**. "Um" and "uh" fade out and the gaps close up, then **✓ The brief is ready.**

## 5 · Bilingual app (0:38 – 0:46) · sky blue

| Time | What happens on screen | Label |
|---|---|---|
| 0:38.5 | Your five app icons fade in. Real app screens fade in one per half-beat, and the matching icon lights up | Notes · الملاحظات → Clipboard · الحافظة → Your words · كلماتك → Shortcuts · الاختصارات |
| 0:40.5 | The English home screen settles on top | |
| 0:41.5 | | App language: English → **العربية** |
| 0:42 | The home screen does a 3D flip to the **Arabic** home screen (right to left, "اشرح بلا حدود" banner) | |

Captions: **Every screen, both languages.** / **كل شاشة، بالعربي والإنجليزي**
then **Arabic flips it right to left.** / **بالعربي، كل شي من اليمين لليسار**

## 6 · Privacy (0:46 – 0:52) · night blue

- A Mac drawing. A lock fades onto the screen, with soft halo rings
- Three chips, one per beat: **✕ No account · بدون حساب**, **✕ No subscription · بدون اشتراك**, **✕ No cloud · بدون سحابة**

Caption: **Everything stays on your Mac.** / **كل شي يبقى على جهازك**

## 7 · End card (0:52 – 1:00) · cream

- The megaphone image fills the screen
- Kalam icon and the Kalam wordmark fade in
- **Write less, speak more.**
- **اشرح بلا حدود**

**Sound:** the beat thins out, a soft bell chord on the logo, then fade out.

---

### Where each thing lives (if you'd rather edit the code directly)

| To change… | Edit in `promo/scenes-vertical.html` |
|---|---|
| Captions | the `<div class="cap" …>` blocks; each has an `.en` and an `.ar` line |
| Typed messages (scene 2) | the `data-text="…"` on each card |
| The email text (scene 1) | `$("dict").dataset.text = …` in `init()`, and `SLOW` for the slow typing |
| Chat bubbles, dialect chips, results, end card | plain text in the HTML, in scene order |
| Scene timing | `SC` (scene start/end) plus the times inside `renderAt()` |

If you change timing, the sound-effect cues in `promo/music_vertical.py` need to move with it. I can do that for you.
Rebuild with `./promo/build.sh vertical` (about 15 min).
