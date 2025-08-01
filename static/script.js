// Resume Query Web Interface JavaScript

class ResumeQueryApp {
    constructor() {
        this.currentResults = [];
        this.currentMode = 'semantic';
        this.isSearching = false;
        
        this.initializeElements();
        this.bindEvents();
        this.loadDatabases();
        this.checkSystemHealth();
    }
    
    initializeElements() {
        // Search elements
        this.searchInput = document.getElementById('search-input');
        this.searchBtn = document.getElementById('search-btn');
        this.resultLimit = document.getElementById('result-limit');
        this.databaseSelect = document.getElementById('database-select');
        this.modeButtons = document.querySelectorAll('.mode-btn');
        this.rerankToggle = document.getElementById('enable-rerank');
        this.rerankModelSelector = document.getElementById('rerank-model');
        this.rerankContainer = document.querySelector('.rerank-toggle');
        
        // Weighted search elements
        this.weightedContainer = document.getElementById('weighted-search-container');
        this.skillsInput = document.getElementById('skills-input');
        this.experienceInput = document.getElementById('experience-input');
        this.companyInput = document.getElementById('company-input');
        this.educationInput = document.getElementById('education-input');
        this.skillsWeight = document.getElementById('skills-weight');
        this.experienceWeight = document.getElementById('experience-weight');
        this.companyWeight = document.getElementById('company-weight');
        this.educationWeight = document.getElementById('education-weight');
        this.thresholdSlider = document.getElementById('threshold-slider');
        
        // Results elements
        this.resultsHeader = document.getElementById('results-header');
        this.resultsTitle = document.getElementById('results-title');
        this.resultsInfo = document.getElementById('results-info');
        this.resultsContainer = document.getElementById('results-container');
        this.loadingSpinner = document.getElementById('loading');
        
        // Status elements
        this.statusDot = document.getElementById('status-dot');
        this.statusText = document.getElementById('status-text');
        
        // Modal elements
        this.modal = document.getElementById('candidate-modal');
        this.modalContent = document.getElementById('modal-body');
        this.modalName = document.getElementById('modal-candidate-name');
        this.modalEmail = document.getElementById('modal-candidate-email');
        this.closeModal = document.getElementById('close-modal');
    }
    
