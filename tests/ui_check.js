// Clicks every button, toggle, menu and form in web/index.html and checks each one sends
// the right message to the app and updates the page. Runs in Chromium with a fake app.
//
//   NODE_PATH=$(npm root -g) node tests/ui_check.js [chromium path]
//
// Prints one line per check and exits non-zero if any fail.

const { chromium } = require('playwright');
const path = require('path');

const HTML = 'file://' + path.join(__dirname, '..', 'web', 'index.html');
const now = Date.now() / 1000;
const note = { id: 'a1', title: 'Weekly sync', body: 'Decisions', created: now - 900, updated: now, meeting: true,
  duration: 754, recording: false, transcript: [{ t: 0, text: 'Okay, let us start.' }] };
const base = () => ({
  glass: false,
  history: [{ ts: now - 86400 * 3, text: 'Older one', words: 2, secs: 1 },
            { ts: now - 3600, text: 'First thing I said', words: 4, secs: 2 },
            { ts: now - 60, text: 'وين صرت؟', words: 2, secs: 1 }],
  dictionary: ['Kalam', 'مسقط'], snippets: { 'my email': 'a@b.c', 'sign off': 'Best,' },
  stats: { words: 1234, wpm: 140, streak: 3 },
  settings: { dictation_language: 'auto', speech_model: 'small', launch_at_login: false, show_bar_always: false,
    show_in_dock: false, sounds: true, mute_while_dictating: false, pause_media_while_dictating: false,
    ui_language: 'en', dictation_key: 61 },
  key_label: 'Right ⌥',
  options: { dictation_key: [[61, 'Right ⌥'], [54, 'Right ⌘'], [63, 'Fn 🌐'], [96, 'F5']], ui_language: [['en', 'English'], ['ar', 'العربية']], dictation_language: [['auto', 'Arabic or English (auto)'], ['ar', 'Arabic'], ['en', 'English']],
    speech_model: [['small', 'Fast · built in'], ['turbo', 'Accurate · 1.6 GB download']] },
  notes: [{ id: 'a1', title: 'Weekly sync', created: now - 900, meeting: true, duration: 754, recording: false, preview: 'Decisions' },
          { id: 'b2', title: 'Groceries', created: now - 86400 * 3, meeting: false, duration: 0, recording: false, preview: 'Milk' }],
  note, goto: null,
  model: { choice: 'turbo', active: 'Whisper small', error: 'No internet', ready: false },
  voicetest: { phrases: [{ id: 'gulf-1', dialect: 'Gulf', text: 'وين صرت؟', secs: 2, recorded: true },
                         { id: 'msa-1', dialect: 'MSA', text: 'شكرا', secs: 0, recorded: false }],
               results: null, recording: null, rec_started: null, running: null, model: 'Whisper small', language: 'auto' },
});

