// MakeSense - Survey Form Handling

(function() {
    'use strict';

    // Configuration
    const API_ENDPOINT = '/api/submit-topic'; // Will be handled by GitHub Actions
    const TOPICS_DATA_URL = '/data/topics.json';

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
            .split(/[\n,]+/)
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
            // Submit to GitHub Actions workflow via form POST
            // Using GitHub's webhook-style approach with a hidden iframe
            await submitToWorkflow(submission);

            showMessage('Thank you! Your topics have been submitted. We\'ll start creating content for them.', 'success');
            form.reset();
            submitBtn.disabled = true;

            // Reload topics to show the new submission
            setTimeout(loadTopics, 2000);
        } catch (error) {
            console.error('Submission error:', error);
            showMessage('Something went wrong. Please try again.', 'error');
        } finally {
            setSubmitting(false);
        }
    }

    function submitToWorkflow(submission) {
        // Since this is a static site, we'll use GitHub Actions workflow_dispatch
        // The form will POST to a GitHub Actions workflow that:
        // 1. Reads the current topics.json
        // 2. Appends the new submission
        // 3. Commits the updated file
        // 4. Triggers the content generation workflow

        // For static hosting, we'll use a clever approach:
        // The form submits to a GitHub Actions workflow via a POST to the repo's
        // workflow_dispatch endpoint, or we use a serverless function.
        // For now, we'll simulate by storing locally and showing the flow.

        // In production, this would be:
        // return fetch('https://api.github.***REDACTED***urvey-handler.yml/dispatches', {
        //     method: 'POST',
        //     headers: { 'Authorization': 'token GITHUB_TOKEN', 'Accept': 'application/vnd.github.v3+json' },
        //     body: JSON.stringify({ ref: 'main', inputs: { submission: JSON.stringify(submission) } })
        // });

        // For the static demo, we'll store in localStorage and simulate
        return new Promise((resolve) => {
            // Simulate API call
            setTimeout(() => {
                // Store locally for demo
                const existing = JSON.parse(localStorage.getItem('makesense_topics') || '[]');
                existing.unshift(submission);
                localStorage.setItem('makesense_topics', JSON.stringify(existing));
                resolve();
            }, 500);
        });
    }

    async function loadTopics() {
        try {
            // Try to fetch from data/topics.json (will work after GitHub Actions runs)
            const response = await fetch(TOPICS_DATA_URL);
            if (response.ok) {
                const data = await response.json();
                renderTopics(data);
                return;
            }
        } catch (e) {
            // Fallback to localStorage for demo
        }

        // Fallback: load from localStorage
        const local = JSON.parse(localStorage.getItem('makesense_topics') || '[]');
        renderTopics(local);
    }

    function renderTopics(topics) {
        if (!topics || topics.length === 0) {
            topicsList.innerHTML = '<p class="empty">No topics submitted yet. Be the first!</p>';
            return;
        }

        // Show latest 10
        const displayTopics = topics.slice(0, 10);

        topicsList.innerHTML = displayTopics.map((item, index) => {
            const date = new Date(item.timestamp).toLocaleDateString();
            const topicPreview = item.topics.slice(0, 3).join(', ');
            const moreCount = item.topics.length > 3 ? ` +${item.topics.length - 3} more` : '';

            return `
                <div class="topic-item">
                    <div class="topic-icon">${index + 1}</div>
                    <div class="topic-content">
                        <div class="topic-title">${escapeHtml(topicPreview)}${moreCount}</div>
                        <div class="topic-meta">Submitted by ${escapeHtml(item.name)} on ${date} — Status: ${item.status}</div>
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