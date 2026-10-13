# Kalam promo · vertical script (9:16, 42 s)

Edit anything in this file: captions, sample messages, timing or the order of shots. Then send it back and I'll update the video.
Everything shown matches `KALAM.md`. The names and messages are sample text only.

**Format:** 1080×1920, 30 fps, no voiceover. Bilingual captions, with English on top and Arabic underneath (right to left).
**Music:** upbeat at 120 BPM (one bar = 2 s). There's a quiet build-up for 4 s, then the beat drops when Right ⌥ is pressed.
Every cut is a fast blurred swipe on the beat.

---

## 1 · Hook (0:00 – 0:08) · cream, then coral

| Time | What happens on screen | English caption | Arabic caption |
|---|---|---|---|
| 0:00 | An email window ("New Message", To: Sara, Subject: Campaign brief). Someone types slowly, with a typo: **"Hi Sr" → "Hi Sara,"** | Still typing? | لين الحين تكتب؟ |
| 0:03 | A big **Right ⌥ option** key drops in from the top | | |
| 0:04 | **DROP.** The key slams down, the screen shakes and coral fills the frame. The Kalam recording bar pops up with live sound levels | Hold **Right ⌥** and talk. | اضغط مطوّل على **⌥ اليمين** وتكلّم |
| 0:06 | Key released. The text springs into the email: **"Thanks for the update! Let's review the brief tomorrow at 10."** | Let go. It's typed. | تفكّه، وينكتب على طول |

**Sound:** soft key clicks → riser and snare roll → thud and boom on the drop → sparkle when the text lands.

## 2 · Any app (0:08 – 0:14) · sky blue

Four app cards swing in one after another. Each one shows the recording bar, then the text types in.

| Time | App | Text typed |
|---|---|---|
| 0:08 | Email · "Re: Final brief" | Attached is the final brief. Let me know what you think! |
| 0:09.6 | WhatsApp Web · "Mum" | واصل بعد 10 دقايق، جهّزي القهوة |
| 0:10.9 | Slack · "#marketing" | New captions are up in the shared folder. |
| 0:12.1 | Notes · "Friday shoot" | Ideas: launch reel, client brief, behind the scenes. |

Caption: **Works in any app.** / **يشتغل في أي تطبيق**

## 3 · Arabic + English (0:14 – 0:20) · deep blue

| Time | What happens on screen |
|---|---|
| 0:14.6 | Recording bar. A language switch (English · العربية) lands on **العربية** |
| 0:15.6 | Chat bubble, tagged "Arabic · عربي": **شحالج؟ نتلاقى الساعة 4 في الكوفي؟** |
| 0:16.3 | Recording bar again. The switch slides to **English** |
| 0:17.3 | Chat bubble, tagged "English · إنجليزي": **Perfect, see you at 4!** |
| 0:18 | Dialect chips bounce in: **خليجي Gulf** and **عُماني Omani** (highlighted), then **فصحى MSA**, **مصري Egyptian** and **شامي Levantine** |

Caption: **Arabic or English. It just knows.** / **عربي أو إنجليزي، يعرف بروحه**

## 4 · Smart touches (0:20 – 0:28) · warm sun

**4a (0:20 – 0:22.7)**: Changed your mind? / غيّرت رأيك؟
- Big words pop in on the beat: **"Meet at / 3, no wait, / 4"**
- "3, no wait," gets slashed out, then **✓ Meet at 4.** slams in

**4b (0:22.7 – 0:25.3)**: Say a shortcut. / قول الاختصار
- The real Kalam Shortcuts screen, zooming into the row **sign off → Best regards,**
- "YOU SAY · تقول: **"sign off"**" → **✓ Best regards,**

**4c (0:25.3 – 0:28)**: No ums. No uhs. / بلا «إمم» ولا «آه»
- **"Um, the brief is, uh, ready"**. "Um" and "uh" pop like bubbles, then **✓ The brief is ready.**

## 5 · Bilingual app (0:28 – 0:34) · sky blue

| Time | What happens on screen | Label |
|---|---|---|
| 0:28.3 | Real app screens are dealt in like cards, one per half-beat | Notes · الملاحظات → Clipboard · الحافظة → Your words · كلماتك → Shortcuts · الاختصارات |
| 0:29.9 | The English home screen slams on top | |
| 0:30.5 | | App language: English → **العربية** |
| 0:31 | The home screen does a 3D flip to the **Arabic** home screen (right to left, "اشرح بلا حدود" banner) | |

Captions: **Every screen, both languages.** / **كل شاشة، بالعربي والإنجليزي**
then **Arabic flips it right to left.** / **بالعربي، كل شي من اليمين لليسار**

## 6 · Privacy (0:34 – 0:37.5) · night blue

- A Mac drawing. A lock slams onto the screen, with pulse rings
- Three stamps, one per beat: **✕ No account · بدون حساب**, **✕ No subscription · بدون اشتراك**, **✕ No cloud · بدون سحابة**

Caption: **Everything stays on your Mac.** / **كل شي يبقى على جهازك**

## 7 · End card (0:37.5 – 0:42) · cream

- Megaphone banner "Write less, speak more.", which crossfades at 0:40 to the Arabic banner "اشرح بلا حدود"
- Kalam icon (pops in with a burst) and the Kalam wordmark
- **Write less, speak more.**
- **اشرح بلا حدود**
- Powered by Amira Hamood

**Sound:** half-time beat, a bell chord on the logo, then fade out.

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
