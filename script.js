(function() {
  const $ = id => document.getElementById(id);
  
  const toast = (msg, ms = 2500) => {
    const t = $('toast');
    $('toast-text').textContent = msg;
    t.style.opacity = '1';
    t.style.pointerEvents = 'auto';
    clearTimeout(t._timer);
    t._timer = setTimeout(() => {
      t.style.opacity = '0';
      t.style.pointerEvents = 'none';
    }, ms);
  };

  // Session timer
  const startTime = Date.now();
  setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 60000);
    $('session-time').textContent = `${elapsed}m`;
  }, 1000);

  // Conversion arrays (ODSD/KDJ mapping)
  const consonants = [], consonantsUni = [], vowels = [], vowelsUni = [], vowelModifiersUni = [];
  const specialConsonants = [], specialConsonantsUni = [], specialChar = [], specialCharUni = [];

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
  const nVowels = 26;

  specialConsonantsUni[0] = 'ං'; specialConsonants[0] = /\\n/g;
  specialConsonantsUni[1] = 'ඃ'; specialConsonants[1] = /\\h/g;
  specialConsonantsUni[2] = 'ඞ'; specialConsonants[2] = /\\N/g;
  specialConsonantsUni[3] = 'ඍ'; specialConsonants[3] = /\\R/g;
  specialConsonantsUni[4] = 'ර්\u200D'; specialConsonants[4] = /R/g;
  specialConsonantsUni[5] = 'ර්\u200D'; specialConsonants[5] = /\\r/g;

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
  consonantsUni[45] = 'ර'; consonants[45] = 'r';

  specialCharUni[0] = 'ෲ'; specialChar[0] = 'ruu';
  specialCharUni[1] = 'ෘ'; specialChar[1] = 'ru';

  function convertSinglishToSinhala(input) {
    if (!input) return '';
    let out = input;

    for (let i = 0; i < specialConsonants.length; i++) {
      out = out.replace(specialConsonants[i], specialConsonantsUni[i]);
    }

    for (let i = 0; i < specialCharUni.length; i++) {
      for (let j = 0; j < consonants.length; j++) {
        const s = consonants[j] + specialChar[i];
        const v = consonantsUni[j] + specialCharUni[i];
        const r = new RegExp(s, "g");
        out = out.replace(r, v);
      }
    }

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

    for (let i = 0; i < consonants.length; i++) {
      for (let j = 0; j < nVowels; j++) {
        const s = consonants[i] + vowels[j];
        const v = consonantsUni[i] + vowelModifiersUni[j];
        const r = new RegExp(s, "g");
        out = out.replace(r, v);
      }
    }

    for (let i = 0; i < consonants.length; i++) {
      const r = new RegExp(consonants[i], "g");
      out = out.replace(r, consonantsUni[i] + "්");
    }

    for (let i = 0; i < vowels.length; i++) {
      const r = new RegExp(vowels[i], "g");
      out = out.replace(r, vowelsUni[i]);
    }

    return out;
  }

  function updateStats() {
    const inputVal = $('input').value || '';
    const outputVal = $('output').textContent || '';
    
    $('input-chars').textContent = `${inputVal.length} characters`;
    $('output-chars').textContent = `${outputVal.length} characters`;
    
    const words = inputVal.trim() ? inputVal.trim().split(/\s+/).length : 0;
    $('word-count').textContent = words;
  }

  let debounceTimer;
  function performConversion() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const input = $('input').value;
      const output = convertSinglishToSinhala(input);
      $('output').textContent = output;
      updateStats();
    }, 100);
  }

  // Event Listeners
  $('input').addEventListener('input', performConversion);

  $('paste-btn').addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      $('input').value = text;
      performConversion();
      toast('✓ Pasted from clipboard');
    } catch {
      toast('✗ Clipboard access denied');
    }
  });

  $('clear-input').addEventListener('click', () => {
    $('input').value = '';
    $('output').textContent = '';
    updateStats();
    toast('✓ Input cleared');
  });

  $('copy-btn').addEventListener('click', async () => {
    const text = $('output').textContent;
    if (!text) {
      toast('✗ Nothing to copy');
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      toast('✓ Copied to clipboard');
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      toast('✓ Copied (fallback)');
    }
  });

  $('download-btn').addEventListener('click', () => {
    const text = $('output').textContent;
    if (!text) {
      toast('✗ Nothing to download');
      return;
    }
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sinhala-unicode.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('✓ File downloaded');
  });

  // Voice Input
  let recognition = null;
  let recognizing = false;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'si-LK';
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.addEventListener('start', () => {
      recognizing = true;
      $('voice-text').textContent = 'Listening...';
      $('pulse-ring').classList.add('pulse-ring');
      $('pulse-ring').style.opacity = '0.5';
    });

    recognition.addEventListener('end', () => {
      recognizing = false;
      $('voice-text').textContent = 'Voice Input';
      $('pulse-ring').classList.remove('pulse-ring');
      $('pulse-ring').style.opacity = '0';
    });

    recognition.addEventListener('result', (event) => {
      let finalTranscript = '';
      let interimTranscript = '';
      
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }
      
      $('input').value = (finalTranscript || interimTranscript).trim();
      performConversion();
    });

    recognition.addEventListener('error', (event) => {
      toast('✗ Voice error: ' + event.error);
      recognizing = false;
      $('voice-text').textContent = 'Voice Input';
      $('pulse-ring').classList.remove('pulse-ring');
      $('pulse-ring').style.opacity = '0';
    });
  } else {
    $('voice-btn').disabled = true;
    $('voice-btn').classList.add('opacity-50', 'cursor-not-allowed');
    $('voice-text').textContent = 'Not Supported';
  }

  $('voice-btn').addEventListener('click', () => {
    if (!recognition) {
      toast('✗ Voice recognition not available');
      return;
    }
    
    if (recognizing) {
      recognition.stop();
    } else {
      try {
        recognition.start();
        toast('🎤 Voice recognition started');
      } catch (error) {
        toast('✗ Could not start voice recognition');
      }
    }
  });

  // Example buttons
  document.querySelectorAll('.example-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const text = btn.getAttribute('data-text');
      $('input').value = text;
      performConversion();
      toast('✓ Example loaded');
    });
  });

  // Dark mode toggle (auto-detect system preference)
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.classList.add('dark');
  }

  // Initialize
  updateStats();
  toast('✨ Singlish to Unicode Converter Ready', 2000);

  // Initialize AOS
  AOS.init({
    duration: 800,
    easing: 'ease-in-out',
    once: true,
    mirror: false
  });

  // API exposure
  window.SinglishConverter = {
    convert: convertSinglishToSinhala,
    version: '2.0.0',
    author: 'KDJ'
  };
})();