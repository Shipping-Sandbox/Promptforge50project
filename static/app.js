let sessionId = null;
let currentQuestions = [];

const $ = (selector) => document.querySelector(selector);

function show(id) { document.getElementById(id).classList.remove('hidden'); }
function hide(id) { document.getElementById(id).classList.add('hidden'); }
function setStatus(id, message = '') { $(id).textContent = message; }

function updateBackButton(showBack) {
  $('#back-btn').classList.toggle('hidden', !showBack);
}

function showStartScreen() {
  hide('questions-card');
  hide('api-card');
  hide('result-card');
  show('start-card');
  updateBackButton(false);
}

async function loadHistory() {
  try {
    const response = await fetch('/api/history');
    const data = await response.json();
    const history = $('#history');

    if (!data.history?.length) {
      history.innerHTML = `
        <p class="history-empty">
          Your saved prompts will appear here.
        </p>
      `;
      return;
    }

    history.innerHTML = data.history.map(item => `
      <button
        class="history-item"
        data-session-id="${item.id}"
        type="button"
      >

        <span class="history-title">
          ${escapeHtml(makeHistoryTitle(item.prompt))}
        </span>

        <span class="history-meta">
          ${escapeHtml(item.created_at)}
        </span>

        <span class="history-arrow">
          →
        </span>

      </button>
    `).join('');

    history
      .querySelectorAll('.history-item')
      .forEach(button => {

        button.addEventListener('click', () => {
          openHistory(
            Number(button.dataset.sessionId)
          );
        });

      });

  } catch (_) {

    // History should never prevent the main
    // PromptForge workflow from working.

  }
}


function makeHistoryTitle(prompt) {

  const clean = String(
    prompt || ''
  )
    .replace(/\s+/g, ' ')
    .trim();

  if (!clean) {
    return 'Untitled conversation';
  }

  /*
    Keep the history list compact.

    Prefer the first sentence when the prompt
    contains one.
  */

  const firstSentence = clean.match(
    /^(.+?[.!?])(?:\s|$)/
  );

  let title = firstSentence
    ? firstSentence[1]
    : clean;

  /*
    Avoid very long history rows.
  */

  if (title.length > 72) {
    title = title.slice(0, 69).trimEnd() + '…';
  }

  return title;
}

