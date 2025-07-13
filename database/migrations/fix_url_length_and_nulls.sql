-- Fix URL column lengths and NULL values
-- Migration: fix_url_length_and_nulls.sql

-- Increase URL column sizes for long I2P URLs
ALTER TABLE sites MODIFY COLUMN url VARCHAR(2000);
ALTER TABLE pages MODIFY COLUMN url VARCHAR(2000);
ALTER TABLE media MODIFY COLUMN url VARCHAR(2000);

-- Fix NULL values in count columns
UPDATE sites SET crawl_count = 0 WHERE crawl_count IS NULL;
UPDATE sites SET error_count = 0 WHERE error_count IS NULL;
UPDATE sites SET page_count = 0 WHERE page_count IS NULL;

-- Ensure columns have proper defaults
ALTER TABLE sites MODIFY COLUMN crawl_count INT DEFAULT 0 NOT NULL;
ALTER TABLE sites MODIFY COLUMN error_count INT DEFAULT 0 NOT NULL;
ALTER TABLE sites MODIFY COLUMN page_count INT DEFAULT 0 NOT NULL;