    bindEvents() {
        // Search events
        this.searchBtn.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        
        // Mode selection events
        this.modeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.selectMode(btn.dataset.mode));
        });
        
        // Database selection events
        this.databaseSelect.addEventListener('change', () => this.switchDatabase());
        
        // Weighted search events
        this.initializeWeightedSearchEvents();
        
        // Modal events
        this.closeModal.addEventListener('click', () => this.hideModal());
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.hideModal();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.hideModal();
        });
    }
    
    async checkSystemHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            if (data.status === 'ready') {
                this.updateStatus('ready', `Ready • ${data.total_chunks} chunks loaded`);
                if (!data.hybrid_search_available) {
                    this.disableMode('hybrid');
                    this.disableMode('bm25');
                }
                if (!data.reranking_available) {
                    this.disableReranking();
                }
            } else {
                this.updateStatus('error', 'System not ready');
            }
        } catch (error) {
            this.updateStatus('error', 'Connection failed');
            console.error('Health check failed:', error);
        }
    }
    
    updateStatus(status, text) {
        this.statusDot.className = `status-dot ${status}`;
        this.statusText.textContent = text;
    }
    
    async loadDatabases() {
        try {
            const response = await fetch('/api/databases');
            const data = await response.json();
            
            // Clear existing options
            this.databaseSelect.innerHTML = '';
            
            // Add database options
            data.databases.forEach(db => {
                const option = document.createElement('option');
                option.value = db.name;
                option.textContent = `${db.name} (${Math.round(db.size / 1024 / 1024)}MB)`;
                if (db.name === data.current) {
                    option.selected = true;
                }
                this.databaseSelect.appendChild(option);
            });
            
        } catch (error) {
            console.error('Failed to load databases:', error);
            this.databaseSelect.innerHTML = '<option value="">Error loading databases</option>';
        }
    }
    
    async switchDatabase() {
        const selectedDb = this.databaseSelect.value;
        if (!selectedDb) return;
        
        try {
            this.updateStatus('loading', 'Switching database...');
            
            const response = await fetch('/api/switch-database', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    database: selectedDb
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateStatus('ready', `Ready • ${data.total_chunks} chunks loaded`);
                // Clear any existing results
                this.resultsHeader.style.display = 'none';
                this.resultsContainer.innerHTML = '';
                this.currentResults = [];
            } else {
                this.updateStatus('error', data.error || 'Failed to switch database');
                console.error('Database switch failed:', data.error);
            }
            
        } catch (error) {
            this.updateStatus('error', 'Failed to switch database');
            console.error('Database switch error:', error);
        }
    }
    
    initializeWeightedSearchEvents() {
        // Weight slider events
        this.skillsWeight.addEventListener('input', () => {
            document.getElementById('skills-weight-value').textContent = this.skillsWeight.value + '%';
        });
        this.experienceWeight.addEventListener('input', () => {
            document.getElementById('experience-weight-value').textContent = this.experienceWeight.value + '%';
        });
        this.companyWeight.addEventListener('input', () => {
            document.getElementById('company-weight-value').textContent = this.companyWeight.value + '%';
        });
        this.educationWeight.addEventListener('input', () => {
            document.getElementById('education-weight-value').textContent = this.educationWeight.value + '%';
        });
        this.thresholdSlider.addEventListener('input', () => {
            document.getElementById('threshold-value').textContent = this.thresholdSlider.value + '%';
        });
    }
    
    selectMode(mode) {
        this.currentMode = mode;
        this.modeButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
        
        // Show/hide weighted search UI
        if (mode === 'weighted') {
            this.weightedContainer.style.display = 'block';
            this.searchInput.style.display = 'none';
        } else {
            this.weightedContainer.style.display = 'none';
            this.searchInput.style.display = 'block';
        }
    }
    
    disableMode(mode) {
        const btn = document.querySelector(`[data-mode="${mode}"]`);
        if (btn) {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.title = 'Elasticsearch required for this search mode';
        }
    }
    
    disableReranking() {
        if (this.rerankContainer) {
            this.rerankContainer.classList.add('disabled');
            this.rerankToggle.disabled = true;
            this.rerankToggle.checked = false;
            this.rerankModelSelector.disabled = true;
        }
    }
    
    async performSearch() {
        let searchPayload;
        
        if (this.currentMode === 'weighted') {
            // Validate weighted search inputs
            const criteria = {
                skills: this.skillsInput.value.trim(),
                experience: this.experienceInput.value.trim(),
                company: this.companyInput.value.trim(),
                education: this.educationInput.value.trim()
            };
            
            // Check if at least one criterion is provided
            if (!Object.values(criteria).some(val => val)) {
                this.showError('Please enter at least one search criterion');
                return;
            }
            
            const weights = {
                skills: parseFloat(this.skillsWeight.value) / 100,
                experience: parseFloat(this.experienceWeight.value) / 100,
                company: parseFloat(this.companyWeight.value) / 100,
                education: parseFloat(this.educationWeight.value) / 100
            };
            
            const threshold = parseFloat(this.thresholdSlider.value) / 100;
            
            searchPayload = {
                mode: 'weighted',
                criteria: criteria,
                weights: weights,
                threshold: threshold,
                limit: parseInt(this.resultLimit.value),
                rerank: this.rerankToggle.checked,
                rerank_model: this.rerankModelSelector.value
            };
        } else {
            // Regular search
            const query = this.searchInput.value.trim();
            if (!query) return;
            
            searchPayload = {
                query: query,
                mode: this.currentMode,
                limit: parseInt(this.resultLimit.value),
                rerank: this.rerankToggle.checked,
                rerank_model: this.rerankModelSelector.value
            };
        }
        
        if (this.isSearching) return;
        
        this.isSearching = true;
        this.showLoading();
        this.searchBtn.disabled = true;
        
        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(searchPayload)
            });
            
            if (!response.ok) {
                throw new Error(`Search failed: ${response.status}`);
            }
            
            const data = await response.json();
            this.currentResults = data.results;
            this.displayResults(data);
            
        } catch (error) {
            this.showError('Search failed: ' + error.message);
            console.error('Search error:', error);
        } finally {
            this.isSearching = false;
            this.hideLoading();
            this.searchBtn.disabled = false;
        }
    }
    
    showLoading() {
        this.loadingSpinner.style.display = 'block';
        this.resultsHeader.style.display = 'none';
        this.resultsContainer.innerHTML = '';
    }
    
    hideLoading() {
        this.loadingSpinner.style.display = 'none';
    }
    
    displayResults(data) {
        this.resultsHeader.style.display = 'block';
        this.resultsTitle.textContent = `Search Results for "${data.query}"`;
        
        // Update results info
        let infoText = `Found ${data.total} results using ${data.search_info.mode} search`;
        if (data.search_info.semantic_count !== undefined) {
            infoText += ` (${data.search_info.semantic_count} semantic, ${data.search_info.bm25_count} keyword)`;
        }
        if (data.search_info.reranked) {
            const modelName = data.search_info.rerank_metadata?.model || 'Cohere';
            const modelIcon = modelName === 'rerank-v3.5' ? '🚀' : 
                             modelName.includes('multilingual') ? '🌍' : 
                             modelName.includes('v2.0') ? '📝' : '🎯';
            infoText += ` • ${modelIcon} Reranked with ${modelName}`;
        }
        this.resultsInfo.textContent = infoText;
        
        // Display results
        if (data.results.length === 0) {
            this.resultsContainer.innerHTML = `
                <div class="no-results">
                    <h3>No candidates found</h3>
                    <p>Try different keywords or switch to a different search mode.</p>
                </div>
            `;
            return;
        }
        
        this.resultsContainer.innerHTML = data.results.map((result, index) => 
            this.createResultCard(result, index)
        ).join('');
        
        // Add click handlers to result cards
        document.querySelectorAll('.result-card').forEach((card, index) => {
            card.addEventListener('click', () => this.showCandidateDetails(data.results[index]));
        });
    }
    
    createResultCard(result, index) {
        const isCandidate = result.chunk_type === 'candidate_summary';
        const typeClass = isCandidate ? 'candidate' : 'position';
        const typeLabel = isCandidate ? '👤 Candidate Profile' : '💼 Job Experience';
        
        let title, subtitle;
        if (isCandidate) {
            title = result.name;
            subtitle = `📧 ${result.email}`;
        } else {
            title = `${result.metadata.company} - ${result.metadata.title}`;
            subtitle = `👤 ${result.name} • 📅 ${result.metadata.start_date} - ${result.metadata.end_date}`;
        }
        
        // Truncate content for preview
        const maxLength = 200;
        const content = result.content.length > maxLength 
            ? result.content.substring(0, maxLength) + '...'
            : result.content;
        
        return `
            <div class="result-card" data-index="${index}">
                <div class="result-header">
                    <div class="result-type ${typeClass}">${typeLabel}</div>
                    <div class="result-title">${this.escapeHtml(title)}</div>
                    <div class="result-subtitle">${this.escapeHtml(subtitle)}</div>
                    <div class="result-score">
                        ${result.weighted_score ? 
                            `⚖️ Weighted: ${result.weighted_score.toFixed(3)} • Similarity: ${result.similarity.toFixed(4)}` :
                            result.rerank_score ? 
                                `Rerank: ${result.rerank_score.toFixed(4)} • Similarity: ${result.similarity.toFixed(4)}` :
                                `Similarity: ${result.similarity.toFixed(4)}`
                        }
                    </div>
                </div>
                <div class="result-content">
                    ${this.escapeHtml(content).replace(/\\n/g, '<br>')}
                </div>
            </div>
        `;
    }
    
    async showCandidateDetails(result) {
        this.modalName.textContent = result.name;
        this.modalEmail.textContent = result.email;
        
        try {
            const response = await fetch(`/api/candidate/${result.candidate_id}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to load candidate details');
            }
            
            this.modalContent.innerHTML = this.createCandidateDetailHTML(data);
            this.showModal();
            
        } catch (error) {
            this.modalContent.innerHTML = `
                <div class="error-message">
                    Failed to load candidate details: ${error.message}
                </div>
            `;
            this.showModal();
        }
    }
    
    createCandidateDetailHTML(data) {
        let html = '';
        
        // Candidate summary
        if (data.summary) {
            html += `
                <div class="candidate-section">
                    <h3>📋 Profile Summary</h3>
                    <div class="position-item">
                        <div><strong>Location:</strong> ${this.escapeHtml(data.summary.location || 'Not specified')}</div>
                        <div><strong>Stage:</strong> ${this.escapeHtml(data.summary.stage || 'Not specified')}</div>
                        <div><strong>Headline:</strong> ${this.escapeHtml(data.summary.headline || 'Not specified')}</div>
                    </div>
                </div>
            `;
        }
        
        // Links section (always show for Lever profile link)
        html += `
            <div class="candidate-section">
                <h3>🔗 Links & Profiles</h3>
                <div class="links-container">
        `;
        
        // Add Lever profile link first
        const leverUrl = `https://hire.lever.co/candidates/${data.candidate_id}`;
        html += `
            <a href="${leverUrl}" target="_blank" rel="noopener noreferrer" class="link-item">
                <span class="link-icon">⚖️</span>
                <span class="link-label">Lever Profile</span>
                <span class="link-url">hire.lever.co</span>
            </a>
        `;
        
        // Add other links if they exist
        if (data.links && data.links.length > 0) {
            data.links.forEach(link => {
                const linkIcon = this.getLinkIcon(link.type);
                const linkLabel = this.getLinkLabel(link.type);
                html += `
                    <a href="${this.escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer" class="link-item">
                        <span class="link-icon">${linkIcon}</span>
                        <span class="link-label">${linkLabel}</span>
                        <span class="link-url">${this.escapeHtml(this.shortenUrl(link.url))}</span>
                    </a>
                `;
            });
        }
        
        html += `
                </div>
            </div>
        `;
        
        // Work experience
        if (data.positions && data.positions.length > 0) {
            html += `
                <div class="candidate-section">
                    <h3>💼 Work Experience (${data.total_positions} positions)</h3>
            `;
            
            data.positions.forEach(position => {
                html += `
                    <div class="position-item">
                        <div class="position-header">
                            <div class="position-title">${this.escapeHtml(position.title || 'Unknown Title')}</div>
                            <div class="position-company">${this.escapeHtml(position.company || 'Unknown Company')}</div>
                            <div class="position-duration">${this.escapeHtml(position.start_date || '')} - ${this.escapeHtml(position.end_date || 'Present')}</div>
                            ${position.location ? `<div class="position-duration">📍 ${this.escapeHtml(position.location)}</div>` : ''}
                        </div>
                        <div class="position-summary">
                            ${this.escapeHtml(position.summary || 'No description available').replace(/\\n/g, '<br>')}
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
        }
        
        // Education section
        if (data.education && data.education.length > 0) {
            html += `
                <div class="candidate-section">
                    <h3>🎓 Education (${data.total_education} entries)</h3>
            `;
            
            data.education.forEach(edu => {
                html += `
                    <div class="position-item">
                        <div class="position-header">
                            <div class="position-title">${this.escapeHtml(edu.school_name || 'Unknown School')}</div>
                            <div class="position-company">${this.escapeHtml(edu.degree || 'Unknown Degree')}</div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
        }
        
        return html || '<p>No detailed information available for this candidate.</p>';
    }
    
    showModal() {
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
    
    hideModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
    
    showError(message) {
        this.resultsContainer.innerHTML = `
            <div class="error-message">
                ${this.escapeHtml(message)}
            </div>
        `;
        this.resultsHeader.style.display = 'none';
    }
    
    getLinkIcon(linkType) {
        const icons = {
            'linkedin': '💼',
            'code_repository': '💻',
            'portfolio': '🌐',
            'twitter': '🐦',
            'instagram': '📷',
            'facebook': '📘',
            'other': '🔗'
        };
        return icons[linkType] || icons['other'];
    }
    
    getLinkLabel(linkType) {
        const labels = {
            'linkedin': 'LinkedIn',
            'code_repository': 'Code Repository',
            'portfolio': 'Portfolio',
            'twitter': 'Twitter',
            'instagram': 'Instagram',
            'facebook': 'Facebook',
            'other': 'Link'
        };
        return labels[linkType] || labels['other'];
    }
    
    shortenUrl(url) {
        try {
            const urlObj = new URL(url);
            let domain = urlObj.hostname.replace('www.', '');
            if (urlObj.pathname !== '/') {
                domain += urlObj.pathname;
            }
            return domain.length > 40 ? domain.substring(0, 37) + '...' : domain;
        } catch {
            return url.length > 40 ? url.substring(0, 37) + '...' : url;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new ResumeQueryApp();
});