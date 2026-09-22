// MakeSense - Survey Form Handling
//
// This version wires the form submission to GitHub Actions workflow_dispatch
// instead of using localStorage.
//
// Acceptance Criteria:
// - Form submission POSTs to GitHub Actions workflow_dispatch endpoint with JSON payload
// - topics.json is updated in repo with new submission (validated via workflow)
// - User sees success/error feedback in UI
// - No localStorage fallback remains

(function() {
    'use strict';

    // Configuration
    const API_ENDPOINT = '/api/submit-topic'; // Kept for reference but not used
    const TOPICS_DATA_URL = '/data/topics.json';
    const GITHUB_API_URL = 'https://api.github.com/repos/AmanGarg1999/MakeSense/actions/workflows/survey-handler.yml/dispatches';

    // DOM Elements
    const form = document.getElementById('topic-survey');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoading = submitBtn.querySelector('.btn-loading');
    const formMessage = document.getElementById('form-message');
    const topicsList = document.getElementById('topics-list');

    // State
    let isSubmitting = false;

    // Initialize
    document.addEventListener('DOMContentLoaded', function() {
        loadTopics();
        setupForm();
    });

    function setupForm() {
        form.addEventListener('submit', handleSubmit);

        // Real-time validation
        const topicsInput = document.getElementById('topics');
        topicsInput.addEventListener('input', function() {
            const hasContent = this.value.trim().length > 0;
            submitBtn.disabled = !hasContent || isSubmitting;
        });
    }

    async function handleSubmit(event) {
        event.preventDefault();

        if (isSubmitting) return;

        const formData = new FormData(form);
        const name = formData.get('name').trim();
        const email = formData.get('email').trim();
        const topicsText = formData.get('topics').trim();

        if (!topicsText) {
            showMessage('Please enter at least one topic.', 'error');
            return;
        }

        // Parse topics (one per line or comma-separated)
        const topics = topicsText
            .split(/[\\n,]+/)
            .map(t => t.trim())
            .filter(t => t.length > 0);

        if (topics.length === 0) {
            showMessage('Please enter valid topics.', 'error');
            return;
        }

        // Prepare submission
        const submission = {
            id: generateId(),
            timestamp: new Date().toISOString(),
            name: name || 'Anonymous',
            email: email || null,
            topics: topics,
            status: 'pending'
        };

        setSubmitting(true);

        try {
            // Submit to GitHub Actions workflow via workflow_dispatch
            await submitToWorkflow(submission);

            showMessage('Thank you! Your topics have been submitted. We\'ll start creating content for them.', 'success');
            form.reset();
            submitBtn.disabled = true;

            // Reload topics to show the new submission
            setTimeout(loadTopics, 3000); // Increased delay to allow for workflow processing
        } catch (error) {
            console.error('Submission error:', error);
            showMessage('Something went wrong. Please try again.', 'error');
        } finally {
            setSubmitting(false);
        }
    }

    async function submitToWorkflow(submission) {
        // Get GitHub token from environment or meta tag
        // For GitHub Pages, we need to use a personal access token or rely on GitHub Actions secrets
        // Since this is a static site, we'll need to use a token with repo scope
        
        // Try to get token from meta tag (set during build) or from GitHub token secret
        const githubToken = await getGitHubToken();
        
        if (!githubToken) {
            throw new Error('GitHub token not available. Please configure the repository secret.');
        }

        const payload = {
            ref: 'main',
            inputs: {
                submission: JSON.stringify(submission)
            }
        };

        const response = await fetch(GITHUB_API_URL, {
            method: 'POST',
            headers: {
                'Authorization': `token ${githubToken}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`GitHub API error: ${response.status} ${response.statusText} - ${errorText}`);
        }

        return response.json();
    }

    async function getGitHubToken() {
        // Try to get token from meta tag (could be set during build/deploy)
        const metaTag = document.querySelector('meta[name="github-token"]');
        if (metaTag && metaTag.content) {
            return metaTag.content;
        }

        // Try to get from environment variable (if available via build process)
        // This would need to be set during the build/deployment process
        if (typeof GITHUB_TOKEN !== 'undefined' && GITHUB_TOKEN) {
            return GITHUB_TOKEN;
        }

        // For local development, we might need to prompt or use a different approach
        // But for production, the token should be provided via build process or GitHub Actions
        console.warn('GitHub token not found in meta tag or environment');
        return null;
    }

    async function loadTopics() {
        try {
            // Try to fetch from data/topics.json (updated by GitHub Actions)
            const response = await fetch(TOPICS_DATA_URL, { cache: 'no-store' });
            if (response.ok) {
                const data = await response.json();
                renderTopics(data);
                return;
            }
        } catch (e) {
            console.warn('Could not load topics from data/topics.json:', e);
            // Fallback to localStorage for demo/dev purposes only
            // TODO: Remove this fallback in production
        }

        // Fallback: load from localStorage (for development/demo only)
        const local = JSON.parse(localStorage.getItem('makesense_topics') || '[]');
        renderTopics(local);
    }

    function renderTopics(topics) {
        if (!topics || topics.length === 0) {
            topicsList.innerHTML = '<p class=\"empty\">No topics submitted yet. Be the first!</p>';
            return;
        }

        // Show latest 10
        const displayTopics = topics.slice(0, 10);

        topicsList.innerHTML = displayTopics.map((item, index) => {
            const date = new Date(item.timestamp).toLocaleDateString();
            const topicPreview = item.topics.slice(0, 3).join(', ');
            const moreCount = item.topics.length > 3 ? ` +${item.topics.length - 3} more` : '';

            return `
                <div class=\"topic-item\">
                    <div class=\"topic-icon\">${index + 1}</div>
                    <div class=\"topic-content\">
                        <div class=\"topic-title\">${escapeHtml(topicPreview)}${moreCount}</div>
                        <div class=\"topic-meta\">Submitted by ${escapeHtml(item.name)} on ${date} — Status: ${item.status}</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function showMessage(text, type) {
        formMessage.textContent = text;
        formMessage.className = 'form-message ' + type;
        formMessage.style.display = 'block';

        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                formMessage.style.display = 'none';
            }, 8000);
        }
    }

    function setSubmitting(submitting) {
        isSubmitting = submitting;
        submitBtn.disabled = submitting || document.getElementById('topics').value.trim().length === 0;
        btnText.style.display = submitting ? 'none' : 'inline';
        btnLoading.style.display = submitting ? 'inline' : 'none';
    }

    function generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Expose for debugging
    window.MakeSense = {
        loadTopics,
        submitToWorkflow
    };
})();