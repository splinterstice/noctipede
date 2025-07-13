-- AI Reports Database Migration
-- This script adds the necessary tables for the AI Reports component

-- Dataset Management Tables
CREATE TABLE IF NOT EXISTS datasets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    schema_definition JSON,
    partition_strategy VARCHAR(50) DEFAULT 'by_domain',
    storage_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    record_count BIGINT DEFAULT 0,
    size_bytes BIGINT DEFAULT 0,
    
    INDEX idx_dataset_name (name),
    INDEX idx_dataset_status (status),
    INDEX idx_dataset_created_at (created_at)
);

-- Dataset Partitions for HIVE compatibility
CREATE TABLE IF NOT EXISTS dataset_partitions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    dataset_id INT NOT NULL,
    partition_key VARCHAR(255) NOT NULL,
    partition_value VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500),
    record_count BIGINT DEFAULT 0,
    size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    INDEX idx_partition_dataset_id (dataset_id),
    INDEX idx_partition_key_value (partition_key, partition_value),
    UNIQUE KEY unique_partition (dataset_id, partition_key, partition_value)
);

-- Query History and Management
CREATE TABLE IF NOT EXISTS query_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    query_text LONGTEXT NOT NULL,
    query_hash VARCHAR(64),
    dataset_ids JSON,
    execution_time_ms BIGINT,
    result_count BIGINT,
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    INDEX idx_query_hash (query_hash),
    INDEX idx_query_status (status),
    INDEX idx_query_created_at (created_at)
);

-- Screenshot Management
CREATE TABLE IF NOT EXISTS site_screenshots (
    id INT PRIMARY KEY AUTO_INCREMENT,
    site_id INT,
    page_id INT,
    dataset_id INT,
    screenshot_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    capture_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    viewport_width INT DEFAULT 1920,
    viewport_height INT DEFAULT 1080,
    file_size BIGINT,
    storage_path VARCHAR(500),
    
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    INDEX idx_screenshot_site_id (site_id),
    INDEX idx_screenshot_dataset_id (dataset_id),
    INDEX idx_screenshot_timestamp (capture_timestamp)
);

-- MemeCLIP Analysis Results
CREATE TABLE IF NOT EXISTS memeclip_analysis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    media_file_id INT,
    dataset_id INT,
    classification_result JSON,
    similarity_scores JSON,
    meme_detected BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT,
    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (media_file_id) REFERENCES media_files(id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    INDEX idx_memeclip_media_file_id (media_file_id),
    INDEX idx_memeclip_dataset_id (dataset_id),
    INDEX idx_memeclip_meme_detected (meme_detected),
    INDEX idx_memeclip_timestamp (analysis_timestamp)
);

-- Update existing user_queries table if it doesn't have all required columns
ALTER TABLE user_queries 
ADD COLUMN IF NOT EXISTS ai_model VARCHAR(100),
ADD COLUMN IF NOT EXISTS ai_prompt LONGTEXT,
ADD COLUMN IF NOT EXISTS ai_response LONGTEXT;

-- Update existing generated_reports table if it doesn't have all required columns  
ALTER TABLE generated_reports
ADD COLUMN IF NOT EXISTS data_json JSON,
ADD COLUMN IF NOT EXISTS data_sources JSON,
ADD COLUMN IF NOT EXISTS date_range_start TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS date_range_end TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS generation_time FLOAT,
ADD COLUMN IF NOT EXISTS file_size INT,
ADD COLUMN IF NOT EXISTS view_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS download_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS minio_bucket VARCHAR(100),
ADD COLUMN IF NOT EXISTS minio_object_name VARCHAR(500),
ADD COLUMN IF NOT EXISTS file_path VARCHAR(500),
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;

-- Query Templates for reusable queries
CREATE TABLE IF NOT EXISTS query_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    template_text LONGTEXT NOT NULL,
    parameters JSON,
    example_query TEXT,
    usage_count INT DEFAULT 0,
    last_used TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_template_name (name),
    INDEX idx_template_category (category),
    INDEX idx_template_is_active (is_active),
    INDEX idx_template_usage_count (usage_count)
);

