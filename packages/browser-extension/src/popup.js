/**
 * MakeSense Extension Popup Controller
 * Connects tab extraction, on-device AI synthesis, and MakeSense API ingestion.
 */

let activeTab = null;
let currentExtractedData = null;
let currentSynthesized = null;
let serverUrl = "http://localhost:8090";

document.addEventListener('DOMContentLoaded', async () => {
  // Load saved settings
  const config = await chrome.storage.local.get(['serverUrl', 'targetModel']);
  if (config.serverUrl) {
    serverUrl = config.serverUrl;
    document.getElementById('server-url').value = serverUrl;
  }
  if (config.targetModel) {
    document.getElementById('model-select').value = config.targetModel;
    document.getElementById('model-tag').innerText = config.targetModel;
  }

  // Ensure offscreen document is ready for on-device inference
  try {
    await chrome.runtime.sendMessage({ type: 'ENSURE_OFFSCREEN' });
  } catch (e) {
    console.warn('Offscreen runtime init:', e);
  }

  // Get active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  activeTab = tab;
  
  if (!tab || !tab.url || tab.url.startsWith('chrome://')) {
    document.getElementById('page-title').innerText = "Open a webpage or article to learn.";
    document.getElementById('btn-create-lesson').disabled = true;
    document.getElementById('btn-quick-quiz').disabled = true;
    return;
  }

  document.getElementById('page-title').innerText = tab.title || "Untitled Page";
  
  // Extract and synthesize current page
  await extractAndAnalyzeTab();

  // Wire event handlers
  document.getElementById('btn-settings').addEventListener('click', toggleSettings);
  document.getElementById('btn-save-settings').addEventListener('click', saveSettings);
  document.getElementById('btn-create-lesson').addEventListener('click', createMakeSenseLesson);
  document.getElementById('btn-quick-quiz').addEventListener('click', runQuickOnDeviceQuiz);
});

async function extractAndAnalyzeTab() {
  try {
    // Inject content script if not present, then extract
    const response = await chrome.tabs.sendMessage(activeTab.id, { action: "extract_content" })
      .catch(async () => {
        await chrome.scripting.executeScript({
          target: { tabId: activeTab.id },
          files: ['src/content.js']
        });
        return await chrome.tabs.sendMessage(activeTab.id, { action: "extract_content" });
      });

    if (response && response.data) {
      currentExtractedData = response.data;
      
      // Request on-device classification via offscreen document
      const synthResponse = await chrome.runtime.sendMessage({
        target: 'offscreen',
        type: 'SYNTHESIZE_TOPIC',
        payload: {
          title: response.data.title,
          headings: response.data.headings,
          text: response.data.text
        }
      });

      if (synthResponse && synthResponse.success) {
        currentSynthesized = synthResponse.data;
        document.getElementById('detected-category').innerText = currentSynthesized.category;
        document.getElementById('page-title').innerText = currentSynthesized.topic;
      }
    }
  } catch (err) {
    console.warn("Content analysis error:", err);
    document.getElementById('detected-category').innerText = "General";
  }
}