async function openHistory(id) {
  setStatus('#start-status', 'Loading saved session…');

  try {
    const response = await fetch(`/api/session/${id}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not load history.');

    sessionId = data.id;
    $('#prompt').value = data.original_prompt;
    currentQuestions = data.questions || [];

    hide('api-card');

    if (data.result?.available !== false && data.result) {
      renderResult(data.result);
      hide('start-card');
      hide('questions-card');
      show('result-card');
      updateBackButton(true);
    } else if (currentQuestions.length) {
      renderQuestions();
      hide('start-card');
      show('questions-card');
      hide('result-card');
      updateBackButton(true);
    } else {
      showApiState(data.result?.message || 'This session was created before the LLM API was connected.');
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (error) {
    setStatus('#start-status', error.message);
  }
}

function renderQuestions() {
  const form = $('#questions-form');

  form.innerHTML = currentQuestions.map((q, index) => {
    const inputName = `question-${q.id}`;
    const options = (q.options || []).map(option => `
      <button type="button" class="choice" data-name="${escapeHtml(inputName)}" data-value="${escapeHtml(option)}">
        <span class="choice-marker"></span>
        <span>${escapeHtml(option)}</span>
      </button>
    `).join('');

    return `
      <fieldset class="question"
        data-id="${escapeHtml(q.id)}"
        data-question="${escapeHtml(q.question)}"
        data-multi="${q.multi ? 'true' : 'false'}">
        <legend>${index + 1}. ${escapeHtml(q.question)}</legend>
        <div class="hint">${escapeHtml(q.hint || '')}</div>

        <div class="options" data-type="${q.multi ? 'checkbox' : 'radio'}">
          ${options}

          <button type="button"
            class="choice other-choice"
            data-name="${escapeHtml(inputName)}"
            data-value="__other__">
            <span class="choice-marker"></span>
            <span>Other</span>
          </button>
        </div>

        <textarea
          class="other-text"
          rows="2"
          placeholder="Describe your answer…"
          disabled></textarea>
      </fieldset>
    `;
  }).join('');

  form.querySelectorAll('.choice').forEach(button => {
    button.addEventListener('click', () => {
      const fieldset = button.closest('fieldset');
      const multi = fieldset.dataset.multi === 'true';

      if (!multi) {
        fieldset.querySelectorAll('.choice').forEach(b => b.classList.remove('selected'));
      }

      button.classList.toggle(
        'selected',
        multi ? !button.classList.contains('selected') : true
      );

      const otherSelected = fieldset.querySelector('.other-choice').classList.contains('selected');
      const otherText = fieldset.querySelector('.other-text');

      otherText.disabled = !otherSelected;

      if (!otherSelected) {
        otherText.value = '';
      } else {
        otherText.focus();
      }
    });
  });
}

function showApiState(message) {
  $('#api-message').textContent = message || 'The LLM API is not connected yet.';
  hide('start-card');
  hide('questions-card');
  hide('result-card');
  show('api-card');
  updateBackButton(true);
}

$('#start-btn').addEventListener('click', async () => {
  const prompt = $('#prompt').value.trim();

  if (prompt.length < 5) {
    setStatus('#start-status', 'Give me a little more detail so I can analyze the actual request.');
    return;
  }

  setStatus('#start-status', 'Analyzing this specific request…');
  $('#start-btn').disabled = true;
  hide('api-card');

  try {
    const response = await fetch('/api/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not start session.');

    sessionId = data.session_id;

    if (!data.available || !data.questions?.length) {
      showApiState(data.message || 'Prompt-specific clarifying questions are unavailable until an LLM API is connected.');
      loadHistory();
      return;
    }

    currentQuestions = data.questions;
    renderQuestions();
    hide('start-card');
    show('questions-card');
    updateBackButton(true);
    setStatus('#finish-status', '');
    loadHistory();

    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (error) {
    setStatus('#start-status', error.message);
  } finally {
    $('#start-btn').disabled = false;
  }
});

$('#finish-btn').addEventListener('click', async () => {
  const fieldsets = [...document.querySelectorAll('#questions-form fieldset')];
  const answers = [];

  for (const fieldset of fieldsets) {
    const selected = [...fieldset.querySelectorAll('.choice.selected')];

    if (!selected.length) {
      setStatus('#finish-status', 'Choose an answer for every question.');
      return;
    }

    const values = selected.map(choice => {
      if (choice.dataset.value === '__other__') {
        return fieldset.querySelector('.other-text').value.trim();
      }
      return choice.dataset.value;
    }).filter(Boolean);

    if (!values.length) {
      setStatus('#finish-status', 'Please describe your answer in the Other field.');
      return;
    }

    answers.push({
      id: fieldset.dataset.id,
      question: fieldset.dataset.question,
      answer: values.join(', ')
    });
  }

  setStatus('#finish-status', 'Creating a plan specifically for your request…');
  $('#finish-btn').disabled = true;

  try {
    const response = await fetch(`/api/session/${sessionId}/finalize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not finalize session.');

    if (data.result?.available === false) {
      showApiState(data.result.message);
      return;
    }

    renderResult(data.result);
    hide('questions-card');
    show('result-card');
    updateBackButton(true);
    loadHistory();

    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (error) {
    setStatus('#finish-status', error.message);
  } finally {
    $('#finish-btn').disabled = false;
  }
});

$('#restart-btn').addEventListener('click', () => {
  sessionId = null;
  currentQuestions = [];
  $('#prompt').value = '';
  $('#questions-form').innerHTML = '';
  $('#result').innerHTML = '';
  showStartScreen();
  setStatus('#start-status', '');
  loadHistory();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

$('#back-btn').addEventListener('click', () => {
  showStartScreen();
  setStatus('#start-status', '');
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

function renderResult(result) {
  const pipeline = (result.pipeline || []).map(item => `
    <div class="pipeline-item">
      <div class="pipeline-step">${escapeHtml(item.step)}</div>
      <strong>${escapeHtml(item.tool)}</strong>
      <p>${escapeHtml(item.purpose || '')}</p>
      ${item.when_to_use ? `<p><b>Use it when:</b> ${escapeHtml(item.when_to_use)}</p>` : ''}
    </div>
  `).join('');

  const models = (result.suggested_models || []).map(model =>
    `<div class="model-card">
      <strong>${escapeHtml(model.name)}</strong>
      <span>${escapeHtml(model.role)}</span>
      <p>${escapeHtml(model.reason)}</p>
    </div>`
  ).join('');

  const warnings = (result.warnings || []).map(w =>
    `<div class="warning">${escapeHtml(w)}</div>`
  ).join('');

  $('#result').innerHTML = `
    ${result.task_summary ? `
      <div class="result-block">
        <div class="result-title">What I understood</div>
        <div class="refined">${escapeHtml(result.task_summary)}</div>
      </div>` : ''}

    <div class="result-block">
      <div class="result-title">Verdict for this request</div>
      <div class="refined">${escapeHtml(result.verdict || '')}</div>
    </div>

    <div class="result-block">
      <div class="result-title">Refined prompt</div>
      <div class="refined">${escapeHtml(result.refined_prompt || '')}</div>
    </div>

    <div class="result-block">
      <div class="result-title">Recommended pipeline</div>
      <div class="pipeline">${pipeline}</div>
    </div>

    ${models ? `
      <div class="result-block">
        <div class="result-title">Best model roles for this task</div>
        <div class="model-grid">${models}</div>
      </div>` : ''}

    ${warnings ? `
      <div class="result-block">
        <div class="result-title">Task-specific watch-outs</div>
        ${warnings}
      </div>` : ''}
  `;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[char]));
}

updateBackButton(false);
loadHistory();

/* --------------------------------------------------
   INTERACTIVE DEMO
-------------------------------------------------- */

const demoData = {
  pymupdf: {
    name: 'PyMuPDF',
    slug: 'python',
    icon: 'https://cdn.simpleicons.org/python',
    url: 'https://pymupdf.readthedocs.io/en/latest/',
    purpose: 'Extract the PDF locally with page boundaries preserved. This is the source-of-truth ingestion step, so downstream AI sees the actual document rather than an image of it.',
    instruction: `Implement a PDF ingestion service in Python using PyMuPDF.\n\nInput: uploaded PDF file.\nOutput: a structured JSON document with:\n- page number\n- extracted text\n- document title/metadata when available\n- character count\n\nPreserve page boundaries, remove obvious repeated headers/footers where safe, and flag pages with little or no extractable text so OCR can be added later. Do not summarize or rewrite the source at this stage.`
  },
  claude: {
    name: 'Claude',
    slug: 'anthropic',
    icon: 'https://cdn.simpleicons.org/anthropic',
    url: 'https://docs.anthropic.com/en/docs',
    purpose: 'Turn the extracted source into a chaptered, two-host podcast script while staying faithful to the PDF. The model should identify the important ideas, decide what belongs in each chapter, and keep claims traceable to source pages.',
    instruction: `Using the page-aware PDF text below, create a chaptered two-host podcast script.\n\nRequirements:\n- preserve factual meaning; never invent facts, statistics, quotations, or citations\n- introduce the document and its purpose clearly\n- divide the material into logical chapters\n- write natural back-and-forth dialogue between Host A and Host B\n- let the hosts explain, question, connect, and clarify ideas instead of simply reading the PDF aloud\n- keep important technical terms accurate and explain them in plain language when useful\n- attach source page references to factual claims in metadata, not as spoken dialogue\n- create a concise episode title and chapter titles\n- return estimated spoken duration for each chapter\n\nReturn structured JSON containing episode metadata, chapters, speaker turns, and source-page references.`
  },
  elevenlabs: {
    name: 'ElevenLabs',
    slug: 'elevenlabs',
    icon: 'https://cdn.simpleicons.org/elevenlabs',
    url: 'https://elevenlabs.io/docs/overview/capabilities/text-to-speech',
    purpose: 'Convert the approved Host A / Host B script into natural speech. Keep each speaker consistent across every chapter and return one audio asset per chapter so the app can assemble and retry pieces independently.',
    instruction: `Generate speech from the approved two-speaker script.\n\nVoice requirements:\n- Host A: calm, informed, conversational\n- Host B: curious, warm, slightly more energetic\n- natural pauses and turn-taking\n- pronounce technical terms clearly\n- do not add words that are not present in the approved script\n- create separate audio files for each chapter\n- keep voice IDs and generation settings fixed across chapters for consistency\n\nOutput metadata must map each generated audio file to its chapter and speaker turns.`
  },
  ffmpeg: {
    name: 'FFmpeg',
    slug: 'ffmpeg',
    icon: 'https://cdn.simpleicons.org/ffmpeg',
    url: 'https://ffmpeg.org/documentation.html',
    purpose: 'Assemble the generated speaker clips into chapter episodes and one final podcast. Normalize loudness, add optional intro/outro music, and export a clean MP3 for playback and download.',
    instruction: `Build the audio post-processing job with FFmpeg.\n\nFor every chapter:\n1. concatenate Host A and Host B clips in script order\n2. keep sample rate/channel settings consistent\n3. normalize perceived loudness to a consistent podcast level\n4. add a short intro only if supplied by the product\n5. export MP3 suitable for web streaming\n\nThen concatenate chapters into a complete episode, preserve chapter timing metadata separately, and return the final duration plus file paths. Never re-synthesize or edit the spoken words in this step.`
  },
  supabase: {
    name: 'Supabase',
    slug: 'supabase',
    icon: 'https://cdn.simpleicons.org/supabase',
    url: 'https://supabase.com/docs/guides/storage/quickstart',
    purpose: 'Persist the uploaded source and generated assets outside the relational records. Keep each episode, its chapters, transcript, audio files, and processing status linked by one episode ID with access controls.',
    instruction: `Create storage and database records for each generated podcast.\n\nStore:\n- original PDF\n- extracted text JSON\n- chapter transcript JSON\n- chapter audio files\n- final MP3\n- episode title, language, duration, chapter list, status, timestamps\n\nUse a stable episode_id to link every asset. Keep large files in object storage rather than embedding them in relational rows. Apply per-user access rules so one user cannot read another user's source PDF or audio.`
  },
  vercel: {
    name: 'Vercel',
    slug: 'vercel',
    icon: 'https://cdn.simpleicons.org/vercel',
    url: 'https://vercel.com/docs',
    purpose: 'Deploy the user-facing upload, processing-status, transcript, chapter navigation, streaming, and download experience. The deployment layer should only orchestrate requests; long-running PDF/audio work belongs in background jobs.',
    instruction: `Deploy the web application with a production flow of:\n\nUpload PDF → create episode record → enqueue processing → show progress → poll/subscribe for status → display chapters + transcript → stream final audio → offer MP3 download.\n\nKeep secrets server-side. Treat PDF extraction, LLM calls, TTS generation, and FFmpeg as asynchronous work rather than one long browser request. Expose only the minimum API routes required by the frontend.`
  }
};

function setDemoTool(toolKey) {
  const data = demoData[toolKey];
  if (!data) return;

  document.querySelectorAll('.tool-node').forEach(node => {
    node.classList.toggle('active', node.dataset.tool === toolKey);
  });

  $('#tool-detail-icon').innerHTML = `<img src="${data.icon}" alt="${escapeHtml(data.name)}">`;
  $('#tool-detail-title').textContent = data.name;
  $('#tool-detail-purpose').textContent = data.purpose;
  $('#tool-detail-instruction').textContent = data.instruction;
  $('#tool-link').href = data.url;
}

function openDemo() {
  $('#demo-modal').classList.remove('hidden');
  document.body.classList.add('demo-open');
  setDemoTool('pymupdf');
}

function closeDemo() {
  $('#demo-modal').classList.add('hidden');
  document.body.classList.remove('demo-open');
}

$('#demo-btn').addEventListener('click', openDemo);
$('#demo-close').addEventListener('click', closeDemo);
$('#demo-close-bottom').addEventListener('click', closeDemo);

$('#demo-modal').addEventListener('click', event => {
  if (event.target.matches('[data-close-demo]')) {
    closeDemo();
  }
});

document.querySelectorAll('.tool-node').forEach(node => {
  node.addEventListener('click', () => setDemoTool(node.dataset.tool));
});

document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !$('#demo-modal').classList.contains('hidden')) {
    closeDemo();
  }
});
