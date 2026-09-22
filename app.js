(function() {
    // DOM Elements
    const form = document.getElementById('topic-survey');
    const topicsList = document.getElementById('topics-list');
    const topicsCount = document.getElementById('topics-count');
    const previewFilterButtons = document.querySelectorAll('#preview-filter-buttons .filter-btn');
    const suggestionChips = document.querySelectorAll('#suggestion-chips .chip-btn');
    const toastContainer = document.getElementById('toast-container');
    
    let allTopicsData = [];
    let currentPreviewFilter = 'all';

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        if (form) {
            form.addEventListener('submit', handleSubmit);
        }

        // Suggestion chip quick fill
        if (suggestionChips) {
            suggestionChips.forEach(chip => {
                chip.addEventListener('click', () => {
                    const topicText = chip.getAttribute('data-topic');
                    const textarea = document.getElementById('topics');
                    if (textarea) {
                        const current = textarea.value.trim();
                        if (!current) {
                            textarea.value = topicText;
                        } else if (!current.includes(topicText)) {
                            textarea.value = current + ', ' + topicText;
                        }
                        textarea.focus();
                        showToast(`Added "${topicText}" to your topic list!`, 'info', 3000);
                    }
                });
            });
        }

        // Preview filter buttons
        if (previewFilterButtons) {
            previewFilterButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    previewFilterButtons.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    renderTopics(allTopicsData, btn.dataset.category);
                });
            });
        }
        
        loadRecentTopics();
    }

    function showToast(message, type = 'info', duration = 6000) {
        if (!toastContainer) return;
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : '💡';
        toast.innerHTML = `<span>${icon}</span><div style="flex:1;">${message}</div>`;
        
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px) scale(0.95)';
            toast.style.transition = 'all 0.25s ease';
            setTimeout(() => toast.remove(), 250);
        }, duration);
    }
    window.showToast = showToast;

    async function handleSubmit(event) {
        event.preventDefault();
        const form = event.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        
        // Honeypot check
        const honeypot = form.querySelector('#website_url');
        if (honeypot && honeypot.value) return;

        // Get form data
        const name = form.querySelector('#name') ? form.querySelector('#name').value.trim() : '';
        const email = form.querySelector('#email') ? form.querySelector('#email').value.trim() : '';
        const topicsText = form.querySelector('#topics') ? form.querySelector('#topics').value.trim() : '';
        
        const topics = topicsText.split(/[,\n]+/).map(t => t.trim()).filter(t => t.length > 0);
        
        if (topics.length === 0) {
            showToast('Please specify at least one topic to learn.', 'error');
            return;
        }
        
        submitBtn.disabled = true;
        const btnText = submitBtn.querySelector('.btn-text');
        const btnLoading = submitBtn.querySelector('.btn-loading');
        if (btnText) btnText.style.display = 'none';
        if (btnLoading) btnLoading.style.display = 'inline';
        
        try {
            const payload = { topics };
            if (name) payload.name = name;
            if (email) payload.email = email;

            const response = await fetch('/api/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                let msg = 'Submission failed';
                if (typeof err.detail === 'string') msg = err.detail;
                else if (Array.isArray(err.detail)) msg = err.detail.map(d => d.msg || JSON.stringify(d)).join(', ');
                throw new Error(msg);
            }
            
            const result = await response.json();
            
            showToast(`🚀 ${topics.length} topic${topics.length > 1 ? 's' : ''} submitted! <a href="/library.html?user=${result.email_hash}">Open Your Library →</a>`, 'success', 9000);
            
            // Auto trigger generator in background
            fetch(`/api/generate/${result.id}`, { method: 'POST' }).catch(() => {});
            
            form.reset();
            loadRecentTopics();
        } catch (error) {
            showToast(error.message || 'Failed to submit topics. Please retry.', 'error');
        } finally {
            submitBtn.disabled = false;
            if (btnText) btnText.style.display = 'inline';
            if (btnLoading) btnLoading.style.display = 'none';
        }
    }

    async function loadRecentTopics() {
        if (!topicsList) return;
        try {
            const response = await fetch('/api/topics');
            if (!response.ok) throw new Error('Network error');
            const data = await response.json();
            allTopicsData = Array.isArray(data) ? data : [];
            if (topicsCount) {
                topicsCount.textContent = `${allTopicsData.length} Curriculum Units Available`;
            }
            renderTopics(allTopicsData, currentPreviewFilter);
        } catch (err) {
            console.error('Error fetching topics:', err);
            topicsList.innerHTML = `<p class="empty">Unable to load topics right now.</p>`;
        }
    }

    function renderTopics(topics, categoryFilter = 'all') {
        if (!topicsList) return;
        currentPreviewFilter = categoryFilter;

        const filtered = topics.filter(topic => {
            if (categoryFilter === 'all') return true;
            const cats = topic.categories || [];
            return cats.includes(categoryFilter);
        });

        if (filtered.length === 0) {
            topicsList.innerHTML = `<p class="empty" style="text-align:center; padding: 2rem; color: var(--text-muted);">No topics match the selected category filter.</p>`;
            return;
        }

        topicsList.innerHTML = filtered.slice(0, 10).map(topic => {
            const title = topic.name || (topic.raw_topics && topic.raw_topics.join(', ')) || (topic.topics && topic.topics.join(', ')) || 'Curriculum Item';
            const categories = topic.categories || ['General'];
            const status = topic.status || 'ready';
            const lessons = topic.lessons || [];

            let actionsHtml = '';
            if (lessons.length > 0) {
                const lessonId = typeof lessons[0] === 'object' ? lessons[0].id : lessons[0];
                actionsHtml = `
                    <a href="/app/#/lesson/${lessonId}" class="content-link-btn">📖 Read Lesson</a>
                    <a href="/app/#/quiz/${lessonId}" class="content-link-btn" style="border-color: rgba(16, 185, 129, 0.3); color: #059669;">✍️ Quiz</a>
                `;
            } else {
                actionsHtml = `<a href="/library.html?user=${topic.email_hash || ''}" class="content-link-btn">View Details →</a>`;
            }

            return `
                <div class="topic-card">
                    <div class="topic-main-info">
                        <div class="topic-card-title">${escapeHtml(title)}</div>
                        <div class="topic-card-meta">
                            ${categories.map(c => `<span class="category-badge">${escapeHtml(c)}</span>`).join('')}
                            <span class="status-badge ${status}">${status}</span>
                        </div>
                    </div>
                    <div class="topic-card-actions">
                        ${actionsHtml}
                    </div>
                </div>
            `;
        }).join('');
    }

    function escapeHtml(text) {
        if (!text) return '';
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
})();
