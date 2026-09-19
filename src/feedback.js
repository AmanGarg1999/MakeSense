// MakeSense - Feedback Handling
// Handles thumbs up/down feedback on generated content

(function() {
    'use strict';

    // Configuration
    const GITHUB_API_URL = 'https://api.github.com/repos/AmanGarg1999/MakeSense/actions/workflows/feedback-handler.yml/dispatches';
    const FEEDBACK_DATA_URL = '/data/feedback.json';

    // State
    let githubToken = null;

    // Initialize feedback handling
    document.addEventListener('DOMContentLoaded', function() {
        setupFeedbackButtons();
    });

    function setupFeedbackButtons() {
        // Find all feedback button containers
        const containers = document.querySelectorAll('.feedback-buttons');
        containers.forEach(container => {
            const buttons = container.querySelectorAll('.feedback-btn');
            buttons.forEach(button => {
                button.addEventListener('click', handleFeedbackClick);
            });
        });
    }

    async function handleFeedbackClick(event) {
        const button = event.currentTarget;
        const container = button.closest('.feedback-buttons');
        const messageDiv = container.nextElementSibling; // feedback-message

        if (!container) return;

        const contentFile = container.dataset.contentFile;
        const topic = container.dataset.topic;
        const submissionId = container.dataset.submissionId;
        const feedbackType = button.dataset.feedback; // 'up' or 'down'

        // Generate a user identifier (could be improved with actual auth)
        const userIdentifier = getUserIdentifier();

        // Disable buttons during submission
        const buttons = container.querySelectorAll('.feedback-btn');
        buttons.forEach(btn => btn.disabled = true);

        // Show loading state
        button.classList.add('loading');
        if (messageDiv) {
            messageDiv.textContent = 'Submitting...';
            messageDiv.style.display = 'block';
            messageDiv.className = 'feedback-message';
        }

        try {
            // Submit feedback
            await submitFeedback({
                id: generateFeedbackId(),
                content_file: contentFile,
                topic: topic,
                submission_id: submissionId,
                feedback_type: feedbackType,
                user_identifier: userIdentifier,
                comment: null,
                timestamp: new Date().toISOString()
            });

            // Success
            if (messageDiv) {
                messageDiv.textContent = feedbackType === 'up' ? 'Thanks for your feedback! 👍' : 'Thanks for your feedback! We\'ll improve. 👎';
                messageDiv.className = 'feedback-message success';
            }
            button.classList.add('selected');

            // Visually show the vote count (could fetch from API)
            updateButtonStates(container, feedbackType);

        } catch (error) {
            console.error('Feedback submission error:', error);
            if (messageDiv) {
                messageDiv.textContent = 'Failed to submit feedback. Please try again.';
                messageDiv.className = 'feedback-message error';
            }
            buttons.forEach(btn => btn.disabled = false);
        } finally {
            button.classList.remove('loading');
        }
    }

    async function submitFeedback(feedbackData) {
        // Get GitHub token
        githubToken = await getGitHubToken();
        if (!githubToken) {
            throw new Error('GitHub token not available');
        }

        const payload = {
            ref: 'main',
            inputs: {
                feedback: JSON.stringify(feedbackData)
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
        // Try to get token from meta tag
        const metaTag = document.querySelector('meta[name="github-token"]');
        if (metaTag && metaTag.content) {
            return metaTag.content;
        }

        // Try environment variable
        if (typeof GITHUB_TOKEN !== 'undefined' && GITHUB_TOKEN) {
            return GITHUB_TOKEN;
        }

        console.warn('GitHub token not found in meta tag or environment');
        return null;
    }

    function getUserIdentifier() {
        // Try to get from localStorage (persistent anonymous ID)
        let userId = localStorage.getItem('makesense_user_id');
        if (!userId) {
            userId = 'user_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('makesense_user_id', userId);
        }
        return userId;
    }

    function generateFeedbackId() {
        return 'fb_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    }

    function updateButtonStates(container, selectedType) {
        const buttons = container.querySelectorAll('.feedback-btn');
        buttons.forEach(btn => {
            btn.classList.remove('selected');
            if (btn.dataset.feedback === selectedType) {
                btn.classList.add('selected');
            }
        });
    }

    // Expose for debugging
    window.MakeSenseFeedback = {
        submitFeedback,
        getUserIdentifier
    };
})();