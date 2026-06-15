document.addEventListener('DOMContentLoaded', () => {
    // Application State
    let state = {
        allNotes: [],
        activeType: 'all',
        searchQuery: '',
        sortOrder: 'desc', // 'desc' = Newest first, 'asc' = Oldest first
        selectedNote: null
    };

    // DOM Elements
    const elements = {
        refreshBtn: document.getElementById('refreshBtn'),
        refreshIcon: document.getElementById('refreshIcon'),
        cacheStatus: document.getElementById('cacheStatus'),
        
        // Stats
        statTotal: document.getElementById('statTotal'),
        statFeatures: document.getElementById('statFeatures'),
        statChanges: document.getElementById('statChanges'),
        statDeprecations: document.getElementById('statDeprecations'),
        statCardAll: document.getElementById('statCardAll'),
        statCardFeature: document.getElementById('statCardFeature'),
        statCardChanged: document.getElementById('statCardChanged'),
        statCardDeprecated: document.getElementById('statCardDeprecated'),

        // Filters & Search
        searchInput: document.getElementById('searchInput'),
        clearSearchBtn: document.getElementById('clearSearchBtn'),
        filterPills: document.querySelectorAll('#filterPills .pill'),
        sortToggle: document.getElementById('sortToggle'),
        sortIcon: document.getElementById('sortIcon'),
        sortText: document.getElementById('sortText'),

        // States
        loadingState: document.getElementById('loadingState'),
        errorState: document.getElementById('errorState'),
        errorMessage: document.getElementById('errorMessage'),
        emptyState: document.getElementById('emptyState'),
        updatesFeed: document.getElementById('updatesFeed'),
        retryBtn: document.getElementById('retryBtn'),
        resetFiltersBtn: document.getElementById('resetFiltersBtn'),

        // Modal
        tweetModal: document.getElementById('tweetModal'),
        tweetTextarea: document.getElementById('tweetTextarea'),
        charCount: document.getElementById('charCount'),
        publishTweetBtn: document.getElementById('publishTweetBtn'),
        closeModalBtn: document.getElementById('closeModalBtn'),
        cancelTweetBtn: document.getElementById('cancelTweetBtn')
    };

    // Initialize lucide icons
    lucide.createIcons();

    // Load Initial Data
    fetchReleaseNotes(false);

    // Event Listeners
    elements.refreshBtn.addEventListener('click', () => fetchReleaseNotes(true));
    elements.retryBtn.addEventListener('click', () => fetchReleaseNotes(true));
    elements.resetFiltersBtn.addEventListener('click', resetFilters);
    
    // Search input handlers
    elements.searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.trim().toLowerCase();
        toggleClearSearchButton();
        renderFeed();
    });

    elements.clearSearchBtn.addEventListener('click', () => {
        elements.searchInput.value = '';
        state.searchQuery = '';
        toggleClearSearchButton();
        renderFeed();
        elements.searchInput.focus();
    });

    // Category pill filter handlers
    elements.filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            elements.filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            state.activeType = pill.getAttribute('data-type');
            renderFeed();
        });
    });

    // Stats card click handlers (triggers filtering)
    elements.statCardAll.addEventListener('click', () => triggerFilter('all'));
    elements.statCardFeature.addEventListener('click', () => triggerFilter('feature'));
    elements.statCardChanged.addEventListener('click', () => triggerFilter('changed'));
    elements.statCardDeprecated.addEventListener('click', () => triggerFilter('deprecated'));

    // Sort toggle
    elements.sortToggle.addEventListener('click', () => {
        if (state.sortOrder === 'desc') {
            state.sortOrder = 'asc';
            elements.sortText.textContent = 'Oldest First';
            elements.sortIcon.setAttribute('data-lucide', 'sort-asc');
        } else {
            state.sortOrder = 'desc';
            elements.sortText.textContent = 'Newest First';
            elements.sortIcon.setAttribute('data-lucide', 'sort-desc');
        }
        lucide.createIcons();
        renderFeed();
    });

    // Tweet Modal event listeners
    elements.closeModalBtn.addEventListener('click', closeTweetModal);
    elements.cancelTweetBtn.addEventListener('click', closeTweetModal);
    elements.tweetTextarea.addEventListener('input', handleTweetTextareaInput);
    elements.publishTweetBtn.addEventListener('click', publishTweet);

    // Close modal on click outside
    elements.tweetModal.addEventListener('click', (e) => {
        if (e.target === elements.tweetModal) {
            closeTweetModal();
        }
    });

    // Helper functions
    function toggleClearSearchButton() {
        if (state.searchQuery.length > 0) {
            elements.clearSearchBtn.style.display = 'flex';
        } else {
            elements.clearSearchBtn.style.display = 'none';
        }
    }

    function triggerFilter(type) {
        state.activeType = type;
        elements.filterPills.forEach(pill => {
            if (pill.getAttribute('data-type') === type) {
                pill.classList.add('active');
            } else {
                pill.classList.remove('active');
            }
        });
        renderFeed();
    }

    function resetFilters() {
        elements.searchInput.value = '';
        state.searchQuery = '';
        toggleClearSearchButton();
        triggerFilter('all');
    }

    // API Call: Fetch Release Notes
    function fetchReleaseNotes(forceRefresh = false) {
        // Start spinning refresh icon
        elements.refreshIcon.classList.add('icon-spin');
        elements.refreshBtn.disabled = true;
        
        // Show loading state
        elements.loadingState.classList.remove('hidden');
        elements.errorState.classList.add('hidden');
        elements.updatesFeed.classList.add('hidden');
        elements.emptyState.classList.add('hidden');

        let url = '/api/release-notes';
        if (forceRefresh) {
            url += '?refresh=true';
        }

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server error: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    state.allNotes = data.notes;
                    
                    // Update Cache Metadata
                    if (data.cached_at) {
                        elements.cacheStatus.textContent = `Sync: ${data.cached_at}`;
                    } else {
                        elements.cacheStatus.textContent = 'Sync: Live';
                    }

                    // Update stats
                    calculateStats();
                    
                    // Render UI feed
                    renderFeed();
                } else {
                    throw new Error(data.error || 'Failed to fetch release notes.');
                }
            })
            .catch(error => {
                console.error('Fetch error:', error);
                elements.errorMessage.textContent = error.message || 'An error occurred while communicating with the server.';
                elements.errorState.classList.remove('hidden');
                elements.loadingState.classList.add('hidden');
            })
            .finally(() => {
                // Stop spinning refresh icon
                elements.refreshIcon.classList.remove('icon-spin');
                elements.refreshBtn.disabled = false;
            });
    }

    // Stats Calculation
    function calculateStats() {
        const total = state.allNotes.length;
        const features = state.allNotes.filter(n => n.type.toLowerCase() === 'feature').length;
        const changes = state.allNotes.filter(n => n.type.toLowerCase() === 'changed').length;
        const deprecations = state.allNotes.filter(n => n.type.toLowerCase() === 'deprecated').length;

        animateCounter(elements.statTotal, total);
        animateCounter(elements.statFeatures, features);
        animateCounter(elements.statChanges, changes);
        animateCounter(elements.statDeprecations, deprecations);
    }

    // Sleek counter animation
    function animateCounter(element, target) {
        let current = 0;
        const duration = 800; // ms
        const stepTime = Math.max(Math.floor(duration / (target || 1)), 15);
        
        element.textContent = '0';
        if (target === 0) return;

        const timer = setInterval(() => {
            current += Math.ceil(target / (duration / stepTime));
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = current;
            }
        }, stepTime);
    }

    // Filter & Render Release Notes
    function renderFeed() {
        // Filter notes
        let notes = state.allNotes;

        // 1. Filter by category
        if (state.activeType !== 'all') {
            notes = notes.filter(n => n.type.toLowerCase() === state.activeType.toLowerCase());
        }

        // 2. Filter by search query
        if (state.searchQuery.length > 0) {
            notes = notes.filter(n => {
                const searchTxt = `${n.type} ${n.date} ${n.description}`.toLowerCase();
                return searchTxt.includes(state.searchQuery);
            });
        }

        // 3. Sort notes
        notes = [...notes]; // Clone array
        if (state.sortOrder === 'asc') {
            // Oldest first: we reverse the parsed order (which is newest first)
            notes.reverse();
        }

        // Update UI states
        elements.loadingState.classList.add('hidden');

        if (notes.length === 0) {
            elements.updatesFeed.classList.add('hidden');
            elements.emptyState.classList.remove('hidden');
            return;
        }

        elements.emptyState.classList.add('hidden');
        elements.updatesFeed.classList.remove('hidden');

        // Render Cards
        elements.updatesFeed.innerHTML = '';
        notes.forEach(note => {
            const card = createCardElement(note);
            elements.updatesFeed.appendChild(card);
        });

        // Initialize lucide icons for injected cards
        lucide.createIcons();
    }

    // HTML Card Factory
    function createCardElement(note) {
        const card = document.createElement('div');
        card.className = 'update-card';
        card.setAttribute('data-id', note.id);

        const typeClass = note.type.toLowerCase();
        
        card.innerHTML = `
            <div class="card-meta">
                <div class="card-meta-left">
                    <span class="type-badge ${typeClass}">${note.type}</span>
                    <span class="card-date">
                        <i data-lucide="calendar" style="width: 12px; height: 12px;"></i>
                        <span>${note.date}</span>
                    </span>
                </div>
                ${note.link ? `
                    <a href="${note.link}" target="_blank" class="card-source-link">
                        <span>Google Docs</span>
                        <i data-lucide="external-link" style="width: 12px; height: 12px;"></i>
                    </a>
                ` : ''}
            </div>
            <div class="card-content">
                ${note.description}
            </div>
            <div class="card-actions">
                <button class="btn-card-action btn-copy-link" title="Copy link to this update">
                    <i data-lucide="link" style="width: 14px; height: 14px;"></i>
                    <span>Copy Link</span>
                </button>
                <button class="btn-card-action btn-tweet-trigger">
                    <svg class="x-logo-btn-svg" viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                    </svg>
                    <span>Tweet Update</span>
                </button>
            </div>
        `;

        // Copy Link Action
        card.querySelector('.btn-copy-link').addEventListener('click', (e) => {
            const button = e.currentTarget;
            const originalHTML = button.innerHTML;
            
            let linkToCopy = note.link;
            if (!linkToCopy) {
                linkToCopy = window.location.href;
            }

            navigator.clipboard.writeText(linkToCopy)
                .then(() => {
                    button.innerHTML = `<i data-lucide="check" style="width: 14px; height: 14px; color: var(--accent-green);"></i><span style="color: var(--accent-green);">Copied!</span>`;
                    lucide.createIcons();
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        lucide.createIcons();
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy: ', err);
                });
        });

        // Tweet Trigger Action
        card.querySelector('.btn-tweet-trigger').addEventListener('click', () => {
            openTweetModal(note);
        });

        return card;
    }

    // HTML Content Extractor
    function getCleanText(htmlContent) {
        const temp = document.createElement('div');
        temp.innerHTML = htmlContent;
        // Clean up code blocks to format them inside text
        const codeElems = temp.querySelectorAll('code');
        codeElems.forEach(el => {
            el.textContent = `\`${el.textContent}\``;
        });
        
        let text = temp.textContent || temp.innerText || '';
        // Replace multiple newlines or spaces with single ones
        text = text.replace(/\s+/g, ' ').trim();
        return text;
    }

    // Twitter Modal Controller
    function openTweetModal(note) {
        state.selectedNote = note;
        
        // Extract clean text from release description
        let cleanText = getCleanText(note.description);
        
        // Build an elegant share tweet template
        // Format: "BigQuery Update [Date] - [Type]: [Short Description...] [Link] #BigQuery #GoogleCloud"
        const prefix = `BigQuery Update (${note.date}) • [${note.type}]: `;
        const hashtags = ` #BigQuery #GoogleCloud`;
        const link = note.link ? ` ${note.link}` : '';
        
        // Calculate maximum length available for description
        // Max Tweet = 280 chars
        const reservedLen = prefix.length + link.length + hashtags.length;
        const maxDescLen = 280 - reservedLen;
        
        let displayDesc = cleanText;
        if (cleanText.length > maxDescLen) {
            displayDesc = cleanText.substring(0, maxDescLen - 3) + '...';
        }
        
        const initialTweetText = `${prefix}${displayDesc}${link}${hashtags}`;
        
        elements.tweetTextarea.value = initialTweetText;
        elements.tweetModal.classList.remove('hidden');
        elements.tweetTextarea.focus();
        
        updateCharCount();
    }

    function closeTweetModal() {
        elements.tweetModal.classList.add('hidden');
        state.selectedNote = null;
    }

    function handleTweetTextareaInput() {
        updateCharCount();
    }

    function updateCharCount() {
        const text = elements.tweetTextarea.value;
        const len = text.length;
        elements.charCount.textContent = len;

        // Dynamic classes based on length limits
        elements.charCount.classList.remove('near-limit', 'over-limit');
        if (len > 250 && len <= 280) {
            elements.charCount.classList.add('near-limit');
            elements.publishTweetBtn.disabled = false;
        } else if (len > 280) {
            elements.charCount.classList.add('over-limit');
            elements.publishTweetBtn.disabled = true;
        } else if (len === 0) {
            elements.publishTweetBtn.disabled = true;
        } else {
            elements.publishTweetBtn.disabled = false;
        }
    }

    function publishTweet() {
        const tweetText = elements.tweetTextarea.value.trim();
        if (!tweetText || tweetText.length > 280) return;

        // Twitter Web Intent sharing URL
        const shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(tweetText)}`;
        window.open(shareUrl, '_blank', 'width=550,height=420,toolbar=0,status=0');
        
        closeTweetModal();
    }
});
