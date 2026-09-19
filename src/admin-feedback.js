// MakeSense - Admin Feedback Dashboard
// Handles loading, filtering, and displaying feedback data

(function() {
    'use strict';

    // Configuration
    const FEEDBACK_DATA_URL = '/data/feedback.json';
    const TOPICS_DATA_URL = '/data/topics.json';

    // State
    let allFeedback = [];
    let allTopics = [];
    let filteredFeedback = [];

    // DOM Elements
    const feedbackTbody = document.getElementById('feedback-tbody');
    const topicSelect = document.getElementById('topic-select');
    const filterType = document.getElementById('filter-type');
    const filterTopic = document.getElementById('filter-topic');
    const filterSubmission = document.getElementById('filter-submission');
    const filterDate = document.getElementById('filter-date');
    const clearFiltersBtn = document.getElementById('clear-filters');
    const topicSummary = document.getElementById('topic-summary');
    
    // Stat elements
    const statTotal = document.getElementById('stat-total');
    const statUp = document.getElementById('stat-up');
    const statDown = document.getElementById('stat-down');
    const statScore = document.getElementById('stat-score');
    
    // Detail elements
    const summaryTopicTitle = document.getElementById('summary-topic-title');
    const detailUp = document.getElementById('detail-up');
    const detailDown = document.getElementById('detail-down');
    const detailScore = document.getElementById('detail-score');
    const detailTotal = document.getElementById('detail-total');
    const detailComments = document.getElementById('detail-comments');

    // Initialize
    document.addEventListener('DOMContentLoaded', async function() {
        await loadData();
        setupEventListeners();
        populateFilters();
        renderTable();
        updateOverallStats();
    });

    async function loadData() {
        try {
            // Load feedback
            const feedbackResponse = await fetch(FEEDBACK_DATA_URL, { cache: 'no-store' });
            if (feedbackResponse.ok) {
                allFeedback = await feedbackResponse.json();
            } else {
                console.warn('Could not load feedback from', FEEDBACK_DATA_URL);
                // Try localStorage fallback
                allFeedback = JSON.parse(localStorage.getItem('makesense_feedback') || '[]');
            }

            // Load topics
            const topicsResponse = await fetch(TOPICS_DATA_URL, { cache: 'no-store' });
            if (topicsResponse.ok) {
                allTopics = await topicsResponse.json();
            } else {
                console.warn('Could not load topics from', TOPICS_DATA_URL);
            }

            // Initialize filtered feedback
            filteredFeedback = [...allFeedback];
        } catch (error) {
            console.error('Error loading data:', error);
            // Fallback to localStorage
            allFeedback = JSON.parse(localStorage.getItem('makesense_feedback') || '[]');
            filteredFeedback = [...allFeedback];
        }
    }

    function setupEventListeners() {
        // Filter changes
        filterType.addEventListener('change', applyFilters);
        filterTopic.addEventListener('change', applyFilters);
        filterSubmission.addEventListener('change', applyFilters);
        filterDate.addEventListener('change', applyFilters);
        clearFiltersBtn.addEventListener('click', clearFilters);
        
        // Topic selector change
        topicSelect.addEventListener('change', function() {
            const selectedTopic = this.value;
            if (selectedTopic) {
                showTopicSummary(selectedTopic);
            } else {
                topicSummary.style.display = 'none';
            }
        });
    }

    function populateFilters() {
        // Get unique topics from feedback
        const topics = [...new Set(allFeedback.map(f => f.topic).filter(Boolean))].sort();
        topics.forEach(topic => {
            const option = document.createElement('option');
            option.value = topic;
            option.textContent = topic;
            filterTopic.appendChild(option.cloneNode(true));
            topicSelect.appendChild(option);
        });

        // Get unique submissions from feedback
        const submissions = [...new Set(allFeedback.map(f => f.submission_id).filter(Boolean))].sort();
        submissions.forEach(sub => {
            const option = document.createElement('option');
            option.value = sub;
            option.textContent = sub;
            filterSubmission.appendChild(option);
        });
    }

    function applyFilters() {
        const type = filterType.value;
        const topic = filterTopic.value;
        const submission = filterSubmission.value;
        const dateFrom = filterDate.value ? new Date(filterDate.value) : null;

        filteredFeedback = allFeedback.filter(item => {
            if (type && item.feedback_type !== type) return false;
            if (topic && item.topic !== topic) return false;
            if (submission && item.submission_id !== submission) return false;
            if (dateFrom) {
                const itemDate = new Date(item.timestamp);
                if (itemDate < dateFrom) return false;
            }
            return true;
        });

        renderTable();
    }

    function clearFilters() {
        filterType.value = '';
        filterTopic.value = '';
        filterSubmission.value = '';
        filterDate.value = '';
        filteredFeedback = [...allFeedback];
        renderTable();
    }

    function renderTable() {
        if (filteredFeedback.length === 0) {
            feedbackTbody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        <h3>No feedback found</h3>
                        <p>No feedback matches the current filters.</p>
                    </td>
                </tr>
            `;
            return;
        }

        // Sort by timestamp descending (newest first)
        const sortedFeedback = [...filteredFeedback].sort((a, b) => 
            new Date(b.timestamp) - new Date(a.timestamp)
        );

        feedbackTbody.innerHTML = sortedFeedback.map(item => `
            <tr>
                <td class="timestamp-cell">${formatDate(item.timestamp)}</td>
                <td class="topic-cell" title="${escapeHtml(item.topic)}">${escapeHtml(item.topic)}</td>
                <td>${escapeHtml(item.submission_id)}</td>
                <td>
                    <span class="feedback-type ${item.feedback_type}">
                        ${item.feedback_type === 'up' ? '👍' : '👎'} ${item.feedback_type === 'up' ? 'Helpful' : 'Not Helpful'}
                    </span>
                </td>
                <td class="comment-cell" title="${escapeHtml(item.comment || '')}">${escapeHtml(item.comment || '—')}</td>
                <td>${escapeHtml(item.user_identifier)}</td>
            </tr>
        `).join('');
    }

    function updateOverallStats() {
        const total = allFeedback.length;
        const up = allFeedback.filter(f => f.feedback_type === 'up').length;
        const down = allFeedback.filter(f => f.feedback_type === 'down').length;
        const score = up - down;

        statTotal.textContent = total;
        statUp.textContent = up;
        statDown.textContent = down;
        statScore.textContent = score >= 0 ? `+${score}` : score;
        statScore.className = 'stat-value ' + (score > 0 ? 'positive' : score < 0 ? 'negative' : 'neutral');
    }

    function showTopicSummary(topicName) {
        const topicFeedback = allFeedback.filter(f => f.topic === topicName);
        const up = topicFeedback.filter(f => f.feedback_type === 'up').length;
        const down = topicFeedback.filter(f => f.feedback_type === 'down').length;
        const total = topicFeedback.length;
        const score = up - down;
        const comments = topicFeedback
            .filter(f => f.comment)
            .slice(-5)
            .reverse(); // Most recent first

        summaryTopicTitle.textContent = `Feedback for: ${topicName}`;
        detailUp.textContent = up;
        detailDown.textContent = down;
        detailTotal.textContent = total;
        detailScore.textContent = score >= 0 ? `+${score}` : score;
        detailScore.className = 'value ' + (score > 0 ? 'positive' : score < 0 ? 'negative' : 'neutral');

        if (comments.length > 0) {
            detailComments.innerHTML = comments.map(c => `
                <div class="comment-item">
                    <strong>${escapeHtml(c.user_identifier)}</strong> (${formatDate(c.timestamp)})
                    <br>${escapeHtml(c.comment)}
                </div>
            `).join('');
        } else {
            detailComments.innerHTML = '<p class="empty-state">No comments yet</p>';
        }

        topicSummary.style.display = 'block';
    }

    function formatDate(isoString) {
        try {
            const date = new Date(isoString);
            return date.toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return isoString;
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Expose for debugging
    window.MakeSenseAdmin = {
        allFeedback,
        allTopics,
        filteredFeedback,
        loadData,
        applyFilters
    };
})();