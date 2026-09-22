# MakeSense - Browse to Learn (Chrome Extension)

Turn any webpage, article, or documentation page into an interactive, gamified lesson on **MakeSense** powered by **RunAnywhere on-device AI**.

---

## Features

- **Ambient Learning**: Click the extension icon while reading an article or documentation page to automatically extract the main topic, domain, and structured curriculum milestones.
- **On-Device RunAnywhere Inference**: Uses Chrome's Offscreen Document API (`@runanywhere/web` / WebGPU) for local processing—zero page data leaves your machine.
- **Instant MakeSense Ingestion**: Submits the analyzed topic directly to MakeSense (`POST /api/submit`) and generates a structured interactive lesson with quizzes and code/scenarios.
- **Micro Active Recall**: Test yourself immediately with a 2-question quick quiz right inside the extension popup before navigating away.
- **Configurable Models**: Supports `qwen2.5:3b`, `qwen2.5:1.5b`, or `llama3.2:3b`.

---

## How to Install in Chrome

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked**.
4. Select the directory:
   ```
   packages/browser-extension
   ```
5. Pin the **MakeSense** extension to your toolbar.

---

## Usage

1. Open any web article, blog post, or documentation (e.g. an article on personal finance, music theory, or machine learning).
2. Click the **MakeSense** extension icon in your toolbar.
3. Click **🚀 Create Full Lesson on MakeSense**.
4. Once completed, click **Open in MakeSense Dashboard ↗** to practice with interactive quizzes, earn XP, and level up your skills!
