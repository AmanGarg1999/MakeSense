/**
 * MakeSense Content Script
 * Extracts clean, pedagogical article content and structure from the active tab.
 */

function extractCleanPageData() {
  const title = document.title || "";
  const url = window.location.href;
  
  // Extract meta description
  const metaDesc = document.querySelector('meta[name="description"]')?.getAttribute('content') || "";
  
  // Extract main headings
  const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
    .map(h => h.innerText.trim())
    .filter(h => h.length > 3 && h.length < 120)
    .slice(0, 10);

  // Extract core text content from semantic article or main containers
  const contentElement = document.querySelector('article, main, [role="main"], #content, .post-content') || document.body;
  
  // Clone element to sanitize without altering DOM
  const clone = contentElement.cloneNode(true);
  
  // Remove boilerplate & noise elements
  const noiseSelectors = [
    'script', 'style', 'nav', 'header', 'footer', 'aside',
    'iframe', 'noscript', '.ad', '.ads', '.advertisement',
    '.sidebar', '.comments', '.social-share', '.cookie-banner'
  ];
  clone.querySelectorAll(noiseSelectors.join(',')).forEach(el => el.remove());
  
  // Extract paragraphs
  const paragraphs = Array.from(clone.querySelectorAll('p, li, blockquote'))
    .map(p => p.innerText.trim())
    .filter(p => p.length > 25)
    .slice(0, 30);
    
  const fullText = paragraphs.join('\n\n').slice(0, 8000); // 8k char context budget
  
  return {
    title,
    url,
    metaDesc,
    headings,
    text: fullText
  };
}

// Listen for requests from popup or service worker
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extract_content") {
    const pageData = extractCleanPageData();
    sendResponse({ success: true, data: pageData });
  }
  return true;
});
