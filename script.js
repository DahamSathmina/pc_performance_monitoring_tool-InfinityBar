/* ---------------------------
  ODSD / UCO Singlish ->to Sinhala
  Advanced UI glue (production-ready)
   - auto-convert, debounce
   - voice typing
   - history (localStorage)
   - theme, settings modal
----------------------------*/

(function () {
  // ---------- Utility helpers ----------
  const $ = (id) => document.getElementById(id);
  const toast = (msg, ms = 2000) => {
    const t = $('toast');
    t.textContent = msg;
    t.style.opacity = '1';
    t.style.pointerEvents = 'auto';
    clearTimeout(t._t);
    t._t = setTimeout(() => {
      t.style.opacity = '0';
      t.style.pointerEvents = 'none';
    }, ms);
  };

  // ---------- Persistent state ----------
  const LS = {
    THEME: 'ods_theme_v1',
    HISTORY: 'ods_history_v1',
    SETTINGS: 'ods_settings_v1'
  };

  const defaults = {
    theme: 'dark',
    autoConvert: true,
    debounce: 300,
    historyLimit: 50
  };

  function loadSettings() {
    try {
      const s = JSON.parse(localStorage.getItem(LS.SETTINGS) || '{}');
      return Object.assign({}, defaults, s);
    } catch {
      return Object.assign({}, defaults);
    }
  }

  function saveSettings(obj) {
    localStorage.setItem(LS.SETTINGS, JSON.stringify(obj));
  }

  const settings = loadSettings();

  // ---------- Theme handling ----------
  function applyTheme(theme) {
    if (theme === 'dark') document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
    localStorage.setItem(LS.THEME, theme);
  }
  // init theme
  (function initTheme() {
    const saved = localStorage.getItem(LS.THEME);
    if (saved) applyTheme(saved);
    else applyTheme(settings.theme || 'dark');
  })();

  $('theme-toggle').addEventListener('click', () => {
    const current = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    toast(`Theme: ${next}`);
  });

  // ---------- History ----------
  function loadHistory() {
    try {
      return JSON.parse(localStorage.getItem(LS.HISTORY) || '[]');
    } catch { return []; }
  }
  function saveHistory(h) { localStorage.setItem(LS.HISTORY, JSON.stringify(h)); }
  function addHistory(inputText, outputText) {
    if (!inputText) return;
    const hist = loadHistory();
    // don't duplicate consecutive equal entries
    if (hist.length && hist[0].input === inputText && hist[0].output === outputText) return;
    hist.unshift({ input: inputText, output: outputText, ts: Date.now() });
    if (hist.length > settings.historyLimit) hist.length = settings.historyLimit;
    saveHistory(hist);
    renderHistoryList();
  }
  function clearHistory() {
    localStorage.removeItem(LS.HISTORY);
    renderHistoryList();
    toast('History cleared');
  }

  function renderHistoryList(filter = '') {
    const wrap = $('history-list');
    const hist = loadHistory();
    wrap.innerHTML = '';
    const filtered = filter ? hist.filter(h => (h.input + ' ' + h.output).toLowerCase().includes(filter.toLowerCase())) : hist;
    if (!filtered.length) {
      wrap.innerHTML = `<div class="text-sm text-gray-500 dark:text-gray-400 p-3">No history yet</div>`;
      return;
    }
    filtered.forEach(entry => {
      const el = document.createElement('div');
      el.className = 'p-3 rounded-lg bg-gray-50 dark:bg-neutral-900 border border-gray-100 dark:border-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-neutral-800 smooth';
      el.innerHTML = `<div class="text-sm mb-1 text-gray-700 dark:text-gray-200">${escapeHtml(entry.input)}</div>
                      <div class="text-sm text-gray-600 dark:text-gray-400">${escapeHtml(entry.output)}</div>
                      <div class="text-xs text-gray-400 mt-2">${new Date(entry.ts).toLocaleString()}</div>`;
      el.addEventListener('click', () => {
        $('input').value = entry.input;
        setTimeout(() => { performConversion(); }, 50);
      });
      wrap.appendChild(el);
    });
  }

  // ---------- Escape helper ----------
  function escapeHtml(str) {
    if (!str) return '';
    return str.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
  }

  // ---------- DOM refs ----------
  const inputEl = $('input');
  const outputEl = $('output');
  const copyBtn = $('copy-btn');
  const copyBtnSmall = $('copy-btn'); // same
  const copyBtnTop = $('copy-btn');
  const pasteBtn = $('paste-btn');
  const clearBtn = $('clear-btn');
  const undoBtn = $('undo-btn');
  const voiceBtn = $('voice-btn');
  const voiceStatus = $('voice-status');
  const downloadBtn = $('download-btn');
  const historyToggle = $('history-toggle');
  const historySearch = $('history-search');
  const clearHistoryBtn = $('clear-history');
  const autoToggle = $('auto-toggle');

  // initialize auto toggle from settings
  autoToggle.checked = settings.autoConvert;
  $('modal-auto-toggle') && ($('modal-auto-toggle').checked = settings.autoConvert);
  $('debounce-input') && ($('debounce-input').value = settings.debounce || defaults.debounce);

  // ---------- Undo stack ----------
  const undoStack = [];
  function pushUndo(state) {
    if (undoStack.length > 50) undoStack.shift();
    undoStack.push(state);
  }

  // ---------- Debounced conversion ----------
  let debounceTimer = null;
  function scheduleConversion() {
    if (!settings.autoConvert) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => performConversion(true), settings.debounce || 300);
  }

  // ---------- Conversion logic (your original mapping) ----------
  // We'll include your UCSC/KDJ arrays and conversion function here.
  var text;
  var nVowels;
  var consonants = new Array();
  var consonantsUni = new Array();
  var vowels = new Array();
  var vowelsUni = new Array();
  var vowelModifiersUni = new Array();
  var specialConsonants = new Array();
  var specialConsonantsUni = new Array();
  var specialCharUni = new Array();
  var specialChar = new Array();


  vowelsUni[0] = 'ඌ'; vowels[0] = 'oo'; vowelModifiersUni[0] = 'ූ';
  vowelsUni[1] = 'ඕ'; vowels[1] = 'o\\)'; vowelModifiersUni[1] = 'ෝ';
  vowelsUni[2] = 'ඕ'; vowels[2] = 'oe'; vowelModifiersUni[2] = 'ෝ';
  vowelsUni[3] = 'ආ'; vowels[3] = 'aa'; vowelModifiersUni[3] = 'ා';
  vowelsUni[4] = 'ආ'; vowels[4] = 'a\\)'; vowelModifiersUni[4] = 'ා';
  vowelsUni[5] = 'ඈ'; vowels[5] = 'Aa'; vowelModifiersUni[5] = 'ෑ';
  vowelsUni[6] = 'ඈ'; vowels[6] = 'A\\)'; vowelModifiersUni[6] = 'ෑ';
  vowelsUni[7] = 'ඈ'; vowels[7] = 'ae'; vowelModifiersUni[7] = 'ෑ';
  vowelsUni[8] = 'ඊ'; vowels[8] = 'ii'; vowelModifiersUni[8] = 'ී';
  vowelsUni[9] = 'ඊ'; vowels[9] = 'i\\)'; vowelModifiersUni[9] = 'ී';
  vowelsUni[10] = 'ඊ'; vowels[10] = 'ie'; vowelModifiersUni[10] = 'ී';
  vowelsUni[11] = 'ඊ'; vowels[11] = 'ee'; vowelModifiersUni[11] = 'ී';
  vowelsUni[12] = 'ඒ'; vowels[12] = 'ea'; vowelModifiersUni[12] = 'ේ';
  vowelsUni[13] = 'ඒ'; vowels[13] = 'e\\)'; vowelModifiersUni[13] = 'ේ';
  vowelsUni[14] = 'ඒ'; vowels[14] = 'ei'; vowelModifiersUni[14] = 'ේ';
  vowelsUni[15] = 'ඌ'; vowels[15] = 'uu'; vowelModifiersUni[15] = 'ූ';
  vowelsUni[16] = 'ඌ'; vowels[16] = 'u\\)'; vowelModifiersUni[16] = 'ූ';
  vowelsUni[17] = 'ඖ'; vowels[17] = 'au'; vowelModifiersUni[17] = 'ෞ';
  vowelsUni[18] = 'ඇ'; vowels[18] = '/\\a'; vowelModifiersUni[18] = 'ැ';

  vowelsUni[19] = 'අ'; vowels[19] = 'a'; vowelModifiersUni[19] = '';
  vowelsUni[20] = 'ඇ'; vowels[20] = 'A'; vowelModifiersUni[20] = 'ැ';
  vowelsUni[21] = 'ඉ'; vowels[21] = 'i'; vowelModifiersUni[21] = 'ි';
  vowelsUni[22] = 'එ'; vowels[22] = 'e'; vowelModifiersUni[22] = 'ෙ';
  vowelsUni[23] = 'උ'; vowels[23] = 'u'; vowelModifiersUni[23] = 'ු';
  vowelsUni[24] = 'ඔ'; vowels[24] = 'o'; vowelModifiersUni[24] = 'ො';
  vowelsUni[25] = 'ඓ'; vowels[25] = 'I'; vowelModifiersUni[25] = 'ෛ';
  nVowels = 26;

  specialConsonantsUni[0] = 'ං'; specialConsonants[0] = /\\n/g;
  specialConsonantsUni[1] = 'ඃ'; specialConsonants[1] = /\\h/g;
  specialConsonantsUni[2] = 'ඞ'; specialConsonants[2] = /\\N/g;
  specialConsonantsUni[3] = 'ඍ'; specialConsonants[3] = /\\R/g;
  //special characher Repaya
  specialConsonantsUni[4] = 'ර්' + '\u200D'; specialConsonants[4] = /R/g;
  specialConsonantsUni[5] = 'ර්' + '\u200D'; specialConsonants[5] = /\\r/g;

  consonantsUni[0] = 'ඬ'; consonants[0] = 'nnd';
  consonantsUni[1] = 'ඳ'; consonants[1] = 'nndh';
  consonantsUni[2] = 'ඟ'; consonants[2] = 'nng';
  consonantsUni[3] = 'ථ'; consonants[3] = 'Th';
  consonantsUni[4] = 'ධ'; consonants[4] = 'Dh';
  consonantsUni[5] = 'ඝ'; consonants[5] = 'gh';
  consonantsUni[6] = 'ඡ'; consonants[6] = 'Ch';
  consonantsUni[7] = 'ඵ'; consonants[7] = 'ph';
  consonantsUni[8] = 'භ'; consonants[8] = 'bh';
  consonantsUni[9] = 'ශ'; consonants[9] = 'sh';
  consonantsUni[10] = 'ෂ'; consonants[10] = 'Sh';
  consonantsUni[11] = 'ඥ'; consonants[11] = 'GN';
  consonantsUni[12] = 'ඤ'; consonants[12] = 'KN';
  consonantsUni[13] = 'ළු'; consonants[13] = 'Lu';
  consonantsUni[14] = 'ද'; consonants[14] = 'dh';
  consonantsUni[15] = 'ච'; consonants[15] = 'ch';
  consonantsUni[16] = 'ඛ'; consonants[16] = 'kh';
  consonantsUni[17] = 'ත'; consonants[17] = 'th';

  consonantsUni[18] = 'ට'; consonants[18] = 't';
  consonantsUni[19] = 'ක'; consonants[19] = 'k';
  consonantsUni[20] = 'ඩ'; consonants[20] = 'd';
  consonantsUni[21] = 'න'; consonants[21] = 'n';
  consonantsUni[22] = 'ප'; consonants[22] = 'p';
  consonantsUni[23] = 'බ'; consonants[23] = 'b';
  consonantsUni[24] = 'ම'; consonants[24] = 'm';
  consonantsUni[25] = '‍ය'; consonants[25] = '\\u005C' + 'y';
  consonantsUni[26] = '‍ය'; consonants[26] = 'Y';
  consonantsUni[27] = 'ය'; consonants[27] = 'y';
  consonantsUni[28] = 'ජ'; consonants[28] = 'j';
  consonantsUni[29] = 'ල'; consonants[29] = 'l';
  consonantsUni[30] = 'ව'; consonants[30] = 'v';
  consonantsUni[31] = 'ව'; consonants[31] = 'w';
  consonantsUni[32] = 'ස'; consonants[32] = 's';
  consonantsUni[33] = 'හ'; consonants[33] = 'h';
  consonantsUni[34] = 'ණ'; consonants[34] = 'N';
  consonantsUni[35] = 'ළ'; consonants[35] = 'L';
  consonantsUni[36] = 'ඛ'; consonants[36] = 'K';
  consonantsUni[37] = 'ඝ'; consonants[37] = 'G';
  consonantsUni[38] = 'ඨ'; consonants[38] = 'T';
  consonantsUni[39] = 'ඪ'; consonants[39] = 'D';
  consonantsUni[40] = 'ඵ'; consonants[40] = 'P';
  consonantsUni[41] = 'ඹ'; consonants[41] = 'B';
  consonantsUni[42] = 'ෆ'; consonants[42] = 'f';
  consonantsUni[43] = 'ඣ'; consonants[43] = 'q';
  consonantsUni[44] = 'ග'; consonants[44] = 'g';
  //last because we need to ommit this in dealing with Rakaransha
  consonantsUni[45] = 'ර'; consonants[45] = 'r';

  specialCharUni[0] = 'ෲ'; specialChar[0] = 'ruu';
  specialCharUni[1] = 'ෘ'; specialChar[1] = 'ru';

  // conversion function (string -> unicode)
  function convertSinglishToSinhala(input) {
    if (!input) return '';
    let out = input;

    // special consonents (regex objects in specialConsonants)
    for (let i = 0; i < specialConsonants.length; i++) {
      out = out.replace(specialConsonants[i], specialConsonantsUni[i]);
    }

    // consonants + specialChar
    for (let i = 0; i < specialCharUni.length; i++) {
      for (let j = 0; j < consonants.length; j++) {
        const s = consonants[j] + specialChar[i];
        const v = consonantsUni[j] + specialCharUni[i];
        const r = new RegExp(s, "g");
        out = out.replace(r, v);
      }
    }

    // consonants + Rakaransha + vowel modifiers
    for (let j = 0; j < consonants.length; j++) {
      for (let i = 0; i < vowels.length; i++) {
        const s = consonants[j] + "r" + vowels[i];
        const v = consonantsUni[j] + "්‍ර" + vowelModifiersUni[i];
        const r = new RegExp(s, "g");
        out = out.replace(r, v);
      }
      const s2 = consonants[j] + "r";
      const v2 = consonantsUni[j] + "්‍ර";
      const r2 = new RegExp(s2, "g");
      out = out.replace(r2, v2);
    }

    // consonents + vowel modifiers
    for (let i = 0; i < consonants.length; i++) {
      for (let j = 0; j < nVowels; j++) {
        const s = consonants[i] + vowels[j];
        const v = consonantsUni[i] + vowelModifiersUni[j];
        const r = new RegExp(s, "g");
        out = out.replace(r, v);
      }
    }

    // consonents + HAL
    for (let i = 0; i < consonants.length; i++) {
      const r = new RegExp(consonants[i], "g");
      out = out.replace(r, consonantsUni[i] + "්");
    }

    // vowels
    for (let i = 0; i < vowels.length; i++) {
      const r = new RegExp(vowels[i], "g");
      out = out.replace(r, vowelsUni[i]);
    }

    return out;
  }

  // ---------- UI behaviors ----------
  let lastInput = '';
  function performConversion(pushHistory = false) {
    const raw = inputEl.value || '';
    // push last state to undo
    if (raw !== lastInput) pushUndo(lastInput);
    lastInput = raw;

    // Do conversion using mapping
    const converted = convertSinglishToSinhala(raw);
    outputEl.innerHTML = escapeHtml(converted) || '';

    // flash output
    const card = $('output-card');
    card.classList.add('glow');
    setTimeout(() => card.classList.remove('glow'), 450);

    // optionally add to history (when user action triggers finalization)
    if (pushHistory && raw.trim()) addHistory(raw, converted);
  }

  // manual convert (immediate)
  function manualConvertAndSave() {
    performConversion(true);
    toast('Converted and saved to history');
  }

  // ---------- Event wiring ----------
  inputEl.addEventListener('input', () => {
    if (settings.autoConvert) scheduleConversion();
  });

  // Paste
  pasteBtn.addEventListener('click', async () => {
    try {
      const t = await navigator.clipboard.readText();
      if (t) {
        pushUndo(inputEl.value);
        inputEl.value = t;
        performConversion(); // do immediate conversion (not saving to history)
        toast('Pasted from clipboard');
      } else {
        toast('Clipboard empty');
      }
    } catch (e) {
      toast('Paste not allowed by browser');
    }
  });

  // Undo
  undoBtn.addEventListener('click', () => {
    if (!undoStack.length) { toast('Nothing to undo'); return; }
    const prev = undoStack.pop();
    inputEl.value = prev || '';
    performConversion();
    toast('Undone');
  });

  // Clear
  clearBtn.addEventListener('click', () => {
    pushUndo(inputEl.value);
    inputEl.value = '';
    outputEl.innerHTML = '';
    toast('Cleared input');
  });

  // Copy
  copyBtn.addEventListener('click', async () => {
    try {
      const txt = outputEl.innerText || outputEl.textContent || '';
      await navigator.clipboard.writeText(txt);
      toast('Copied to clipboard');
    } catch {
      // fallback
      const ta = document.createElement('textarea');
      ta.value = outputEl.innerText || '';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      toast('Copied (fallback)');
    }
  });

  // Download
  downloadBtn.addEventListener('click', () => {
    const txt = outputEl.innerText || '';
    if (!txt) { toast('Nothing to download'); return; }
    const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'converted.txt';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast('Downloaded converted.txt');
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    const isCmd = e.ctrlKey || e.metaKey;
    if (isCmd && e.key === 'Enter') {
      e.preventDefault();
      // Save to history and copy
      performConversion(true);
      // copy to clipboard
      copyBtn.click();
    } else if (isCmd && (e.key === 'l' || e.key === 'L')) {
      e.preventDefault();
      pushUndo(inputEl.value);
      inputEl.value = '';
      performConversion();
    } else if (isCmd && (e.key === 'h' || e.key === 'H')) {
      e.preventDefault();
      $('history-list').parentElement.scrollIntoView({ behavior: 'smooth' });
      $('history-list').classList.add('highlight');
    }
  });

  // History toggle
  historyToggle.addEventListener('click', () => {
    const histCard = $('history-list').parentElement;
    histCard.scrollIntoView({ behavior: 'smooth' });
    toast('History opened');
  });

  historySearch.addEventListener('input', (e) => {
    renderHistoryList(e.target.value);
  });

  clearHistoryBtn.addEventListener('click', () => {
    if (!confirm('Clear entire history?')) return;
    clearHistory();
  });

  // Auto toggle
  autoToggle.addEventListener('change', (e) => {
    settings.autoConvert = e.target.checked;
    saveSettings(settings);
    toast(`Auto-convert ${settings.autoConvert ? 'enabled' : 'disabled'}`);
    if (settings.autoConvert) performConversion();
  });

  // Quick settings open
  $('settings-open').addEventListener('click', () => openSettingsModal());
  $('settings-quick').addEventListener('click', () => openSettingsModal());

  // Settings modal
  function openSettingsModal() {
    $('settings-modal').classList.remove('hidden');
    $('settings-modal').classList.add('flex');
    // sync fields
    $('modal-auto-toggle').checked = settings.autoConvert;
    $('debounce-input').value = settings.debounce || defaults.debounce;
  }
  $('settings-cancel').addEventListener('click', () => {
    $('settings-modal').classList.add('hidden');
    $('settings-modal').classList.remove('flex');
  });

  $('settings-save').addEventListener('click', () => {
    settings.autoConvert = !!$('modal-auto-toggle').checked;
    const d = parseInt($('debounce-input').value || settings.debounce || 300, 10);
    settings.debounce = Math.max(50, Math.min(2000, isNaN(d) ? 300 : d));
    saveSettings(settings);
    $('auto-toggle').checked = settings.autoConvert;
    toast('Settings saved');
    $('settings-modal').classList.add('hidden');
    $('settings-modal').classList.remove('flex');
  });

  // small "quick" settings button on output
  $('settings-quick').addEventListener('click', openSettingsModal);

  // ---------- Voice recognition ----------
  let recognition = null;
  let recognizing = false;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || null;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'si-LK'; // Sinhala language; browsers may fallback
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.addEventListener('start', () => {
      recognizing = true;
      voiceStatus.textContent = 'Listening...';
      voiceBtn.classList.add('bg-red-700');
    });
    recognition.addEventListener('end', () => {
      recognizing = false;
      voiceStatus.textContent = 'Idle';
      voiceBtn.classList.remove('bg-red-700');
    });

    let interim = '';
    recognition.addEventListener('result', (ev) => {
      let finalTranscript = '';
      interim = '';
      for (let i = 0; i < ev.results.length; ++i) {
        const res = ev.results[i];
        if (res.isFinal) finalTranscript += res[0].transcript;
        else interim += res[0].transcript;
      }
      // Put interim as input (do not finalize history)
      pushUndo(inputEl.value);
      inputEl.value = (finalTranscript || interim).trim();
      // perform conversion (but don't add to history yet)
      performConversion();
    });

    recognition.addEventListener('error', (e) => {
      toast('Voice error: ' + (e.error || 'unknown'));
      recognizing = false;
      voiceStatus.textContent = 'Idle';
      voiceBtn.classList.remove('bg-red-700');
    });
  } else {
    voiceBtn.disabled = true;
    voiceStatus.textContent = 'Voice not supported';
  }

  voiceBtn.addEventListener('click', () => {
    if (!recognition) { toast('Voice recognition not available in this browser'); return; }
    if (recognizing) {
      recognition.stop();
      voiceStatus.textContent = 'Stopping...';
    } else {
      try {
        recognition.start();
      } catch (e) {
        // some browsers throw if start called twice quickly
      }
    }
  });

  // ---------- Finalize conversion (manual save) ----------
  // When user hits "Enter" while pressing Ctrl/Cmd+Enter, earlier we save. Also add double-click to output to copy.
  outputEl.addEventListener('dblclick', () => {
    copyBtn.click();
  });

  // add on blur of input: optional final conversion and history push
  inputEl.addEventListener('blur', () => {
    // if there was input, push to history (finalized)
    if ((inputEl.value || '').trim()) addHistory(inputEl.value, convertSinglishToSinhala(inputEl.value));
  });

  // ---------- Init ----------
  function init() {
    // render settings
    settings.autoConvert = settings.autoConvert ?? defaults.autoConvert;
    settings.debounce = settings.debounce ?? defaults.debounce;
    // initial render
    renderHistoryList();
    // attach small events
    $('copy-btn').addEventListener('click', () => {
      copyBtn.click();
    });

    // load any saved input? (optional)
    // keep empty by default

    // quick toolbar actions
    $('paste-btn').addEventListener('click', () => { /* handled earlier */ });
    $('clear-btn').addEventListener('click', () => { /* handled earlier */ });
    $('undo-btn').addEventListener('click', () => { /* handled earlier */ });

    // quick top bar history open
    $('history-toggle').addEventListener('click', () => {
      // bring history into view
      $('history-list').parentElement.scrollIntoView({ behavior: 'smooth' });
    });

    // convert button when user pastes text programmatically
    // If user wants a manual convert button, they can use keyboard shortcuts (Ctrl+Enter).
    toast('Ready — KDJ Singlish mapping loaded', 1400);
  }

  init();

  // expose some things to the window for debugging / quick use
  window.ODS = {
    convertSinglishToSinhala,
    performConversion,
    addHistory,
    loadHistory,
    settings,
    saveSettings
  };

})();
