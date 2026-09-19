# MakeSense Launch Plan

## Overview

This document outlines the launch plan for MakeSense, a platform that captures user learning interests through surveys and generates personalized educational content.

## Goals

1. **Collect Learning Topics**: Build a simple survey mechanism to gather topics users want to learn
2. **Content Generation Pipeline**: Create a pipeline that transforms collected topics into structured learning content
3. **User Engagement**: Establish a feedback loop where users see their requested topics being addressed
4. **Scalable Foundation**: Build on version-controlled infrastructure that can grow with demand

## Timeline

| Phase | Dates | Milestone |
|-------|-------|-----------|
| **Phase 1: Foundation** | Week 1-2 | Launch plan doc, static site with survey, data storage |
| **Phase 2: Pipeline** | Week 3-4 | Content generation pipeline consuming survey data |
| **Phase 3: Deploy** | Week 5 | GitHub Pages deployment, monitoring, feedback loop |
| **Phase 4: Iterate** | Ongoing | User feedback integration, feature expansion |

## Roles & Responsibilities

| Role | Responsibilities |
|------|------------------|
| **Product Owner** | Define priorities, approve content quality, manage roadmap |
| **Frontend Developer** | Survey form, static site, user experience |
| **Backend/DevOps** | Data storage, GitHub Actions workflows, deployment pipeline |
| **Content Engineer** | Content generation templates, quality assurance, formatting |
| **Community Manager** | User outreach, survey promotion, feedback collection |

## Technical Architecture

### Data Flow

```
User → Survey Form (HTML/JS) → GitHub Actions Workflow → data/topics.json → Content Generation Script → Generated Content
```

### Components

1. **Static Website** (`src/`)
   - `index.html` - Landing page with survey form
   - `styles.css` - Styling
   - `app.js` - Form handling and submission

2. **Data Store** (`data/`)
   - `topics.json` - JSON array of submitted topics with metadata

3. **Automation** (`.github/workflows/`)
   - `survey-handler.yml` - Receives form submissions, stores to `topics.json`
   - `content-generator.yml` - Triggered on `topics.json` changes, generates content

4. **Content Generation** (`scripts/`)
   - `generate-content.py` - Reads topics, outputs confirmation/logs

5. **Documentation** (`docs/`)
   - `launch-plan.md` - This document

## Acceptance Criteria Tracking

- [x] Launch plan document exists in the repo (docs/launch-plan.md)
- [ ] Website present in repo (src/) and builds without errors
- [ ] Website includes survey form with name, email, topic fields
- [ ] Form submission stores data in data/topics.json and triggers workflow
- [ ] Placeholder content generation pipeline reads topics and logs confirmation
- [ ] Changes committed to main branch, site accessible via GitHub Pages

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Low survey response | Medium | Medium | Promote via social channels, community outreach |
| GitHub Pages limitations | Low | Low | Use Netlify/Vercel as fallback |
| Content quality issues | Medium | High | Human review gate before publishing |

## Success Metrics

- **Week 2**: 50+ survey submissions
- **Week 4**: 10+ content pieces generated
- **Week 8**: 100+ active users, 4.0+ satisfaction rating

## Next Steps

1. Complete static website with survey form
2. Implement GitHub Actions workflow for data collection
3. Build content generation placeholder script
4. Configure GitHub Pages deployment
5. Promote survey to target audience

---

*Last updated: 2026-09-19*
*Version: 1.0*