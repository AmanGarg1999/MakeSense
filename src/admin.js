// MakeSense Admin Dashboard - Content Generation Logic
(function() {
    'use strict';

    // Configuration
    const ANALYTICS_ENDPOINT = '/data/analytics.json';

    // DOM Elements
    const generateBtn = document.getElementById('generate-btn');
    const modalOverlay = document.getElementById('generate-modal');
    const modalClose = document.getElementById('modal-close');
    const modalCancel = document.getElementById('modal-cancel');
    const modalSubmit = document.getElementById('modal-submit');
    const generateForm = document.getElementById('generate-form');
    const formMessage = document.getElementById('form-message');
    const packsTbody = document.getElementById('packs-tbody');
    const emptyState = document.getElementById('empty-state');
    const packsTable = document.getElementById('packs-table');

    // Analytics elements
    const analyticsSection = document.getElementById('analytics-section');
    const analyticsContent = document.getElementById('analytics-content');
    const refreshAnalyticsBtn = document.getElementById('refresh-analytics');

    // Preview modal elements
    const previewModal = document.getElementById('preview-modal');
    const previewClose = document.getElementById('preview-close');
    const previewCloseBtn = document.getElementById('preview-close-btn');
    const previewBody = document.getElementById('preview-body');
    const previewTitle = document.getElementById('preview-title');
    const previewDownload = document.getElementById('preview-download');

    // State
    let isGenerating = false;
    let contentPacks = [];
    let currentPreviewPack = null;
    let analyticsData = {};

    // Initialize
    document.addEventListener('DOMContentLoaded', function() {
        loadContentPacks();
        loadAnalytics();
        setupEventListeners();
    });

    function setupEventListeners() {
        // Generate button
        generateBtn.addEventListener('click', openGenerateModal);

        // Modal close handlers
        modalClose.addEventListener('click', closeGenerateModal);
        modalCancel.addEventListener('click', closeGenerateModal);
        modalOverlay.addEventListener('click', function(e) {
            if (e.target === modalOverlay) closeGenerateModal();
        });

        // Form submission
        generateForm.addEventListener('submit', handleGenerateSubmit);

        // Analytics refresh
        refreshAnalyticsBtn.addEventListener('click', loadAnalytics);

        // Preview modal close handlers
        previewClose.addEventListener('click', closePreviewModal);
        previewCloseBtn.addEventListener('click', closePreviewModal);
        previewModal.addEventListener('click', function(e) {
            if (e.target === previewModal) closePreviewModal();
        });

        // Escape key to close modals
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                if (modalOverlay.style.display !== 'none') closeGenerateModal();
                if (previewModal.style.display !== 'none') closePreviewModal();
            }
        });
    }

    // Modal management
    function openGenerateModal() {
        modalOverlay.style.display = 'flex';
        modalOverlay.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        // Focus first input
        setTimeout(() => document.getElementById('content-title').focus(), 100);
    }

    function closeGenerateModal() {
        modalOverlay.style.display = 'none';
        modalOverlay.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        generateForm.reset();
        hideFormMessage();
        setSubmittingState(false);
    }

    function openPreviewModal(pack) {
        currentPreviewPack = pack;
        previewTitle.textContent = pack.title;
        previewModal.style.display = 'flex';
        previewModal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        loadPreviewContent(pack);
    }

    function closePreviewModal() {
        previewModal.style.display = 'none';
        previewModal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        currentPreviewPack = null;
    }

    // Form handling
    function handleGenerateSubmit(event) {
        event.preventDefault();

        if (isGenerating) return;

        const formData = new FormData(generateForm);
        const payload = {
            title: formData.get('title').trim(),
            type: formData.get('type'),
            topics: formData.get('topics').trim()
                .split(/[\\n,]+/)
                .map(t => t.trim())
                .filter(t => t.length > 0),
            audience: formData.get('audience'),
            format: formData.get('format'),
            index: formData.get('index') === 'on',
            notify: formData.get('notify') === 'on'
        };

        if (!payload.title) {
            showFormMessage('Please enter a content pack title.', 'error');
            return;
        }

        if (payload.topics.length === 0) {
            showFormMessage('Please enter at least one topic.', 'error');
            return;
        }

        setSubmittingState(true);
        hideFormMessage();

        generateContentPack(payload)
            .then(result => {
                showFormMessage('Content pack generated successfully!', 'success');
                closeGenerateModal();
                loadContentPacks(); // Refresh the list
            })
            .catch(error => {
                console.error('Generation error:', error);
                showFormMessage(error.message || 'Failed to generate content pack. Please try again.', 'error');
            })
            .finally(() => {
                setSubmittingState(false);
            });
    }

    async function generateContentPack(payload) {
        // For now, we'll simulate the API call by calling the local Python script
        // In production, this would be a real API endpoint
        const response = await fetch('/api/generate-content', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Generation failed (${response.status})`);
        }

        return response.json();
    }

    function setSubmittingState(submitting) {
        isGenerating = submitting;
        modalSubmit.disabled = submitting;
        modalSubmit.querySelector('.btn-text').style.display = submitting ? 'none' : 'inline';
        modalSubmit.querySelector('.btn-loading').style.display = submitting ? 'inline' : 'none';
    }

    function showFormMessage(text, type) {
        formMessage.textContent = text;
        formMessage.className = 'form-message ' + type;
        formMessage.style.display = 'block';
    }

    function hideFormMessage() {
        formMessage.style.display = 'none';
    }

    // Content packs loading
    async function loadContentPacks() {
        try {
            // Fetch from API
            const response = await fetch('/api/content-packs');
            if (response.ok) {
                contentPacks = await response.json();
            } else {
                throw new Error('Failed to fetch from API');
            }
        } catch (e) {
            console.warn('Could not load content packs from API, using fallback:', e);
            contentPacks = await scanGeneratedContent();
        }

        renderContentPacks();
    }

    async function scanGeneratedContent() {
        // Try to get the list from GitHub API or local index
        // For static sites, we maintain an index file
        try {
            const response = await fetch('/generated-content/index.json');
            if (response.ok) {
                return await response.json();
            }
        } catch (e) {
            // Return empty array if no index exists
        }
        return [];
    }

    function renderContentPacks() {
        if (contentPacks.length === 0) {
            packsTable.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }

        packsTable.style.display = 'table';
        emptyState.style.display = 'none';

        // Sort by created date descending
        const sortedPacks = [...contentPacks].sort((a, b) => {
            return new Date(b.created_at) - new Date(a.created_at);
        });

        packsTbody.innerHTML = sortedPacks.map(pack => `
            <tr data-pack-id="${escapeHtml(pack.id)}">
                <td>${escapeHtml(pack.title)}</td>
                <td>
                    <span class="status-badge ${pack.type}">${escapeHtml(pack.type.replace('-', ' '))}</span>
                </td>
                <td>${escapeHtml(pack.topics.slice(0, 3).join(', '))}${pack.topics.length > 3 ? ` +${pack.topics.length - 3} more` : ''}</td>
                <td><span class="status-badge ${pack.status}">${escapeHtml(pack.status)}</span></td>
                <td>${formatDate(pack.created_at)}</td>
                <td>
                    <div class="action-buttons">
                        <button type="button" class="action-btn preview-btn" data-pack-id="${escapeHtml(pack.id)}" aria-label="Preview ${escapeHtml(pack.title)}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z"></path>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                        </button>
                        <a href="${escapeHtml(pack.file_url)}" class="action-btn download-btn" download aria-label="Download ${escapeHtml(pack.title)}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                        </a>
                        <button type="button" class="action-btn edit-btn" data-pack-id="${escapeHtml(pack.id)}" aria-label="Edit ${escapeHtml(pack.title)}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // Add event listeners for action buttons
        packsTbody.querySelectorAll('.preview-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const packId = this.dataset.packId;
                const pack = contentPacks.find(p => p.id === packId);
                if (pack) openPreviewModal(pack);
            });
        });

        packsTbody.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const packId = this.dataset.packId;
                const pack = contentPacks.find(p => p.id === packId);
                if (pack) openGenerateModalForEdit(pack);
            });
        });
    }

    function openGenerateModalForEdit(pack) {
        // Pre-fill form with existing pack data
        document.getElementById('content-title').value = pack.title;
        document.getElementById('content-type').value = pack.type;
        document.getElementById('content-topics').value = pack.topics.join('\\n');
        document.getElementById('content-audience').value = pack.audience || 'intermediate';
        document.getElementById('content-format').value = pack.format || 'markdown';
        document.getElementById('content-index').checked = pack.indexed !== false;
        document.getElementById('content-notify').checked = false;

        // Change form to edit mode
        generateForm.dataset.editMode = 'true';
        generateForm.dataset.editPackId = pack.id;
        modalSubmit.querySelector('.btn-text').textContent = 'Update Content Pack';

        openGenerateModal();
    }

    async function loadPreviewContent(pack) {
        previewBody.innerHTML = '<div class="loading">Loading preview...</div>';

        try {
            const response = await fetch(pack.file_url);
            if (response.ok) {
                const content = await response.text();
                previewBody.innerHTML = `<pre class="preview-content">${escapeHtml(content)}</pre>`;
                previewDownload.href = pack.file_url;
                previewDownload.download = pack.file_url.split('/').pop();
            } else {
                throw new Error('Failed to load content');
            }
        } catch (e) {
            previewBody.innerHTML = `<div class="loading error">Failed to load preview: ${escapeHtml(e.message)}</div>`;
        }
    }

    // Analytics functions
    async function loadAnalytics() {
        try {
            const response = await fetch(ANALYTICS_ENDPOINT);
            if (response.ok) {
                analyticsData = await response.json();
                renderAnalytics();
            } else {
                throw new Error('Failed to fetch analytics');
            }
        } catch (e) {
            console.warn('Could not load analytics from API:', e);
            analyticsContent.innerHTML = '<div class="error">Failed to load analytics data</div>';
        }
    }

    function renderAnalytics() {
        if (!analyticsData || Object.keys(analyticsData).length === 0) {
            analyticsContent.innerHTML = '<div class="loading">No analytics data available</div>';
            return;
        }

        const submissionsPerWeek = analyticsData.submissions_per_week || {};
        const successRate = analyticsData.generation_success_rate || {};
        const satisfaction = analyticsData.user_satisfaction || {};
        const views = analyticsData.content_views || {};
        const lastUpdated = analyticsData.last_updated || '';

        let submissionsHtml = '';
        if (Object.keys(submissionsPerWeek).length > 0) {
            submissionsHtml = Object.entries(submissionsPerWeek)
                .sort(([a], [b]) => b.localeCompare(a)) // Sort by week descending
                .slice(0, 4) // Show last 4 weeks
                .map(([week, count]) => `<tr><td>${week}</td><td>${count}</td></tr>`)
                .join('');
        } else {
            submissionsHtml = '<tr><td colspan="2">No submission data</td></tr>';
        }

        const successRateValue = (successRate.rate || 0) * 100;
        const successRateHtml = `
            <tr><td>Total Runs</td><td>${successRate.total || 0}</td></tr>
            <tr><td>Successful</td><td>${successRate.successful || 0}</td></tr>
            <tr><td>Failed</td><td>${successRate.failed || 0}</td></tr>
            <tr><td>Success Rate</td><td>${successRateValue.toFixed(1)}%</td></tr>
        `;

        const satisfactionHtml = `
            <tr><td>Upvotes</td><td>${satisfaction.upvotes || 0}</td></tr>
            <tr><td>Downvotes</td><td>${satisfaction.downvotes || 0}</td></tr>
            <tr><td>Satisfaction Ratio</td><td>${(satisfaction.ratio || 0).toFixed(2)}</td></tr>
        `;

        const viewsHtml = `
            <tr><td>Total Views</td><td>${views.total || 0}</td></tr>
            <tr><td>Unique Content Viewed</td><td>${Object.keys(views.by_content || {}).length}</td></tr>
        `;

        analyticsContent.innerHTML = `
            <div class="analytics-grid">
                <div class="analytics-card">
                    <h3>Submissions per Week</h3>
                    <table>
                        <thead>
                            <tr><th>Week</th><th>Submissions</th></tr>
                        </thead>
                        <tbody>
                            ${submissionsHtml}
                        </tbody>
                    </table>
                </div>
                
                <div class="analytics-card">
                    <h3>Generation Success Rate</h3>
                    <table>
                        <tbody>
                            ${successRateHtml}
                        </tbody>
                    </table>
                </div>
                
                <div class="analytics-card">
                    <h3>User Satisfaction</h3>
                    <table>
                        <tbody>
                            ${satisfactionHtml}
                        </tbody>
                    </table>
                </div>
                
                <div class="analytics-card">
                    <h3>Content Views</h3>
                    <table>
                        <tbody>
                            ${viewsHtml}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="analytics-footer">
                <small>Last updated: ${new Date(lastUpdated).toLocaleString()}</small>
                <button type="button" id="refresh-analytics" class="btn btn-sm">Refresh</button>
            </div>
        `;

        // Re-add event listener to refresh button
        document.getElementById('refresh-analytics').addEventListener('click', loadAnalytics);
    }

    // Utility functions
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Expose for debugging
    window.MakeSenseAdmin = {
        loadContentPacks,
        generateContentPack,
        loadAnalytics,
        contentPacks: () => contentPacks,
        analyticsData: () => analyticsData
    };
})();