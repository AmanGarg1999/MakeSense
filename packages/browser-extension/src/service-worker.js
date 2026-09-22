/**
 * MakeSense Extension Service Worker
 * Manages offscreen document lifecycle and tab communication.
 */

const OFFSCREEN_PATH = 'src/offscreen.html';

async function ensureOffscreenDocument() {
  if (await chrome.offscreen.hasDocument()) {
    return;
  }
  await chrome.offscreen.createDocument({
    url: OFFSCREEN_PATH,
    reasons: ['USER_SCRIPTS'],
    justification: 'RunAnywhere On-Device local model execution'
  });
}

chrome.runtime.onInstalled.addListener(async () => {
  // Set default configurations
  await chrome.storage.local.set({
    serverUrl: 'http://localhost:8090',
    targetModel: 'qwen2.5:3b',
    autoExtract: true
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'ENSURE_OFFSCREEN') {
    ensureOffscreenDocument()
      .then(() => sendResponse({ success: true }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }
});
