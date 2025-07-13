/**
 * Advanced AI Reports JavaScript
 * Implements AWS Athena-like functionality with MemeCLIP integration
 */

class AdvancedAIReports {
    constructor() {
        this.currentDataset = null;
        this.sqlEditor = null;
        this.loadingModal = null;
        this.datasets = [];
        this.queryHistory = [];
        this.init();
    }

    init() {
        this.setupSQLEditor();
        this.setupEventListeners();
        this.loadDatasets();
        this.setupModals();
        this.setupPopupResize();
        console.log('Advanced AI Reports initialized');
    }

    setupSQLEditor() {
        // Initialize CodeMirror for SQL editing
        const textarea = document.getElementById('sqlEditor');
        if (textarea && typeof CodeMirror !== 'undefined') {
            this.sqlEditor = CodeMirror.fromTextArea(textarea, {
                mode: 'text/x-sql',
                theme: 'monokai',
                lineNumbers: true,
                autoCloseBrackets: true,
                matchBrackets: true,
                indentWithTabs: true,
                smartIndent: true,
                lineWrapping: true,
                foldGutter: true,
                gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"]
            });
            
            this.sqlEditor.setSize("100%", "200px");
            console.log('SQL Editor initialized');
        }
    }

    setupEventListeners() {
        // Dataset management events
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('dataset-item')) {
                this.selectDataset(e.target);
            }
        });

        // Image upload for MemeCLIP
        const imageUpload = document.getElementById('imageUpload');
        if (imageUpload) {
            imageUpload.addEventListener('change', (e) => {
                this.analyzeImage(e.target);
            });
        }
    }

    setupModals() {
        this.loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    }

    showLoading(text = 'Processing...', subtext = 'Please wait while we process your request.') {
        document.getElementById('loadingText').textContent = text;
        document.getElementById('loadingSubtext').textContent = subtext;
        this.loadingModal.show();
    }

    hideLoading() {
        this.loadingModal.hide();
    }

    async loadDatasets() {
        try {
            const response = await fetch('/api/ai-reports/datasets');
            if (response.ok) {
                this.datasets = await response.json();
                this.renderDatasets();
            } else {
                console.error('Failed to load datasets');
                this.showError('Failed to load datasets');
            }
        } catch (error) {
            console.error('Error loading datasets:', error);
            this.showError('Error loading datasets: ' + error.message);
        }
    }

    renderDatasets() {
        const container = document.getElementById('datasetList');
        if (!container) return;

        if (this.datasets.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-database fa-2x mb-2"></i>
                    <p>No datasets found</p>
                    <small>Create a dataset to get started</small>
                </div>
            `;
            return;
        }

        container.innerHTML = this.datasets.map(dataset => `
            <div class="dataset-item" data-id="${dataset.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${dataset.name}</h6>
                        <small class="text-muted">${dataset.description || 'No description'}</small>
                    </div>
                    <span class="badge bg-primary">${dataset.record_count || 0}</span>
                </div>
                <div class="mt-2">
                    <small class="text-muted">
                        <i class="fas fa-calendar"></i> ${new Date(dataset.created_at).toLocaleDateString()}
                        <span class="ms-2">
                            <i class="fas fa-hdd"></i> ${this.formatBytes(dataset.size_bytes || 0)}
                        </span>
                    </small>
                </div>
            </div>
        `).join('');
    }

    selectDataset(element) {
        // Remove active class from all items
        document.querySelectorAll('.dataset-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to selected item
        element.classList.add('active');
        
        // Set current dataset
        const datasetId = element.getAttribute('data-id');
        this.currentDataset = this.datasets.find(d => d.id == datasetId);
        
        console.log('Selected dataset:', this.currentDataset);
    }

    async createDataset() {
        const name = document.getElementById('datasetName').value.trim();
        const description = document.getElementById('datasetDescription').value.trim();
        const partitionStrategy = document.getElementById('partitionStrategy').value;

        if (!name) {
            this.showError('Dataset name is required');
            return;
        }

        try {
            this.showLoading('Creating Dataset...', 'Setting up partitions and schema...');
            
            const response = await fetch('/api/ai-reports/datasets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name,
                    description: description,
                    partition_strategy: partitionStrategy
                })
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showSuccess('Dataset created successfully!');
                this.loadDatasets(); // Refresh the list
                
                // Clear form
                document.getElementById('datasetName').value = '';
                document.getElementById('datasetDescription').value = '';
            } else {
                this.showError(result.error || 'Failed to create dataset');
            }
        } catch (error) {
            console.error('Error creating dataset:', error);
            this.showError('Error creating dataset: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async executeQuery() {
        if (!this.sqlEditor) {
            this.showError('SQL Editor not initialized');
            return;
        }

        const query = this.sqlEditor.getValue().trim();
        if (!query) {
            this.showError('Please enter a SQL query');
            return;
        }

        try {
            this.showLoading('Executing Query...', 'Running SQL against your datasets...');
            
            const response = await fetch('/api/ai-reports/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    dataset_id: this.currentDataset?.id,
                    context: 'SQL Query from Advanced AI Reports'
                })
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                this.displayQueryResults(result);
                this.addToQueryHistory(query, result);
                
                // Switch to data tab
                const dataTab = document.getElementById('data-tab');
                if (dataTab) {
                    dataTab.click();
                }
            } else {
                this.showError(result.error || 'Query execution failed');
            }
        } catch (error) {
            console.error('Error executing query:', error);
            this.showError('Error executing query: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    displayQueryResults(result) {
        // Show results in the bottom popup instead of the main area
        this.showBottomPopup('Query Results', 'popup-data-tab');
        
        const container = document.getElementById('popupQueryResults');
        if (!container) return;

        let html = '';

        // Show AI response if available
        if (result.response) {
            html += `
                <div class="alert alert-info">
                    <h6><i class="fas fa-robot"></i> AI Analysis</h6>
                    <div class="markdown-content">
                        ${this.renderMarkdown(result.response)}
                    </div>
                </div>
            `;
        }

        // Show structured data
        if (result.data) {
            html += this.renderStructuredData(result.data);
        }

        // Show raw query results if available
        if (result.query_results) {
            html += this.renderQueryTable(result.query_results);
        }

        container.innerHTML = html;
    }

    renderQueryTable(data) {
        if (!data || !Array.isArray(data) || data.length === 0) {
            return '<div class="alert alert-warning">No data returned from query</div>';
        }

        const columns = Object.keys(data[0]);
        
        return `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            ${columns.map(col => `<th>${col}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(row => `
                            <tr>
                                ${columns.map(col => `<td>${this.escapeHtml(String(row[col] || ''))}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderStructuredData(data) {
        let html = '<div class="structured-data-section">';

        // Render statistics cards
        if (data.stats) {
            html += this.renderStatsCards(data.stats);
        }

        // Render network distribution
        if (data.networks) {
            html += this.renderNetworkChart(data.networks);
        }

        // Render recent sites table
        if (data.recent_sites && data.recent_sites.length > 0) {
            html += this.renderRecentSitesTable(data.recent_sites);
        }

        html += '</div>';
        return html;
    }

    renderStatsCards(stats) {
        return `
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body text-center">
                            <h3>${stats.sites?.toLocaleString() || 0}</h3>
                            <p class="mb-0">Total Sites</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body text-center">
                            <h3>${stats.pages?.toLocaleString() || 0}</h3>
                            <p class="mb-0">Total Pages</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body text-center">
                            <h3>${stats.media?.toLocaleString() || 0}</h3>
                            <p class="mb-0">Media Files</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body text-center">
                            <h3>${stats.flagged_media?.toLocaleString() || 0}</h3>
                            <p class="mb-0">Flagged Media</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderNetworkChart(networks) {
        const total = (networks.clearnet || 0) + (networks.tor || 0) + (networks.i2p || 0);
        const clearnetPct = total > 0 ? ((networks.clearnet || 0) / total * 100).toFixed(1) : 0;
        const torPct = total > 0 ? ((networks.tor || 0) / total * 100).toFixed(1) : 0;
        const i2pPct = total > 0 ? ((networks.i2p || 0) / total * 100).toFixed(1) : 0;

        return `
            <div class="card mb-4">
                <div class="card-header">
                    <h6 class="mb-0"><i class="fas fa-network-wired"></i> Network Distribution</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <div class="progress mb-2" style="height: 30px;">
                                <div class="progress-bar bg-primary" role="progressbar" style="width: ${clearnetPct}%" 
                                     title="Clearnet: ${networks.clearnet || 0} sites (${clearnetPct}%)">
                                    Clearnet: ${networks.clearnet || 0}
                                </div>
                                <div class="progress-bar bg-dark" role="progressbar" style="width: ${torPct}%" 
                                     title="Tor: ${networks.tor || 0} sites (${torPct}%)">
                                    Tor: ${networks.tor || 0}
                                </div>
                                <div class="progress-bar bg-secondary" role="progressbar" style="width: ${i2pPct}%" 
                                     title="I2P: ${networks.i2p || 0} sites (${i2pPct}%)">
                                    I2P: ${networks.i2p || 0}
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="d-flex flex-column">
                                <small><span class="badge bg-primary">🌍</span> Clearnet: ${networks.clearnet || 0} (${clearnetPct}%)</small>
                                <small><span class="badge bg-dark">🧅</span> Tor: ${networks.tor || 0} (${torPct}%)</small>
                                <small><span class="badge bg-secondary">🌐</span> I2P: ${networks.i2p || 0} (${i2pPct}%)</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderRecentSitesTable(recentSites) {
        let html = `
            <div class="card mb-4">
                <div class="card-header">
                    <h6 class="mb-0"><i class="fas fa-clock"></i> Recent Activity</h6>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>Network</th>
                                    <th>URL</th>
                                    <th>Pages</th>
                                    <th>Last Crawled</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        recentSites.slice(0, 10).forEach(site => {
            const networkIcon = site.network_type === 'tor' ? '🧅' : 
                               site.network_type === 'i2p' ? '🌐' : '🌍';
            const networkBadge = site.network_type === 'tor' ? 'bg-dark' : 
                                site.network_type === 'i2p' ? 'bg-secondary' : 'bg-primary';
            
            const lastCrawled = new Date(site.last_crawled).toLocaleString();
            const shortUrl = site.url.length > 50 ? site.url.substring(0, 50) + '...' : site.url;
            
            html += `
                <tr>
                    <td><span class="badge ${networkBadge}">${networkIcon} ${site.network_type.toUpperCase()}</span></td>
                    <td><small title="${site.url}">${this.escapeHtml(shortUrl)}</small></td>
                    <td><span class="badge bg-info">${site.page_count || 0}</span></td>
                    <td><small>${lastCrawled}</small></td>
                </tr>
            `;
        });

        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        return html;
    }

    renderMarkdown(markdown) {
        return markdown
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^\* (.*$)/gim, '<li>$1</li>')
            .replace(/^\- (.*$)/gim, '<li>$1</li>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    formatQuery() {
        if (!this.sqlEditor) return;
        
        // Basic SQL formatting
        let query = this.sqlEditor.getValue();
        query = query
            .replace(/\bSELECT\b/gi, 'SELECT')
            .replace(/\bFROM\b/gi, '\nFROM')
            .replace(/\bWHERE\b/gi, '\nWHERE')
            .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
            .replace(/\bORDER BY\b/gi, '\nORDER BY')
            .replace(/\bLIMIT\b/gi, '\nLIMIT');
        
        this.sqlEditor.setValue(query);
    }

    showQueryHistory() {
        // Implementation for query history modal
        console.log('Query history:', this.queryHistory);
    }

    addToQueryHistory(query, result) {
        this.queryHistory.unshift({
            query: query,
            timestamp: new Date(),
            success: result.success,
            rowCount: result.query_results?.length || 0
        });
        
        // Keep only last 50 queries
        if (this.queryHistory.length > 50) {
            this.queryHistory = this.queryHistory.slice(0, 50);
        }
    }

    // Utility functions
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    showError(message) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0 position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-exclamation-triangle me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    showSuccess(message) {
        // Create success toast notification
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-check-circle me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    // Bottom Popup Management
    showBottomPopup(title, activeTab = null) {
        const popup = document.getElementById('bottomPopup');
        const mainContent = document.getElementById('mainContent');
        const popupTitle = document.getElementById('popupTitle');
        
        if (popup && mainContent) {
            // Update title
            if (popupTitle && title) {
                popupTitle.innerHTML = `<i class="fas fa-chart-bar"></i> ${title}`;
            }
            
            // Show popup
            popup.classList.add('show');
            mainContent.classList.add('popup-open');
            
            // Activate specific tab if provided
            if (activeTab) {
                const tabButton = document.getElementById(activeTab);
                if (tabButton) {
                    tabButton.click();
                }
            }
        }
    }

    hideBottomPopup() {
        const popup = document.getElementById('bottomPopup');
        const mainContent = document.getElementById('mainContent');
        
        if (popup && mainContent) {
            popup.classList.remove('show');
            mainContent.classList.remove('popup-open');
        }
    }

    setupPopupResize() {
        const resizeHandle = document.getElementById('resizeHandle');
        const popup = document.getElementById('bottomPopup');
        const mainContent = document.getElementById('mainContent');
        
        if (!resizeHandle || !popup || !mainContent) return;
        
        let isResizing = false;
        let startY = 0;
        let startHeight = 0;
        
        resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startY = e.clientY;
            startHeight = popup.offsetHeight;
            document.body.style.cursor = 'ns-resize';
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const deltaY = startY - e.clientY;
            const newHeight = Math.min(
                Math.max(startHeight + deltaY, 200), // Minimum 200px
                window.innerHeight * 0.8 // Maximum 80% of viewport
            );
            
            popup.style.height = `${newHeight}px`;
            mainContent.style.paddingBottom = `${newHeight}px`;
        });
        
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
            }
        });
    }
}

// Global functions for HTML onclick handlers
function createDataset() {
    if (window.aiReports) {
        window.aiReports.createDataset();
    }
}

function executeQuery() {
    if (window.aiReports) {
        window.aiReports.executeQuery();
    }
}

function formatQuery() {
    if (window.aiReports) {
        window.aiReports.formatQuery();
    }
}

function showQueryHistory() {
    if (window.aiReports) {
        window.aiReports.showQueryHistory();
    }
}

function refreshDatasets() {
    if (window.aiReports) {
        window.aiReports.loadDatasets();
    }
}

function closeBottomPopup() {
    if (window.aiReports) {
        window.aiReports.hideBottomPopup();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.aiReports = new AdvancedAIReports();
});