async function createMakeSenseLesson() {
  const statusContainer = document.getElementById('status-container');
  const statusText = document.getElementById('status-text');
  const resultCard = document.getElementById('result-card');
  const btnCreate = document.getElementById('btn-create-lesson');

  statusContainer.classList.remove('hidden');
  resultCard.classList.add('hidden');
  btnCreate.disabled = true;
  statusText.innerText = "Submitting topic to MakeSense...";

  try {
    const topic = currentSynthesized?.topic || activeTab.title;
    const category = currentSynthesized?.category || "General";

    // 1. Submit topic to MakeSense API
    const submitRes = await fetch(`${serverUrl}/api/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "Browser Learner",
        topics: [topic],
        categories: [category],
        source: "browser-extension"
      })
    });

    if (!submitRes.ok) {
      throw new Error(`API submit returned HTTP ${submitRes.status}`);
    }

    const submitData = await submitRes.json();
    const topicId = submitData.id;

    statusText.innerText = "⚡ Synthesizing curriculum with on-device RunAnywhere engine...";

    // 2. Trigger generation
    const genRes = await fetch(`${serverUrl}/api/generate/${topicId}`, {
      method: "POST"
    });

    if (!genRes.ok) {
      throw new Error(`API generate returned HTTP ${genRes.status}`);
    }

    // 3. Poll for lesson completion (max 6 attempts)
    let lessonId = null;
    for (let i = 0; i < 6; i++) {
      await new Promise(r => setTimeout(r, 1000));
      const checkRes = await fetch(`${serverUrl}/api/topics/${topicId}`);
      if (checkRes.ok) {
        const topicData = await checkRes.json();
        if (topicData.lessons && topicData.lessons.length > 0) {
          lessonId = topicData.lessons[0].id;
          break;
        }
      }
    }

    statusContainer.classList.add('hidden');
    resultCard.classList.remove('hidden');

    const appUrl = lessonId 
      ? `${serverUrl}/app/#/lesson/${lessonId}`
      : `${serverUrl}/app/#/library`;

    document.getElementById('result-summary').innerText = 
      `Interactive lesson generated for "${topic}" in ${category}. Ready for interactive study and quiz verification.`;
    
    const openLink = document.getElementById('btn-open-lesson');
    openLink.href = appUrl;
    openLink.innerText = `Open Lesson on MakeSense ↗`;

  } catch (err) {
    statusContainer.classList.remove('hidden');
    statusText.innerText = `Error: ${err.message}`;
    console.error("Lesson creation failed:", err);
  } finally {
    btnCreate.disabled = false;
  }
}

async function runQuickOnDeviceQuiz() {
  const quizCard = document.getElementById('quiz-card');
  const quizContent = document.getElementById('quiz-content');
  const btnQuiz = document.getElementById('btn-quick-quiz');

  quizCard.classList.remove('hidden');
  quizContent.innerHTML = `<p style="font-size:11px; color:#94a3b8;">Generating active recall questions on-device...</p>`;
  btnQuiz.disabled = true;

  try {
    const topic = currentSynthesized?.topic || activeTab.title;
    const category = currentSynthesized?.category || "General";
    const text = currentExtractedData?.text || "";

    const res = await chrome.runtime.sendMessage({
      target: 'offscreen',
      type: 'GENERATE_LOCAL_QUIZ',
      payload: { topic, category, text }
    });

    if (res && res.success && res.data) {
      renderQuiz(res.data);
    }
  } catch (err) {
    quizContent.innerHTML = `<p style="color:#ef4444; font-size:11px;">Quiz generation failed: ${err.message}</p>`;
  } finally {
    btnQuiz.disabled = false;
  }
}

function renderQuiz(questions) {
  const quizContent = document.getElementById('quiz-content');
  quizContent.innerHTML = "";

  questions.forEach((q, idx) => {
    const qDiv = document.createElement('div');
    qDiv.className = 'quiz-question';
    qDiv.innerHTML = `<p>${idx + 1}. ${q.question}</p>`;

    const optContainer = document.createElement('div');
    optContainer.className = 'quiz-options';

    q.options.forEach(opt => {
      const optBtn = document.createElement('button');
      optBtn.className = 'quiz-opt';
      optBtn.innerText = opt;
      optBtn.addEventListener('click', () => {
        // Disable sibling buttons
        Array.from(optContainer.children).forEach(b => b.disabled = true);
        if (opt === q.correct_answer) {
          optBtn.classList.add('correct');
        } else {
          optBtn.classList.add('incorrect');
          // Highlight correct one
          Array.from(optContainer.children)
            .find(b => b.innerText === q.correct_answer)
            ?.classList.add('correct');
        }
      });
      optContainer.appendChild(optBtn);
    });

    qDiv.appendChild(optContainer);
    quizContent.appendChild(qDiv);
  });
}

function toggleSettings() {
  const panel = document.getElementById('settings-panel');
  panel.classList.toggle('hidden');
}

async function saveSettings() {
  const newUrl = document.getElementById('server-url').value.trim();
  const newModel = document.getElementById('model-select').value;
  serverUrl = newUrl;
  await chrome.storage.local.set({ serverUrl: newUrl, targetModel: newModel });
  document.getElementById('model-tag').innerText = newModel;
  toggleSettings();
}
