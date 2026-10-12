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
  history: [{ ts: now - 3600, text: 'First thing I said', words: 4, secs: 2 },
            { ts: now - 60, text: 'وين صرت؟', words: 2, secs: 1 }],
  dictionary: ['Kalam', 'مسقط'], snippets: { 'my email': 'a@b.c', 'sign off': 'Best,' },
  stats: { words: 1234, wpm: 140, streak: 3 },
  settings: { dictation_language: 'auto', speech_model: 'small', launch_at_login: false, show_bar_always: false,
    show_in_dock: false, sounds: true, mute_while_dictating: false, pause_media_while_dictating: false,
    notify_before_meeting: 15, show_next_meeting: true, auto_detect_calls: true, max_recording_minutes: 120,
    stop_when_call_ends: true, meeting_shortcut: { label: '⌥ M' }, hide_from_screen_capture: false,
    open_notepad_on_start: true, split_screen_on_join: false, show_live_transcript: true, capture_system_audio: true },
  options: { dictation_language: [['auto', 'Arabic or English (auto)'], ['ar', 'Arabic'], ['en', 'English']],
    speech_model: [['small', 'Fast · built in'], ['turbo', 'Accurate · 1.6 GB download']],
    notify_before_meeting: [[-1, 'Off'], [15, '15 sec'], [60, '1 min']], max_recording_minutes: [[60, '1 hour'], [120, '2 hours']] },
  notes: [{ id: 'a1', title: 'Weekly sync', created: now - 900, meeting: true, duration: 754, recording: false, preview: 'Decisions' },
          { id: 'b2', title: 'Groceries', created: now - 86400 * 3, meeting: false, duration: 0, recording: false, preview: 'Milk' }],
  note, notetaker: { active: false }, calendar: 'denied', goto: null,
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
  check('header image is shown', await p.evaluate(() => { const i = document.getElementById('heroImg'); return i.complete && i.naturalWidth === 2000; }));
  check('logo is shown in the top bar', await p.evaluate(() => document.querySelector('header svg.wordmark').getBoundingClientRect().width > 50));
  await p.hover('#history .row'); await p.click('#history .row [data-copy="0"]');
  let m = await last(p);
  check('history Copy copies the newest text', m.type === 'copy' && m.text === 'وين صرت؟', JSON.stringify(m));
  check('history Copy shows a tick', await p.evaluate(() => document.querySelector('[data-copy="0"]').classList.contains('done')));
  await p.click('#clear');
  check('Clear history asks first (1 click does nothing)', (await sent(p)).filter(x => x.type === 'clearHistory').length === 0);
  check('Clear history button says "Clear all?"', (await p.textContent('#clear')).includes('Clear all?'));
  await p.click('#clear');
  check('Clear history clears on the 2nd click', (await sent(p)).filter(x => x.type === 'clearHistory').length === 1);

  // ── Notes ──
  await p.click('.nb[data-p="notes"]'); await reset(p);
  await p.click('#newNote');
  check('New note', (await last(p)).type === 'newNote');
  await p.click('#ntToggle');
  check('Notetaker button starts the Notetaker', (await last(p)).type === 'startNotetaker');
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

  // Recording: Stop works, Delete is hidden for the note being recorded
  p = await open('main', { ...base(), goto: 'notes', notetaker: { active: true, note_id: 'a1', started_at: now - 75 } });
  check('red dot on the Notes circle while recording', await visible(p, '.nb[data-p="notes"] .rec'));
  check('Delete is hidden while the note is recording', !(await visible(p, '#editor [data-act="delete"]')));
  await p.click('#editor .recbar [data-act="stop"]');
  check('recording bar Stop stops the Notetaker', (await last(p)).type === 'stopNotetaker');
  await p.click('#ntToggle');
  check('Notetaker button stops it while recording', (await last(p)).type === 'stopNotetaker');
  await p.close();

  // Notepad window
  p = await open('notepad', { ...base(), note: null });
  await p.click('#padEditor [data-act="start"]');
  check('Notepad: Start Notetaker', (await last(p)).type === 'startNotetaker');
  await p.close();
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
  for (const t of ['tNotetaker', 'tExperimental', 'tVoice', 'tSystem']) {
    await p.click(`.tabs button[data-t="${t}"]`);
    check(`Settings tab ${t}`, await p.evaluate(id => document.getElementById(id).classList.contains('on'), t));
  }
  const toggles = await p.evaluate(() => [...document.querySelectorAll('input[type=checkbox][data-set]')].map(e => [e.dataset.set, e.closest('.tab').id]));
  for (const [key, tab] of toggles) {
    await p.click(`.tabs button[data-t="${tab}"]`);
    const before = await p.isChecked(`[data-set="${key}"]`);
    await p.click(`label.tog:has([data-set="${key}"])`);
    m = await last(p);
    check(`toggle ${key}`, m.type === 'saveSettings' && m.changes[key] === !before, JSON.stringify(m));
  }
  for (const [key, value, expect] of [['dictation_language', 'ar', 'ar'], ['speech_model', 'small', 'small'],
                                       ['notify_before_meeting', '60', 60], ['max_recording_minutes', '60', 60]]) {
    const tab = await p.evaluate(k => document.querySelector(`[data-set="${k}"]`).closest('.tab').id, key);
    await p.click(`.tabs button[data-t="${tab}"]`);
    await p.selectOption(`[data-set="${key}"]`, value);
    m = await last(p);
    check(`menu ${key}`, m.type === 'saveSettings' && m.changes[key] === expect, JSON.stringify(m));
  }
  await p.click('.tabs button[data-t="tSystem"]');
  check('model download error is shown', (await p.textContent('#modelNote')).includes('No internet'));
  await p.click('#modelRetry');
  check('model Try again', (await last(p)).type === 'retryModel');
  await p.click('.tabs button[data-t="tNotetaker"]');
  check('calendar warning shows when access is off', await visible(p, '#calWarn'));
  await p.click('#calOpen');
  m = await last(p);
  check('Open Privacy settings (calendar)', m.type === 'openPrivacy' && m.pane === 'calendar', JSON.stringify(m));
  await p.click('#scrOpen');
  m = await last(p);
  check('Open settings (screen recording)', m.type === 'openPrivacy' && m.pane === 'screen', JSON.stringify(m));
  await p.click('#scBtn');
  m = await last(p);
  check('Change shortcut starts listening', m.type === 'captureShortcut' && m.on === true, JSON.stringify(m));
  await p.keyboard.press('Escape');
  m = await last(p);
  check('Esc cancels the shortcut change', m.type === 'captureShortcut' && m.on === false, JSON.stringify(m));
  await p.click('#scBtn'); await p.keyboard.press('Control+KeyN');
  m = await last(p);
  check('new shortcut is sent', m.type === 'setShortcut' && m.code === 'KeyN' && m.mods.includes('ctrl'), JSON.stringify(m));

  // Voice test
  await p.click('.tabs button[data-t="tVoice"]'); await reset(p);
  await p.click('[data-vrec="msa-1"]');
  m = await last(p);
  check('Voice test: Record', m.type === 'voiceTestRecord' && m.id === 'msa-1', JSON.stringify(m));
  await p.click('[data-vplay="gulf-1"]');
  m = await last(p);
  check('Voice test: Play', m.type === 'voiceTestPlay' && m.id === 'gulf-1', JSON.stringify(m));
  await reset(p); await p.click('[data-vdel="msa-1"]');
  check('Voice test: Remove asks first', (await sent(p)).length === 0);
  await p.click('[data-vdel="msa-1"]');
  m = await last(p);
  check('Voice test: Remove on 2nd click', m.type === 'voiceTestRemove' && m.id === 'msa-1', JSON.stringify(m));
  await p.fill('#vtIn', 'أبي قهوة'); await p.click('#vtAdd .ib');
  m = await last(p);
  check('Voice test: Add phrase', m.type === 'voiceTestAdd' && m.text === 'أبي قهوة', JSON.stringify(m));
  await p.click('#vtRun');
  check('Voice test: Run test', (await last(p)).type === 'voiceTestRun');
  await p.click('#vtExport');
  check('Voice test: Export', (await last(p)).type === 'voiceTestExport');
  await p.close();

  // Dark mode: every page renders without errors
  p = await open('main', base(), 'dark');
  for (const id of ['notes', 'clip', 'dict', 'snip', 'settings', 'home']) await p.click(`.nb[data-p="${id}"]`);
  check('dark mode: all pages open', await p.evaluate(() => document.getElementById('home').classList.contains('on')));
  await p.close();

  check('no script errors on any page', errors.length === 0, errors.join(' | '));
  await browser.close();
  console.log(fails ? `\n${fails} check(s) failed` : '\nAll checks passed');
  process.exit(fails ? 1 : 0);
})();