-- Insert some default query templates
INSERT IGNORE INTO query_templates (name, description, category, template_text, example_query) VALUES
('Domain Analysis', 'Analyze crawled data by domain', 'analysis', 
 'SELECT domain, COUNT(*) as page_count, AVG(status_code) as avg_status FROM dataset_{dataset_id} WHERE domain LIKE ''%{domain_pattern}%'' GROUP BY domain ORDER BY page_count DESC LIMIT {limit}',
 'SELECT domain, COUNT(*) as page_count, AVG(status_code) as avg_status FROM dataset_1 WHERE domain LIKE ''%.onion%'' GROUP BY domain ORDER BY page_count DESC LIMIT 50'),

('Network Type Distribution', 'Analyze distribution across network types', 'network',
 'SELECT network_type, COUNT(*) as count, COUNT(DISTINCT domain) as unique_domains FROM dataset_{dataset_id} GROUP BY network_type',
 'SELECT network_type, COUNT(*) as count, COUNT(DISTINCT domain) as unique_domains FROM dataset_1 GROUP BY network_type'),

('Content Analysis', 'Analyze content types and sizes', 'content',
 'SELECT content_type, COUNT(*) as count, AVG(content_length) as avg_size FROM dataset_{dataset_id} WHERE content_type IS NOT NULL GROUP BY content_type ORDER BY count DESC',
 'SELECT content_type, COUNT(*) as count, AVG(content_length) as avg_size FROM dataset_1 WHERE content_type IS NOT NULL GROUP BY content_type ORDER BY count DESC'),

('Security Analysis', 'Find potentially suspicious content', 'security',
 'SELECT url, domain, title, status_code FROM dataset_{dataset_id} WHERE (title LIKE ''%hack%'' OR title LIKE ''%exploit%'' OR content LIKE ''%malware%'') AND status_code = 200 LIMIT {limit}',
 'SELECT url, domain, title, status_code FROM dataset_1 WHERE (title LIKE ''%hack%'' OR title LIKE ''%exploit%'' OR content LIKE ''%malware%'') AND status_code = 200 LIMIT 100'),

('Recent Activity', 'Show recently crawled content', 'temporal',
 'SELECT url, domain, title, crawled_at FROM dataset_{dataset_id} WHERE crawled_at >= DATE_SUB(NOW(), INTERVAL {days} DAY) ORDER BY crawled_at DESC LIMIT {limit}',
 'SELECT url, domain, title, crawled_at FROM dataset_1 WHERE crawled_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) ORDER BY crawled_at DESC LIMIT 100');

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sites_network_type ON sites(network_type);
CREATE INDEX IF NOT EXISTS idx_pages_content_type ON pages(content_type);
CREATE INDEX IF NOT EXISTS idx_pages_status_code ON pages(status_code);
CREATE INDEX IF NOT EXISTS idx_media_files_file_type ON media_files(file_type);

-- Add foreign key constraints if they don't exist
-- Note: These might fail if the referenced tables don't exist yet, so we use IF NOT EXISTS equivalent

-- Create a view for easy querying across all datasets
CREATE OR REPLACE VIEW dataset_summary AS
SELECT 
    d.id as dataset_id,
    d.name as dataset_name,
    d.status,
    d.partition_strategy,
    d.record_count,
    d.size_bytes,
    d.created_at,
    COUNT(dp.id) as partition_count,
    COUNT(ss.id) as screenshot_count,
    COUNT(ma.id) as memeclip_analysis_count
FROM datasets d
LEFT JOIN dataset_partitions dp ON d.id = dp.dataset_id
LEFT JOIN site_screenshots ss ON d.id = ss.dataset_id
LEFT JOIN memeclip_analysis ma ON d.id = ma.dataset_id
GROUP BY d.id, d.name, d.status, d.partition_strategy, d.record_count, d.size_bytes, d.created_at;

-- Migration completion marker
INSERT IGNORE INTO query_history (query_text, query_hash, status, created_by) 
VALUES ('AI Reports migration completed', MD5('ai_reports_migration'), 'completed', 'migration_script');
