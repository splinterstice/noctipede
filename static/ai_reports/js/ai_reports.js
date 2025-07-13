/**
 * AI Reports JavaScript functionality
 */

class AIReportsManager {
    constructor() {
        this.selectedDatasetId = null;
        this.currentQueryResult = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadDatasets();
        this.loadQueryTemplates();
        this.setupMemeCLIP();
    }

    bindEvents() {
        // Dataset form submission
        document.getElementById('datasetForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createDataset();
        });

        // Query form submission
        document.getElementById('queryForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.executeQuery();
        });

        // Dataset management buttons
        document.getElementById('refreshDatasets').addEventListener('click', () => this.loadDatasets());
        document.getElementById('newDataset').addEventListener('click', () => this.showNewDatasetForm());
        document.getElementById('editDataset').addEventListener('click', () => this.editSelectedDataset());
        document.getElementById('deleteDataset').addEventListener('click', () => this.deleteSelectedDataset());
        document.getElementById('exportHive').addEventListener('click', () => this.exportToHive());

        // Report and screenshot buttons
        document.getElementById('generateReport').addEventListener('click', () => this.generateReport());
        document.getElementById('captureScreenshots').addEventListener('click', () => this.captureScreenshots());

        // MemeCLIP analysis
        document.getElementById('analyzeImages').addEventListener('click', () => this.analyzeImages());

        // Save dataset changes
        document.getElementById('saveDatasetChanges').addEventListener('click', () => this.saveDatasetChanges());

        // Save query
        document.getElementById('saveQuery').addEventListener('click', () => this.saveQuery());
        
        // Clear query
        document.getElementById('clearQuery').addEventListener('click', () => this.clearQuery());
    }

    async loadDatasets() {
        try {
            this.showLoading('datasetList');
            
            const response = await fetch('/api/ai-reports/datasets');
            const data = await response.json();
            
            if (data.success) {
                this.renderDatasetList(data.datasets);
                this.updateDatasetSelect(data.datasets);
            } else {
                this.showError('Failed to load datasets');
            }
        } catch (error) {
            console.error('Error loading datasets:', error);
            this.showError('Error loading datasets');
        }
    }

    renderDatasetList(datasets) {
        const container = document.getElementById('datasetList');
        
        if (datasets.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No datasets found</div>';
            return;
        }

        const html = datasets.map(dataset => `
            <div class="list-group-item list-group-item-action dataset-item" 
                 data-dataset-id="${dataset.id}" 
                 onclick="aiReports.selectDataset(${dataset.id})">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${dataset.name}</h6>
                    <small class="text-muted">${dataset.status}</small>
                </div>
                <p class="mb-1">${dataset.description || 'No description'}</p>
                <small class="text-muted">
                    Records: ${dataset.record_count || 0} | 
                    Created: ${new Date(dataset.created_at).toLocaleDateString()}
                </small>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    updateDatasetSelect(datasets) {
        const select = document.getElementById('queryDataset');
        select.innerHTML = '<option value="">Select Datasets...</option>';
        
        datasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset.id;
            option.textContent = `${dataset.name} (${dataset.record_count || 0} records)`;
            select.appendChild(option);
        });
    }

    selectDataset(datasetId) {
        // Remove previous selection
        document.querySelectorAll('.dataset-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add selection to clicked item
        const selectedItem = document.querySelector(`[data-dataset-id="${datasetId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
            this.selectedDatasetId = datasetId;
            
            // Enable management buttons
            document.getElementById('editDataset').disabled = false;
            document.getElementById('deleteDataset').disabled = false;
            document.getElementById('exportHive').disabled = false;
        }
    }

    async createDataset() {
        try {
            const formData = {
                name: document.getElementById('datasetName').value,
                description: document.getElementById('datasetDescription').value,
                partition_strategy: document.getElementById('partitionStrategy').value,
                auto_partition: true
            };

            const response = await fetch('/api/ai-reports/datasets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('datasetStatus', 'Dataset created successfully!');
                document.getElementById('datasetForm').reset();
                this.loadDatasets();
            } else {
                this.showError('datasetStatus', 'Failed to create dataset');
            }
        } catch (error) {
            console.error('Error creating dataset:', error);
            this.showError('datasetStatus', 'Error creating dataset');
        }
    }

    async executeQuery() {
        try {
            const sqlQuery = document.getElementById('sqlQuery').value;
            const selectedDatasets = Array.from(document.getElementById('queryDataset').selectedOptions)
                .map(option => parseInt(option.value))
                .filter(id => !isNaN(id));

            if (!sqlQuery.trim()) {
                this.showError('queryStatus', 'Please enter a SQL query');
                return;
            }

            this.showLoading('queryResults');
            this.showStatus('queryStatus', 'Executing query...', 'info');

            const response = await fetch('/api/ai-reports/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: sqlQuery,
                    context: `User query from AI Reports interface`
                })
            });

            const data = await response.json();

            if (data.success) {
                this.currentQueryResult = data;
                this.renderQueryResults(data);
                // For simple API, we don't have metadata.row_count, so use data stats
                const rowCount = data.data && data.data.stats ? data.data.stats.sites : 'N/A';
                this.showSuccess('queryStatus', `Query executed successfully! Data retrieved: ${rowCount} sites`);
            } else {
                this.showError('queryStatus', data.error || 'Query execution failed');
                this.showError('queryResults', data.error || 'Query execution failed');
            }
        } catch (error) {
            console.error('Error executing query:', error);
            this.showError('queryStatus', 'Error executing query');
            this.showError('queryResults', 'Error executing query');
        }
    }

    renderQueryResults(queryResult) {
        const container = document.getElementById('queryResults');
        
        // Check if this is a simple API response (has 'response' field with markdown)
        if (queryResult.response && typeof queryResult.response === 'string') {
            let html = `
                <div class="ai-response">
                    <div class="markdown-content">
                        ${this.renderMarkdown(queryResult.response)}
                    </div>
                </div>
            `;
            
            // If we have structured data, add interactive data sections
            if (queryResult.data) {
                html += this.renderStructuredData(queryResult.data);
            }
            
            container.innerHTML = html;
            return;
        }
        
        // Handle traditional tabular data (fallback)
        const data = queryResult.data || [];
        const columns = queryResult.columns || [];

        if (data.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No results found</div>';
            return;
        }

        // Create table
        let html = `
            <div class="table-responsive results-table">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            ${columns.map(col => `<th>${col}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
        `;

        data.slice(0, 100).forEach(row => { // Limit to first 100 rows for display
            html += '<tr>';
            columns.forEach(col => {
                let value = row[col];
                if (value === null || value === undefined) {
                    value = '';
                } else if (typeof value === 'string' && value.length > 100) {
                    value = value.substring(0, 100) + '...';
                }
                html += `<td>${this.escapeHtml(String(value))}</td>`;
            });
            html += '</tr>';
        });

        html += `
                    </tbody>
                </table>
            </div>
            <div class="mt-2 text-muted">
                Showing ${Math.min(100, data.length)} of ${data.length} results
                (Execution time: ${queryResult.metadata.execution_time_seconds}s)
            </div>
        `;

        container.innerHTML = html;
    }

    async generateReport() {
        if (!this.currentQueryResult) {
            this.showError('No query results available for report generation');
            return;
        }

        try {
            const reportConfig = {
                type: 'summary',
                format: 'html',
                title: 'Query Analysis Report',
                description: 'AI-generated analysis of query results'
            };

            this.showLoading('generatedReports');

            const response = await fetch('/api/ai-reports/reports/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query_result: this.currentQueryResult,
                    report_config: reportConfig
                })
            });

            const data = await response.json();

            if (data.success) {
                this.renderGeneratedReport(data.report);
                // Switch to reports tab
                document.getElementById('reports-tab').click();
            } else {
                this.showError('generatedReports', data.error || 'Report generation failed');
            }
        } catch (error) {
            console.error('Error generating report:', error);
            this.showError('generatedReports', 'Error generating report');
        }
    }

    renderGeneratedReport(report) {
        const container = document.getElementById('generatedReports');
        
        const html = `
            <div class="card">
                <div class="card-header">
                    <h5>${report.title}</h5>
                    <small class="text-muted">Generated: ${new Date().toLocaleString()}</small>
                </div>
                <div class="card-body">
                    ${report.content}
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    async captureScreenshots() {
        if (!this.currentQueryResult || !this.currentQueryResult.data) {
            this.showError('No query results available for screenshot capture');
            return;
        }

        try {
            // Extract URLs from query results
            const urls = this.currentQueryResult.data
                .filter(row => row.url)
                .slice(0, 10) // Limit to first 10 URLs
                .map(row => ({
                    url: row.url,
                    site_id: row.site_id || 0,
                    page_id: row.page_id || null,
                    dataset_id: this.selectedDatasetId
                }));

            if (urls.length === 0) {
                this.showError('No URLs found in query results');
                return;
            }

            this.showLoading('screenshotGallery');

            const response = await fetch('/api/ai-reports/screenshots/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ urls_info: urls })
            });

            const data = await response.json();

            if (data.success) {
                if (data.message) {
                    this.showInfo('Screenshot capture started in background');
                    // Poll for results
                    setTimeout(() => this.loadScreenshots(), 5000);
                } else {
                    this.renderScreenshots(data.results);
                }
                // Switch to screenshots tab
                document.getElementById('screenshots-tab').click();
            } else {
                this.showError('screenshotGallery', 'Screenshot capture failed');
            }
        } catch (error) {
            console.error('Error capturing screenshots:', error);
            this.showError('screenshotGallery', 'Error capturing screenshots');
        }
    }

    async loadScreenshots() {
        if (!this.selectedDatasetId) return;

        try {
            const response = await fetch(`/api/ai-reports/screenshots/dataset/${this.selectedDatasetId}`);
            const data = await response.json();

            if (data.success) {
                this.renderScreenshots(data.screenshots);
            }
        } catch (error) {
            console.error('Error loading screenshots:', error);
        }
    }

    renderScreenshots(screenshots) {
        const container = document.getElementById('screenshotGallery');

        if (!screenshots || screenshots.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No screenshots available</div>';
            return;
        }

        const html = screenshots.map(screenshot => `
            <div class="col-md-3 mb-3">
                <div class="card">
                    <img src="${screenshot.thumbnail_url || screenshot.screenshot_url}" 
                         class="card-img-top screenshot-preview" 
                         alt="Screenshot"
                         onclick="aiReports.showScreenshotModal('${screenshot.screenshot_url}', '${screenshot.url}')">
                    <div class="card-body p-2">
                        <small class="text-muted">${screenshot.url}</small>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = `<div class="row">${html}</div>`;
    }

    showScreenshotModal(screenshotUrl, originalUrl) {
        document.getElementById('screenshotPreview').src = screenshotUrl;
        document.getElementById('screenshotInfo').innerHTML = `<strong>URL:</strong> ${originalUrl}`;
        new bootstrap.Modal(document.getElementById('screenshotModal')).show();
    }

    async analyzeImages() {
        const fileInput = document.getElementById('imageUpload');
        const files = fileInput.files;

        if (files.length === 0) {
            this.showError('Please select images to analyze');
            return;
        }

        try {
            // For demo purposes, we'll simulate the analysis
            // In a real implementation, you'd upload the files and get paths
            const imagePaths = Array.from(files).map(file => `/tmp/${file.name}`);

            const response = await fetch('/api/ai-reports/memeclip/batch-analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_paths: imagePaths,
                    dataset_id: this.selectedDatasetId
                })
            });

            const data = await response.json();

            if (data.success) {
                this.renderMemeCLIPResults(data.results || []);
            } else {
                this.showError('memeclipResults', 'Image analysis failed');
            }
        } catch (error) {
            console.error('Error analyzing images:', error);
            this.showError('memeclipResults', 'Error analyzing images');
        }
    }

    renderMemeCLIPResults(results) {
        const container = document.getElementById('memeclipResults');
        
        if (results.length === 0) {
            container.innerHTML = '<small class="text-muted">No analysis results</small>';
            return;
        }

        const html = results.map((result, index) => `
            <div class="mb-2 p-2 bg-light rounded">
                <small>
                    <strong>Image ${index + 1}:</strong><br>
                    Meme: ${result.meme_detected ? 'Yes' : 'No'}<br>
                    Confidence: ${(result.confidence_score * 100).toFixed(1)}%
                </small>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    setupMemeCLIP() {
        // Initialize MemeCLIP iframe with a placeholder or actual MemeCLIP interface
        const frame = document.getElementById('memeclipFrame');
        // In a real implementation, this would load the MemeCLIP interface
        frame.src = 'data:text/html,<html><body style="margin:0;padding:20px;font-family:Arial;background:#f0f0f0;"><h4>MemeCLIP Interface</h4><p>Image analysis and meme detection interface would be loaded here.</p></body></html>';
    }

    async editSelectedDataset() {
        if (!this.selectedDatasetId) return;

        try {
            const response = await fetch(`/api/ai-reports/datasets/${this.selectedDatasetId}`);
            const data = await response.json();

            if (data.success) {
                const dataset = data.dataset;
                document.getElementById('editDatasetId').value = dataset.id;
                document.getElementById('editDatasetName').value = dataset.name;
                document.getElementById('editDatasetDescription').value = dataset.description || '';
                document.getElementById('editDatasetStatus').value = dataset.status;

                new bootstrap.Modal(document.getElementById('datasetModal')).show();
            }
        } catch (error) {
            console.error('Error loading dataset for edit:', error);
        }
    }

    async saveDatasetChanges() {
        try {
            const datasetId = document.getElementById('editDatasetId').value;
            const formData = {
                description: document.getElementById('editDatasetDescription').value,
                status: document.getElementById('editDatasetStatus').value
            };

            const response = await fetch(`/api/ai-reports/datasets/${datasetId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('datasetModal')).hide();
                this.loadDatasets();
                this.showSuccess('Dataset updated successfully');
            } else {
                this.showError('Failed to update dataset');
            }
        } catch (error) {
            console.error('Error saving dataset changes:', error);
            this.showError('Error saving dataset changes');
        }
    }

    async deleteSelectedDataset() {
        if (!this.selectedDatasetId) return;

        if (!confirm('Are you sure you want to delete this dataset? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`/api/ai-reports/datasets/${this.selectedDatasetId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                this.selectedDatasetId = null;
                this.loadDatasets();
                this.showSuccess('Dataset deleted successfully');
            } else {
                this.showError('Failed to delete dataset');
            }
        } catch (error) {
            console.error('Error deleting dataset:', error);
            this.showError('Error deleting dataset');
        }
    }

    async exportToHive() {
        if (!this.selectedDatasetId) return;

        try {
            const response = await fetch(`/api/ai-reports/datasets/${this.selectedDatasetId}/export-hive`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('HIVE export started in background');
            } else {
                this.showError('Failed to start HIVE export');
            }
        } catch (error) {
            console.error('Error exporting to HIVE:', error);
            this.showError('Error exporting to HIVE');
        }
    }

    saveQuery() {
        const query = document.getElementById('sqlQuery').value;
        if (query.trim()) {
            localStorage.setItem('savedQuery', query);
            this.showSuccess('queryStatus', 'Query saved locally');
        }
    }

    clearQuery() {
        document.getElementById('sqlQuery').value = '';
        document.getElementById('queryResults').innerHTML = '';
        document.getElementById('queryStatus').innerHTML = '';
    }

    async loadQueryTemplates() {
        try {
            const response = await fetch('/api/ai-reports/templates');
            const templates = await response.json();
            
            if (Array.isArray(templates)) {
                this.renderQueryTemplates(templates);
            } else {
                console.error('Invalid templates response:', templates);
                this.showTemplateError('Failed to load templates');
            }
        } catch (error) {
            console.error('Error loading query templates:', error);
            this.showTemplateError('Error loading templates');
        }
    }

    renderQueryTemplates(templates) {
        const container = document.getElementById('templatesContainer');
        
        if (templates.length === 0) {
            container.innerHTML = '<div class="text-muted text-center">No templates available</div>';
            return;
        }

        const groupedTemplates = this.groupTemplatesByCategory(templates);
        let html = '';

        Object.keys(groupedTemplates).forEach(category => {
            html += `
                <div class="mb-3">
                    <h6 class="text-primary mb-2">
                        <i class="fas fa-folder"></i> ${category}
                    </h6>
                    ${groupedTemplates[category].map(template => this.renderTemplateItem(template)).join('')}
                </div>
            `;
        });

        container.innerHTML = html;
        this.bindTemplateEvents();
    }

    groupTemplatesByCategory(templates) {
        const grouped = {};
        templates.forEach(template => {
            const category = template.category || 'General';
            if (!grouped[category]) {
                grouped[category] = [];
            }
            grouped[category].push(template);
        });
        return grouped;
    }

    renderTemplateItem(template) {
        const sqlEquivalent = template.sql_equivalent ? `
            <div class="mt-2">
                <small class="text-muted">SQL Equivalent:</small>
                <div class="template-query">
                    <code style="font-size: 0.8em;">${this.escapeHtml(template.sql_equivalent)}</code>
                </div>
            </div>
        ` : '';

        return `
            <div class="template-item">
                <div class="template-header" data-bs-toggle="collapse" data-bs-target="#template-${template.id}">
                    <div>
                        <strong>${template.name}</strong>
                        <span class="template-category ms-2">${template.category}</span>
                    </div>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="collapse template-body" id="template-${template.id}">
                    <p class="text-muted mb-2">${template.description}</p>
                    <div class="mb-2">
                        <small class="text-muted">Natural Language Query:</small>
                        <div class="template-query">
                            <code>${this.escapeHtml(template.query)}</code>
                        </div>
                    </div>
                    ${sqlEquivalent}
                    <div class="d-flex justify-content-end mt-2">
                        <button class="template-use-btn" data-query="${this.escapeHtml(template.query)}">
                            <i class="fas fa-play"></i> Use This Query
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    bindTemplateEvents() {
        document.querySelectorAll('.template-use-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.target.getAttribute('data-query');
                document.getElementById('sqlQuery').value = query;
                // Collapse the templates section
                const templatesCollapse = new bootstrap.Collapse(document.getElementById('queryTemplates'), {
                    hide: true
                });
                this.showSuccess('queryStatus', 'Template loaded! Click Execute Query to run it.');
            });
        });
    }

    showTemplateError(message) {
        const container = document.getElementById('templatesContainer');
        container.innerHTML = `
            <div class="alert alert-warning" role="alert">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </div>
        `;
    }

    showNewDatasetForm() {
        document.getElementById('datasetForm').reset();
        document.getElementById('datasetName').focus();
    }

    // Utility methods
    showLoading(elementId) {
        const element = document.getElementById(elementId);
        element.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
    }

    showError(elementId, message) {
        if (typeof elementId === 'string' && message) {
            const element = document.getElementById(elementId);
            element.innerHTML = `<div class="alert alert-danger">${message}</div>`;
        } else {
            // If only message provided, show as toast
            this.showToast(elementId, 'error');
        }
    }

    showSuccess(elementId, message) {
        if (typeof elementId === 'string' && message) {
            const element = document.getElementById(elementId);
            element.innerHTML = `<div class="alert alert-success">${message}</div>`;
        } else {
            this.showToast(elementId, 'success');
        }
    }

    showStatus(elementId, message, type = 'info') {
        const element = document.getElementById(elementId);
        element.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    }

    showInfo(message) {
        this.showToast(message, 'info');
    }

    showToast(message, type = 'info') {
        // Simple toast implementation
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
        toast.style.zIndex = '9999';
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    renderStructuredData(data) {
        let html = `
            <div class="structured-data-section mt-4">
                <h5 class="text-primary mb-3">
                    <i class="fas fa-chart-bar"></i> Interactive Data View
                </h5>
        `;

        // Render statistics if available
        if (data.stats) {
            html += this.renderStatsCards(data.stats);
        }

        // Render network distribution if available
        if (data.networks) {
            html += this.renderNetworkChart(data.networks);
        }

        // Render recent sites table if available
        if (data.recent_sites && data.recent_sites.length > 0) {
            html += this.renderRecentSitesTable(data.recent_sites);
        }

        html += `</div>`;
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
        // Simple markdown renderer for basic formatting
        return markdown
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^\* (.*$)/gim, '<li>$1</li>')
            .replace(/^- (.*$)/gim, '<li>$1</li>')
            .replace(/^\d+\. (.*$)/gim, '<li>$1</li>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
            .replace(/<\/ul>\s*<ul>/g, '')
            .replace(/^(.*)$/gm, '<p>$1</p>')
            .replace(/<p><h/g, '<h')
            .replace(/<\/h([1-6])><\/p>/g, '</h$1>')
            .replace(/<p><ul>/g, '<ul>')
            .replace(/<\/ul><\/p>/g, '</ul>')
            .replace(/<p><\/p>/g, '');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize AI Reports Manager
const aiReports = new AIReportsManager();
