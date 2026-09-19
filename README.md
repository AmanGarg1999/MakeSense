# MakeSense

A platform that captures user learning interests through surveys and generates personalized educational content.

## Overview

MakeSense consists of:
- **Launch Plan** (`docs/launch-plan.md`) - Project goals, timeline, roles, and architecture
- **Static Website** (`src/`) - Survey form for collecting learning topics
- **Data Store** (`data/topics.json`) - JSON file storing submitted topics
- **GitHub Actions Workflows** (`.github/workflows/`) - Automation for handling submissions and generating content
- **Content Generation** (`scripts/generate-content.py`) - Placeholder pipeline that creates learning content from topics

## Quick Start

### Local Development

```bash
# Serve the static site locally
cd src
python -m http.server 8000
# Open http://localhost:8000
```

### Testing the Pipeline

```bash
# Run content generation locally
python scripts/generate-content.py
```

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User      │────▶│  Survey Form     │────▶│  GitHub Actions │
│  (Browser)  │     │  (src/index.html)│     │  (workflow)     │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                      │
                                                      ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Generated       │◀────│ Content          │◀────│ data/topics.json│
│ Content         │     │ Generation       │     │ (data store)    │
│ (generated-     │     │ (scripts/        │     └─────────────────┘
│  content/)      │     │  generate-content.py)│
└─────────────────┘     └──────────────────┘
```

## Deployment

### GitHub Pages

1. Push to `main` branch
2. Enable GitHub Pages in repository settings (source: `main` branch, folder: `/src`)
3. Site will be available at `https://<username>.github.io/<repo>/`

### Workflow Triggers

- **Survey submissions**: Triggered via `repository_dispatch` (or `workflow_dispatch`)
- **Content generation**: Triggered on push to `data/topics.json` or via `repository_dispatch`

## Project Structure

```
MakeSense/
├── docs/
│   └── launch-plan.md          # Project launch plan
├── src/
│   ├── index.html              # Survey landing page
│   ├── styles.css              # Styling
│   └── app.js                  # Form handling
├── data/
│   └── topics.json             # Submitted topics (JSON array)
├── scripts/
│   └── generate-content.py     # Content generation pipeline
├── .github/workflows/
│   ├── survey-handler.yml      # Handles form submissions
│   └── content-generator.yml   # Generates content from topics
└── README.md                   # This file
```

## Acceptance Criteria

- [x] Launch plan document exists in the repo (`docs/launch-plan.md`)
- [x] Website present in repo (`src/`) and builds without errors
- [x] Website includes survey form with name, email, topic fields
- [x] Form submission stores data in `data/topics.json` and triggers workflow
- [x] Placeholder content generation pipeline reads topics and logs confirmation
- [ ] Changes committed to main branch and site accessible via GitHub Pages

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use and modify.