/**
 * MemeCLIP Integration for Advanced AI Reports
 * Handles image analysis, meme detection, and similarity search
 */

class MemeCLIPIntegration {
    constructor(aiReports) {
        this.aiReports = aiReports;
        this.analysisResults = [];
        this.init();
    }

    init() {
        this.setupImageUpload();
        console.log('MemeCLIP Integration initialized');
    }

    setupImageUpload() {
        const uploadZone = document.querySelector('.image-upload-zone');
        if (uploadZone) {
            // Drag and drop functionality
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('dragover');
            });

            uploadZone.addEventListener('dragleave', () => {
                uploadZone.classList.remove('dragover');
            });

            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleImageUpload(files[0]);
                }
            });
        }
    }

    async analyzeImage(input) {
        const file = input.files[0];
        if (!file) return;

        await this.handleImageUpload(file);
    }

    async handleImageUpload(file) {
        if (!this.isValidImageFile(file)) {
            this.aiReports.showError('Please upload a valid image file (JPG, PNG, WebP, GIF)');
            return;
        }

        try {
            this.aiReports.showLoading('Analyzing Image...', 'Running MemeCLIP analysis...');

            // Create FormData for file upload
            const formData = new FormData();
            formData.append('image', file);
            formData.append('analysis_type', 'full');

            const response = await fetch('/api/ai-reports/memeclip/analyze', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.displayAnalysisResult(result);
                this.analysisResults.push(result);
                this.aiReports.showSuccess('Image analysis completed!');
            } else {
                this.aiReports.showError(result.error || 'Image analysis failed');
            }
        } catch (error) {
            console.error('Error analyzing image:', error);
            this.aiReports.showError('Error analyzing image: ' + error.message);
        } finally {
            this.aiReports.hideLoading();
        }
    }

    displayAnalysisResult(result) {
        // Show results in the bottom popup
        if (this.aiReports && this.aiReports.showBottomPopup) {
            this.aiReports.showBottomPopup('MemeCLIP Analysis', 'popup-memeclip-tab');
        }
        
        const container = document.getElementById('popupMemeclipContent');
        if (!container) return;

        const resultHtml = `
            <div class="analysis-result fade-in">
                <div class="card bg-dark text-white">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-brain"></i> Analysis Result
                            <span class="badge bg-success ms-2">${result.confidence_score ? (result.confidence_score * 100).toFixed(1) + '%' : 'N/A'}</span>
                        </h6>
                    </div>
                    <div class="card-body">
                        ${this.renderAnalysisDetails(result)}
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = resultHtml;

        // Also update the MemeCLIP widget results
        const widgetContainer = document.getElementById('memeclipResults');
        if (widgetContainer) {
            widgetContainer.innerHTML = resultHtml;
            widgetContainer.style.display = 'block';
        }
    }

    renderAnalysisDetails(result) {
        let html = '';

        // Meme detection result
        if (result.meme_detected !== undefined) {
            html += `
                <div class="mb-3">
                    <strong>Meme Detection:</strong>
                    <span class="badge ${result.meme_detected ? 'bg-warning' : 'bg-success'} ms-2">
                        ${result.meme_detected ? 'Meme Detected' : 'Not a Meme'}
                    </span>
                </div>
            `;
        }

        // Classification results
        if (result.classification_result) {
            html += `
                <div class="mb-3">
                    <strong>Classification:</strong>
                    <div class="mt-2">
                        ${this.renderClassificationResults(result.classification_result)}
                    </div>
                </div>
            `;
        }

        // Similarity scores
        if (result.similarity_scores) {
            html += `
                <div class="mb-3">
                    <strong>Similarity Analysis:</strong>
                    <div class="mt-2">
                        ${this.renderSimilarityScores(result.similarity_scores)}
                    </div>
                </div>
            `;
        }

        // Analysis metadata
        html += `
            <div class="mt-3 pt-3 border-top">
                <small class="text-muted">
                    <i class="fas fa-clock"></i> Analyzed: ${new Date(result.analysis_timestamp || Date.now()).toLocaleString()}
                </small>
            </div>
        `;

        return html;
    }

    renderClassificationResults(classification) {
        if (Array.isArray(classification)) {
            return classification.map(item => `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span>${item.label || item.class || 'Unknown'}</span>
                    <span class="badge bg-info">${((item.score || item.confidence || 0) * 100).toFixed(1)}%</span>
                </div>
            `).join('');
        } else if (typeof classification === 'object') {
            return Object.entries(classification).map(([key, value]) => `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span>${key}</span>
                    <span class="badge bg-info">${typeof value === 'number' ? (value * 100).toFixed(1) + '%' : value}</span>
                </div>
            `).join('');
        }
        return '<span class="text-muted">No classification data available</span>';
    }

    renderSimilarityScores(similarity) {
        if (Array.isArray(similarity)) {
            return similarity.map(item => `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span>${item.image || item.id || 'Similar Image'}</span>
                    <span class="badge bg-warning">${((item.score || item.similarity || 0) * 100).toFixed(1)}%</span>
                </div>
            `).join('');
        }
        return '<span class="text-muted">No similarity data available</span>';
    }

    updateMemeCLIPTab(result) {
        const memeclipContent = document.getElementById('memeclipContent');
        if (!memeclipContent) return;

        const existingResults = memeclipContent.querySelector('.analysis-results') || document.createElement('div');
        existingResults.className = 'analysis-results';

        if (!memeclipContent.querySelector('.analysis-results')) {
            memeclipContent.innerHTML = `
                <div class="mb-3">
                    <button class="btn btn-primary me-2" onclick="searchSimilarImages()">
                        <i class="fas fa-search"></i> Search Similar
                    </button>
                    <button class="btn btn-info me-2" onclick="viewAnalysisResults()">
                        <i class="fas fa-chart-pie"></i> View Results
                    </button>
                    <button class="btn btn-success" onclick="exportMemeclipData()">
                        <i class="fas fa-download"></i> Export Data
                    </button>
                </div>
                <div class="analysis-results"></div>
            `;
        }

        const resultsContainer = memeclipContent.querySelector('.analysis-results');
        const newResult = document.createElement('div');
        newResult.className = 'card mb-3';
        newResult.innerHTML = `
            <div class="card-header">
                <h6 class="mb-0">
                    Analysis #${this.analysisResults.length}
                    <span class="badge bg-primary ms-2">${new Date().toLocaleTimeString()}</span>
                </h6>
            </div>
            <div class="card-body">
                ${this.renderAnalysisDetails(result)}
            </div>
        `;

        resultsContainer.insertBefore(newResult, resultsContainer.firstChild);
    }

    async batchAnalyzeImages() {
        try {
            this.aiReports.showLoading('Batch Analysis...', 'Analyzing multiple images from dataset...');

            const response = await fetch('/api/ai-reports/memeclip/batch-analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    dataset_id: this.aiReports.currentDataset?.id,
                    limit: 50,
                    analysis_type: 'full'
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.displayBatchResults(result);
                this.aiReports.showSuccess(`Batch analysis completed! Analyzed ${result.analyzed_count || 0} images.`);
            } else {
                this.aiReports.showError(result.error || 'Batch analysis failed');
            }
        } catch (error) {
            console.error('Error in batch analysis:', error);
            this.aiReports.showError('Error in batch analysis: ' + error.message);
        } finally {
            this.aiReports.hideLoading();
        }
    }

    displayBatchResults(result) {
        const memeclipContent = document.getElementById('memeclipContent');
        if (!memeclipContent) return;

        const batchResultsHtml = `
            <div class="batch-results card mb-3">
                <div class="card-header">
                    <h6 class="mb-0">
                        <i class="fas fa-layer-group"></i> Batch Analysis Results
                        <span class="badge bg-success ms-2">${result.analyzed_count || 0} images</span>
                    </h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Summary Statistics</h6>
                            <ul class="list-unstyled">
                                <li><i class="fas fa-images"></i> Total Analyzed: ${result.analyzed_count || 0}</li>
                                <li><i class="fas fa-laugh"></i> Memes Detected: ${result.memes_detected || 0}</li>
                                <li><i class="fas fa-flag"></i> Flagged Content: ${result.flagged_count || 0}</li>
                                <li><i class="fas fa-clock"></i> Processing Time: ${result.processing_time || 'N/A'}</li>
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h6>Top Classifications</h6>
                            ${this.renderTopClassifications(result.top_classifications)}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Insert at the top of the content
        const existingContent = memeclipContent.innerHTML;
        memeclipContent.innerHTML = batchResultsHtml + existingContent;
    }

    renderTopClassifications(classifications) {
        if (!classifications || !Array.isArray(classifications)) {
            return '<p class="text-muted">No classification data available</p>';
        }

        return `
            <div class="top-classifications">
                ${classifications.slice(0, 5).map(item => `
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span>${item.label || item.class}</span>
                        <span class="badge bg-info">${item.count || 0}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    async searchSimilarImages() {
        if (this.analysisResults.length === 0) {
            this.aiReports.showError('No analysis results available for similarity search');
            return;
        }

        try {
            this.aiReports.showLoading('Searching...', 'Finding similar images in dataset...');

            const lastResult = this.analysisResults[this.analysisResults.length - 1];
            
            const response = await fetch('/api/ai-reports/memeclip/search-similar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    reference_analysis_id: lastResult.id,
                    dataset_id: this.aiReports.currentDataset?.id,
                    similarity_threshold: 0.7,
                    limit: 20
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.displaySimilarityResults(result);
                this.aiReports.showSuccess(`Found ${result.similar_images?.length || 0} similar images!`);
            } else {
                this.aiReports.showError(result.error || 'Similarity search failed');
            }
        } catch (error) {
            console.error('Error in similarity search:', error);
            this.aiReports.showError('Error in similarity search: ' + error.message);
        } finally {
            this.aiReports.hideLoading();
        }
    }

    displaySimilarityResults(result) {
        const memeclipContent = document.getElementById('memeclipContent');
        if (!memeclipContent || !result.similar_images) return;

        const similarityHtml = `
            <div class="similarity-results card mb-3">
                <div class="card-header">
                    <h6 class="mb-0">
                        <i class="fas fa-search"></i> Similar Images
                        <span class="badge bg-info ms-2">${result.similar_images.length} found</span>
                    </h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        ${result.similar_images.map(img => `
                            <div class="col-md-4 mb-3">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <h6 class="card-title">${img.filename || 'Unknown'}</h6>
                                        <p class="card-text">
                                            <span class="badge bg-success">
                                                ${(img.similarity_score * 100).toFixed(1)}% similar
                                            </span>
                                        </p>
                                        <small class="text-muted">${img.source_url || 'No URL'}</small>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        // Insert at the top of the content
        const existingContent = memeclipContent.innerHTML;
        memeclipContent.innerHTML = similarityHtml + existingContent;
    }

    async viewAnalysisResults() {
        try {
            const response = await fetch(`/api/ai-reports/memeclip/results/${this.aiReports.currentDataset?.id || 'all'}`);
            const result = await response.json();

            if (response.ok && result.success) {
                this.displayAllResults(result.results);
            } else {
                this.aiReports.showError(result.error || 'Failed to load analysis results');
            }
        } catch (error) {
            console.error('Error loading analysis results:', error);
            this.aiReports.showError('Error loading analysis results: ' + error.message);
        }
    }

    displayAllResults(results) {
        const memeclipContent = document.getElementById('memeclipContent');
        if (!memeclipContent) return;

        const allResultsHtml = `
            <div class="all-results card mb-3">
                <div class="card-header">
                    <h6 class="mb-0">
                        <i class="fas fa-chart-pie"></i> All Analysis Results
                        <span class="badge bg-primary ms-2">${results?.length || 0} results</span>
                    </h6>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Image</th>
                                    <th>Meme</th>
                                    <th>Confidence</th>
                                    <th>Date</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${(results || []).map(result => `
                                    <tr>
                                        <td>${result.filename || 'Unknown'}</td>
                                        <td>
                                            <span class="badge ${result.meme_detected ? 'bg-warning' : 'bg-success'}">
                                                ${result.meme_detected ? 'Yes' : 'No'}
                                            </span>
                                        </td>
                                        <td>${((result.confidence_score || 0) * 100).toFixed(1)}%</td>
                                        <td>${new Date(result.analysis_timestamp).toLocaleDateString()}</td>
                                        <td>
                                            <button class="btn btn-sm btn-outline-primary" onclick="viewResultDetails(${result.id})">
                                                <i class="fas fa-eye"></i>
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        // Replace existing content
        memeclipContent.innerHTML = allResultsHtml;
    }

    async exportMemeclipData() {
        try {
            this.aiReports.showLoading('Exporting...', 'Preparing MemeCLIP analysis data...');

            const response = await fetch('/api/ai-reports/memeclip/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    dataset_id: this.aiReports.currentDataset?.id,
                    format: 'json',
                    include_images: false
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `memeclip_analysis_${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                this.aiReports.showSuccess('MemeCLIP data exported successfully!');
            } else {
                const result = await response.json();
                this.aiReports.showError(result.error || 'Export failed');
            }
        } catch (error) {
            console.error('Error exporting MemeCLIP data:', error);
            this.aiReports.showError('Error exporting data: ' + error.message);
        } finally {
            this.aiReports.hideLoading();
        }
    }

    isValidImageFile(file) {
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif', 'image/bmp'];
        return validTypes.includes(file.type);
    }
}

// Global functions for HTML onclick handlers
function analyzeImage(input) {
    if (window.aiReports && window.aiReports.memeclip) {
        window.aiReports.memeclip.analyzeImage(input);
    }
}

function batchAnalyzeImages() {
    if (window.aiReports && window.aiReports.memeclip) {
        window.aiReports.memeclip.batchAnalyzeImages();
    }
}

function searchSimilarImages() {
    if (window.aiReports && window.aiReports.memeclip) {
        window.aiReports.memeclip.searchSimilarImages();
    }
}

function viewAnalysisResults() {
    if (window.aiReports && window.aiReports.memeclip) {
        window.aiReports.memeclip.viewAnalysisResults();
    }
}

function exportMemeclipData() {
    if (window.aiReports && window.aiReports.memeclip) {
        window.aiReports.memeclip.exportMemeclipData();
    }
}

function viewResultDetails(resultId) {
    console.log('View result details for ID:', resultId);
    // Implementation for viewing detailed results
}

// Export for use in main AI Reports class
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MemeCLIPIntegration;
}
