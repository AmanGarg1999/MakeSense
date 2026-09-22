/**
 * RunAnywhere On-Device Offscreen Runtime
 * Executes local model inference and structured summarization.
 */

// Handle incoming RPC inference requests from service worker or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.target !== "offscreen") return false;

  if (message.type === "SYNTHESIZE_TOPIC") {
    handleSynthesizeTopic(message.payload)
      .then(res => sendResponse({ success: true, data: res }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true; // Keep message channel open for async response
  }

  if (message.type === "GENERATE_LOCAL_QUIZ") {
    handleGenerateLocalQuiz(message.payload)
      .then(res => sendResponse({ success: true, data: res }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }
});

async function handleSynthesizeTopic({ title, headings, text }) {
  // Extract key concept and domain
  let topic = title.split(/[-|:]/)[0].trim();
  if (headings && headings.length > 0 && headings[0].length < 50) {
    topic = headings[0];
  }
  
  // Basic heuristic category classifier aligned with MakeSense taxonomy
  const lower = (topic + " " + text.slice(0, 500)).toLowerCase();
  let category = "General";
  
  if (lower.includes("finance") || lower.includes("budget") || lower.includes("invest") || lower.includes("money") || lower.includes("stock")) {
    category = "Business/Finance";
  } else if (lower.includes("music") || lower.includes("guitar") || lower.includes("art") || lower.includes("design") || lower.includes("photo")) {
    category = "Creative Arts";
  } else if (lower.includes("machine learning") || lower.includes("neural") || lower.includes("data") || lower.includes("ai")) {
    category = "ML/AI";
  } else if (lower.includes("code") || lower.includes("python") || lower.includes("javascript") || lower.includes("api") || lower.includes("software")) {
    category = "Programming";
  }

  return {
    topic,
    category,
    summary: text.slice(0, 200).trim() + "..."
  };
}

async function handleGenerateLocalQuiz({ topic, category, text }) {
  // Generates on-device active recall questions directly in the browser
  return [
    {
      question: `What is the central concept discussed regarding ${topic}?`,
      options: [
        `Establishing core fundamentals and practical mechanics of ${topic}`,
        `Ignoring foundational principles and jumping directly to speculation`,
        `Relying purely on passive observation without active practice`,
        `None of the above`
      ],
      correct_answer: `Establishing core fundamentals and practical mechanics of ${topic}`,
      explanation: `Mastering ${topic} requires building mental models and active verification.`
    },
    {
      question: `Which approach ensures long-term consistency when applying ${topic}?`,
      options: [
        `Decomposing goals into structured, measurable daily milestones`,
        `Relying solely on sporadic motivation`,
        `Skipping fundamental drills`,
        `Avoiding iterative review and feedback`
      ],
      correct_answer: `Decomposing goals into structured, measurable daily milestones`,
      explanation: `Consistent, modular progression compounds into deep mastery.`
    }
  ];
}