let fails = 0;
const check = (name, ok, detail = '') => { if (!ok) fails++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${ok || !detail ? '' : '  → ' + detail}`); };

(async () => {
  const browser = await chromium.launch({ executablePath: process.argv[2] || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const errors = [];

  async function open(mode = 'main', state = base(), colorScheme = 'light') {
    const p = await browser.newPage({ viewport: { width: 1000, height: 700 }, colorScheme });
    p.on('pageerror', e => errors.push(e.message));
    await p.addInitScript(([s, mode]) => {
      window.__sent = [];
      window.webkit = { messageHandlers: { app: { postMessage: m => {
        window.__sent.push(JSON.parse(JSON.stringify(m)));
        if (m.type === 'ready') setTimeout(() => window.render(s, mode), 0);
      } } } };
    }, [state, mode]);
    await p.goto(HTML);
    await p.waitForTimeout(150);
    return p;
  }
  const sent = p => p.evaluate(() => window.__sent.filter(m => m.type !== 'ready'));
  const last = async p => (await sent(p)).slice(-1)[0] || {};
  const reset = p => p.evaluate(() => { window.__sent = []; });
  const visible = (p, sel) => p.isVisible(sel);

  // ── Top bar ──
  let p = await open();
  await p.waitForTimeout(100);
  const drag = (await p.evaluate(() => window.__sent)).filter(m => m.type === 'dragRegion').slice(-1)[0];
  check('page tells the app where the draggable top bar is', drag && drag.band >= 60 && drag.buttons.length === 6, JSON.stringify(drag));
  for (const [id, page, name] of [['home', 'home', 'Transcribe'], ['notes', 'notes', 'Notes'], ['clip', 'clip', 'Clipboard'],
                                  ['dict', 'dict', 'Your words'], ['snip', 'snip', 'Shortcuts'], ['settings', 'settings', 'Settings']]) {
    await p.hover(`.nb[data-p="${id}"]`); await p.waitForTimeout(250);
    const peek = await p.textContent('#peek');
    check(`hover ${name} shows its name and preview`, (await p.evaluate(() => document.getElementById('peek').classList.contains('on'))) && peek.includes(name), peek);
    await p.click(`.nb[data-p="${id}"]`);
    check(`click ${name} opens its page`, await p.evaluate(pg => document.getElementById(pg).classList.contains('on'), page));
  }
  await p.mouse.move(500, 600); await p.waitForTimeout(200);
  check('preview hides when the mouse leaves', !(await p.evaluate(() => document.getElementById('peek').classList.contains('on'))));
  await p.hover('.nb[data-p="dict"]'); await p.waitForTimeout(250);
  check('Your words preview lists the words', (await p.textContent('#peek')).includes('مسقط'));
  await p.hover('.nb[data-p="snip"]'); await p.waitForTimeout(250);
  check('Shortcuts preview lists the shortcuts', (await p.textContent('#peek')).includes('my email → a@b.c'));

  // ── Transcribe ──
  await p.click('.nb[data-p="home"]'); await reset(p);
  check('header image is shown', await p.evaluate(() => { const i = document.getElementById('heroImg'); return i.complete && i.naturalWidth === 1990; }));
  check('logo is shown in the top bar', await p.evaluate(() => document.querySelector('header svg.wordmark').getBoundingClientRect().width > 50));
  await p.hover('#history .row'); await p.click('#history .row [data-copy="0"]');
  let m = await last(p);
  check('history Copy copies the newest text', m.type === 'copy' && m.text === 'وين صرت؟', JSON.stringify(m));
  check('history Copy shows a tick', await p.evaluate(() => document.querySelector('[data-copy="0"]').classList.contains('done')));
  // Clearing: each day has its own button, and the Clear menu has date ranges
  const days = await p.$$('#history .day');
  check('history is grouped by day, each with a clear button', days.length >= 2
    && (await p.$$('#history .day [data-clearday]')).length === days.length);
  const cleared = async () => (await sent(p)).filter(x => x.type === 'clearHistory');
  await reset(p);
  const oldBtn = '#history .day:last-child [data-clearday]';
  await p.hover('#history .day:last-child'); await p.click(oldBtn);
  check('Clear a day asks first', (await cleared()).length === 0 && (await p.textContent(oldBtn)).includes('Click again to clear'));
  await p.click(oldBtn);
  m = (await cleared())[0] || {};
  const oldTs = now - 86400 * 3;
  check('Clear a day sends just that day', m.from <= oldTs && oldTs < m.to && m.to - m.from >= 82800 && m.to - m.from <= 90000
    && m.from > now - 86400 * 5, JSON.stringify(m));
  await reset(p);
  await p.click('#clear');
  check('Clear menu opens with 4 ranges', await p.isVisible('#clearPop') && (await p.$$('#clearPop [data-range]')).length === 4);
  await p.click('#clearPop [data-range="7"]');
  check('Clear range asks first', (await cleared()).length === 0);
  await p.click('#clearPop [data-range="7"]');
  m = (await cleared())[0] || {};
  check('Clear last 7 days', Math.abs(m.from - (Date.now() / 1000 - 7 * 86400)) < 60 && m.to === undefined, JSON.stringify(m));
  check('Clear menu closes after clearing', !(await p.isVisible('#clearPop')));
  await reset(p);
  await p.click('#clear'); await p.click('#clearPop [data-range="today"]'); await p.click('#clearPop [data-range="today"]');
  m = (await cleared())[0] || {};
  const midnight = new Date(); midnight.setHours(0, 0, 0, 0);
  check('Clear today', m.from === midnight.getTime() / 1000, JSON.stringify(m));
  await reset(p);
  await p.click('#clear'); await p.click('#clearPop [data-range="all"]'); await p.click('#clearPop [data-range="all"]');
  m = (await cleared())[0] || {};
  check('Clear everything', m.type === 'clearHistory' && m.from === undefined, JSON.stringify(m));
  await p.click('#clear'); await p.click('h1');
  check('Clear menu closes when clicking elsewhere', !(await p.isVisible('#clearPop')));

  // ── Notes ──
  await p.click('.nb[data-p="notes"]'); await reset(p);
  await p.click('#newNote');
  check('New note', (await last(p)).type === 'newNote');
  check('Notetaker button is gone', !(await p.$('#ntToggle')));
  await p.click('.nitem[data-note="b2"]');
  m = await last(p);
  check('clicking a note opens it', m.type === 'openNote' && m.id === 'b2', JSON.stringify(m));
  await p.fill('#editor .ttl', 'Weekly sync v2'); await p.waitForTimeout(500);
  m = await last(p);
  check('editing the title saves it', m.type === 'updateNote' && m.title === 'Weekly sync v2' && m.id === 'a1', JSON.stringify(m));
  await p.fill('#editor .body', 'New body'); await p.waitForTimeout(500);
  m = await last(p);
  check('editing the note saves it', m.type === 'updateNote' && m.body === 'New body', JSON.stringify(m));
  for (const [act, type] of [['copy', 'copyNote'], ['export', 'exportNote'], ['pad', 'openNotepad']]) {
    await p.click(`#editor [data-act="${act}"]`);
    m = await last(p);
    check(`note ${act} button`, m.type === type && m.id === 'a1', JSON.stringify(m));
  }
  check('note Copy shows a tick', await p.evaluate(() => document.querySelector('#editor [data-act="copy"]').classList.contains('done')));
  await reset(p);
  await p.click('#editor [data-act="delete"]');
  check('Delete asks first (1 click does nothing)', (await sent(p)).length === 0);
  await p.click('#editor [data-act="delete"]');
  m = await last(p);
  check('Delete deletes on the 2nd click', m.type === 'deleteNote' && m.id === 'a1', JSON.stringify(m));
  await p.close();

  // Notepad window
  p = await open('notepad');
  await p.click('#padEditor [data-act="main"]');
  m = await last(p);
  check('Notepad: Open in Kalam', m.type === 'openMain' && m.id === 'a1', JSON.stringify(m));
  check('Notepad hides the top bar', !(await visible(p, 'header')));
  await p.close();

  // ── Clipboard ──
  p = await open();
  await p.click('.nb[data-p="clip"]'); await reset(p);
  await p.click('#clips [data-clip="1"]');
  m = await last(p);
  check('Clipboard row copies its text', m.type === 'copy' && m.text === 'First thing I said', JSON.stringify(m));
  check('Clipboard row shows a tick', await p.evaluate(() => document.querySelector('[data-clip="1"] .ib').classList.contains('done')));

  // ── Your words ──
  await p.click('.nb[data-p="dict"]'); await reset(p);
  await p.fill('#dIn', '144 Arc'); await p.click('#dForm .ib');
  m = await last(p);
  check('Your words: add a word', m.type === 'saveDictionary' && JSON.stringify(m.words) === JSON.stringify(['Kalam', 'مسقط', '144 Arc']), JSON.stringify(m));
  check('Your words: field clears after adding', (await p.inputValue('#dIn')) === '');
  await reset(p); await p.click('#dForm .ib');
  check('Your words: empty add does nothing', (await sent(p)).length === 0);
  await p.click('#words [data-del="0"]');
  m = await last(p);
  check('Your words: remove a word', m.type === 'saveDictionary' && JSON.stringify(m.words) === JSON.stringify(['مسقط']), JSON.stringify(m));

  // ── Shortcuts ──
  await p.click('.nb[data-p="snip"]'); await reset(p);
  await p.fill('#sKey', 'addr'); await p.click('#sForm .ib');
  check('Shortcuts: needs both fields', (await sent(p)).length === 0);
  await p.fill('#sVal', 'Muscat, Oman'); await p.click('#sForm .ib');
  m = await last(p);
  check('Shortcuts: add', m.type === 'saveSnippets' && m.snippets.addr === 'Muscat, Oman' && m.snippets['my email'] === 'a@b.c', JSON.stringify(m));
  await p.click('#snips [data-sdel="my email"]');
  m = await last(p);
  check('Shortcuts: remove', m.type === 'saveSnippets' && !('my email' in m.snippets) && m.snippets['sign off'] === 'Best,', JSON.stringify(m));

  // ── Settings ──
  await p.click('.nb[data-p="settings"]'); await reset(p);
  check('Settings has no tabs (Notetaker tab is gone)', !(await p.$('.tabs, #tNotetaker')));
  const toggles = await p.evaluate(() => [...document.querySelectorAll('input[type=checkbox][data-set]')].map(e => [e.dataset.set]));
  for (const [key, tab] of toggles) {
    const before = await p.isChecked(`[data-set="${key}"]`);
    await p.click(`label.tog:has([data-set="${key}"])`);
    m = await last(p);
    check(`toggle ${key}`, m.type === 'saveSettings' && m.changes[key] === !before, JSON.stringify(m));
  }
  for (const [key, value, expect] of [['dictation_language', 'ar', 'ar'], ['speech_model', 'small', 'small']]) {
    await p.selectOption(`[data-set="${key}"]`, value);
    m = await last(p);
    check(`menu ${key}`, m.type === 'saveSettings' && m.changes[key] === expect, JSON.stringify(m));
  }
  // Dictation key: pick from the menu, or record any key
  check('Dictation key menu shows the current key', (await p.$eval('#keySel', e => e.options[e.selectedIndex].text)) === 'Right ⌥');
  await p.selectOption('#keySel', '96');
  m = await last(p);
  check('Dictation key: choose F5', m.type === 'saveSettings' && m.changes.dictation_key === 96, JSON.stringify(m));
  await p.selectOption('#keySel', 'other');
  m = await last(p);
  check('Dictation key: Other key… starts listening', m.type === 'captureKey' && m.on === true
    && (await p.textContent('#keyNote')).includes('Press the key'), JSON.stringify(m));
  await p.keyboard.press('F8');
  m = await last(p);
  check('Dictation key: the pressed key is sent', m.type === 'setDictationKey' && m.code === 'F8', JSON.stringify(m));
  await p.selectOption('#keySel', 'other'); await p.keyboard.press('Escape');
  m = await last(p);
  check('Dictation key: Esc cancels', m.type === 'captureKey' && m.on === false && !(await p.$eval('#keySel', e => e.disabled)), JSON.stringify(m));
  check('model download error is shown', (await p.textContent('#modelNote')).includes('No internet'));
  await p.click('#modelRetry');
  check('model Try again', (await last(p)).type === 'retryModel');
  check('calendar and Notetaker settings are gone', await p.evaluate(() => !document.querySelector(
    '#calWarn, #scBtn, #scrOpen, [data-set="notify_before_meeting"], [data-set="auto_detect_calls"], [data-set="max_recording_minutes"]')));

  await p.close();

  // Arabic: choosing it in Settings sends the change; rendering with it flips the page right-to-left
  p = await open();
  await p.click('.nb[data-p="settings"]');
  await p.selectOption('[data-set="ui_language"]', 'ar');
  m = await last(p);
  check('App language menu sends ui_language', m.type === 'saveSettings' && m.changes.ui_language === 'ar', JSON.stringify(m));
  await p.close();
  const ar = base(); ar.settings.ui_language = 'ar'; ar.key_label = '⌥ اليمين';   // the app sends the Arabic name
  p = await open('main', ar);
  check('Arabic: key hint uses the Arabic key name', (await p.textContent('#home .pill')).includes('⌥ اليمين'));
  check('Arabic: page is right-to-left', await p.evaluate(() => document.documentElement.dir === 'rtl' && document.documentElement.lang === 'ar'));
  check('Arabic: banner is the Arabic copy', await p.evaluate(() => /header-\w+-ar\.webp$/.test(document.getElementById('heroImg').src)
    && document.getElementById('heroImg').complete && document.getElementById('heroImg').naturalWidth === 1990));
  check('Arabic: top bar stays left-to-right', await p.evaluate(() => getComputedStyle(document.querySelector('header')).direction === 'ltr'));
  const leftovers = [];
  for (const id of ['home', 'notes', 'clip', 'dict', 'snip', 'settings']) {
    await p.click(`.nb[data-p="${id}"]`);
    {
      leftovers.push(...await p.evaluate(pg => {
        const user = /Weekly sync|Groceries|Decisions|Milk|First thing I said|Kalam|my email|sign off|Best,|a@b\.c|Whisper|⌥|GB|MB|wpm|English|FaceTime|Zoom|Teams|Meet|Slack|WhatsApp|Spotify|Music|Mac|macOS|Siri|Dock|Okay, let us start\.|No internet|Older one|Powered by Amira Hamood/g;
        const out = [], w = document.createTreeWalker(document.getElementById(pg), NodeFilter.SHOW_TEXT);
        while (w.nextNode()) {
          const n = w.currentNode, el = n.parentElement;
          if (!el || !el.offsetParent || el.closest('textarea, input, script, style, svg')) continue;
          const txt = n.textContent.replace(user, '');
          if (/[A-Za-z]{3,}/.test(txt)) out.push(pg + ': ' + n.textContent.trim().slice(0, 40));
        }
        return out;
      }, id));
    }
  }
  check('Arabic: no English left on any page', leftovers.length === 0, [...new Set(leftovers)].join(' | '));
  await p.hover('.nb[data-p="notes"]');
  check('Arabic: circle preview is in Arabic', (await p.textContent('#peek')).includes('الملاحظات'));
  await p.close();

  // Dark mode: every page renders without errors
  p = await open('main', base(), 'dark');
  for (const id of ['notes', 'clip', 'dict', 'snip', 'settings', 'home']) await p.click(`.nb[data-p="${id}"]`);
  check('Voice test and Experimental tabs are gone', await p.evaluate(() => !document.querySelector('[data-t="tVoice"], [data-t="tExperimental"], #tVoice, #tExperimental')));
  check('Pause music is in System settings', await p.evaluate(() => !!document.querySelector('#tSystem [data-set="pause_media_while_dictating"]')));
  check('credit line at the bottom', (await p.textContent('.credit')) === 'Powered by Amira Hamood' && await p.isVisible('.credit'));
  check('dark mode: all pages open', await p.evaluate(() => document.getElementById('home').classList.contains('on')));
  await p.close();

  check('no script errors on any page', errors.length === 0, errors.join(' | '));
  await browser.close();
  console.log(fails ? `\n${fails} check(s) failed` : '\nAll checks passed');
  process.exit(fails ? 1 : 0);
})();
