"""HIVE format exporter for datasets."""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

from core import get_logger
from config import get_settings
from database import get_db_session
from storage import get_storage_manager
from sqlalchemy import text

logger = get_logger(__name__)


class HiveExporter:
    """Exports datasets to HIVE-compatible format with proper partitioning."""
    
    def __init__(self):
        self.settings = get_settings()
        self.storage_manager = get_storage_manager()
        self.base_export_path = getattr(self.settings, 'dataset_storage_path', '/app/datasets')
        
        # Ensure export directory exists
        os.makedirs(self.base_export_path, exist_ok=True)
    
    def export_dataset(self, dataset_id: int, dataset_info: Dict[str, Any]) -> Optional[str]:
        """
        Export dataset to HIVE format with partitioning.
        
        Args:
            dataset_id: Dataset ID to export
            dataset_info: Dataset metadata
            
        Returns:
            Export path or None if failed
        """
        try:
            logger.info(f"Starting HIVE export for dataset {dataset_id}")
            
            # Create export directory
            export_path = self._create_export_directory(dataset_id, dataset_info['name'])
            
            # Get partition strategy
            partition_strategy = dataset_info.get('partition_strategy', 'by_domain')
            
            # Load and partition data
            partitioned_data = self._load_partitioned_data(dataset_id, partition_strategy)
            
            if not partitioned_data:
                logger.warning(f"No data found for dataset {dataset_id}")
                return None
            
            # Export each partition
            exported_partitions = []
            for partition_key, partition_data in partitioned_data.items():
                partition_path = self._export_partition(
                    export_path, partition_key, partition_data, partition_strategy
                )
                if partition_path:
                    exported_partitions.append(partition_path)
            
            # Create HIVE metadata files
            self._create_hive_metadata(export_path, dataset_info, exported_partitions)
            
            # Upload to MinIO if available
            if self.storage_manager:
                self._upload_to_storage(export_path, dataset_id)
            
            # Update dataset record with export info
            self._update_dataset_export_info(dataset_id, export_path)
            
            logger.info(f"HIVE export completed for dataset {dataset_id}: {export_path}")
            return export_path
            
        except Exception as e:
            logger.error(f"Failed to export dataset {dataset_id} to HIVE: {e}")
            return None
    
    def create_external_table_ddl(self, dataset_id: int, table_name: Optional[str] = None) -> Optional[str]:
        """
        Generate CREATE EXTERNAL TABLE DDL for the exported dataset.
        
        Args:
            dataset_id: Dataset ID
            table_name: Optional custom table name
            
        Returns:
            DDL string or None if failed
        """
        try:
            # Get dataset info
            with get_db_session() as session:
                query = text("""
                    SELECT name, schema_definition, partition_strategy, storage_path
                    FROM datasets 
                    WHERE id = :dataset_id
                """)
                
                result = session.execute(query, {'dataset_id': dataset_id}).fetchone()
                
                if not result:
                    return None
                
                dataset_info = dict(result._mapping)
            
            # Generate table name
            if not table_name:
                table_name = f"dataset_{dataset_id}_{dataset_info['name'].replace('-', '_')}"
            
            # Parse schema
            schema = json.loads(dataset_info.get('schema_definition', '{}'))
            
            # Generate column definitions
            columns = self._generate_column_definitions(schema)
            
            # Generate partition columns
            partition_columns = self._generate_partition_columns(dataset_info['partition_strategy'])
            
            # Generate DDL
            ddl = self._build_create_table_ddl(
                table_name, columns, partition_columns, 
                dataset_info['storage_path'], dataset_id
            )
            
            return ddl
            
        except Exception as e:
            logger.error(f"Failed to generate DDL for dataset {dataset_id}: {e}")
            return None
    
    def validate_hive_export(self, export_path: str) -> Dict[str, Any]:
        """
        Validate HIVE export structure and data integrity.
        
        Args:
            export_path: Path to exported dataset
            
        Returns:
            Validation results
        """
        try:
            validation_results = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'partition_count': 0,
                'total_records': 0,
                'file_count': 0
            }
            
            export_dir = Path(export_path)
            
            # Check if export directory exists
            if not export_dir.exists():
                validation_results['valid'] = False
                validation_results['errors'].append(f"Export directory not found: {export_path}")
                return validation_results
            
            # Check for metadata files
            metadata_file = export_dir / '_metadata.json'
            if not metadata_file.exists():
                validation_results['warnings'].append("Metadata file not found")
            
            # Count partitions and files
            partition_dirs = [d for d in export_dir.iterdir() if d.is_dir() and not d.name.startswith('_')]
            validation_results['partition_count'] = len(partition_dirs)
            
            total_records = 0
            file_count = 0
            
            for partition_dir in partition_dirs:
                parquet_files = list(partition_dir.glob('*.parquet'))
                file_count += len(parquet_files)
                
                # Count records in parquet files
                for parquet_file in parquet_files:
                    try:
                        table = pq.read_table(parquet_file)
                        total_records += len(table)
                    except Exception as e:
                        validation_results['errors'].append(f"Failed to read {parquet_file}: {e}")
                        validation_results['valid'] = False
            
            validation_results['total_records'] = total_records
            validation_results['file_count'] = file_count
            
            # Validate schema consistency
            schema_validation = self._validate_schema_consistency(partition_dirs)
            validation_results.update(schema_validation)
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate HIVE export: {e}")
            return {
                'valid': False,
                'errors': [str(e)],
                'warnings': [],
                'partition_count': 0,
                'total_records': 0,
                'file_count': 0
            }
    
    def _create_export_directory(self, dataset_id: int, dataset_name: str) -> str:
        """Create directory structure for HIVE export."""
        # Create timestamp-based directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = dataset_name.replace(' ', '_').replace('-', '_')
        
        export_dir = os.path.join(
            self.base_export_path, 
            f"hive_export_{dataset_id}_{safe_name}_{timestamp}"
        )
        
        os.makedirs(export_dir, exist_ok=True)
        return export_dir
    
    def _load_partitioned_data(self, dataset_id: int, partition_strategy: str) -> Dict[str, pd.DataFrame]:
        """Load data from database and organize by partitions."""
        try:
            partitioned_data = {}
            
            with get_db_session() as session:
                # Base query to get all relevant data
                base_query = """
                    SELECT 
                        s.id as site_id,
                        s.url,
                        s.domain,
                        s.network_type,
                        s.last_crawled as site_last_crawled,
                        s.crawl_count,
                        s.page_count,
                        s.status as site_status,
                        p.id as page_id,
                        p.title,
                        p.content,
                        p.content_hash,
                        p.status_code,
                        p.crawled_at,
                        p.content_type,
                        p.content_length,
                        p.response_time,
                        p.language,
                        p.sentiment_score,
                        p.sentiment_label,
                        m.id as media_id,
                        m.filename as media_filename,
                        m.file_type,
                        m.mime_type,
                        m.file_size,
                        m.description as media_description,
                        m.analysis_score,
                        m.is_flagged
                    FROM sites s
                    LEFT JOIN pages p ON s.id = p.site_id
                    LEFT JOIN media_files m ON p.id = m.page_id
                    WHERE s.status = 'active'
                """
                
                # Add dataset-specific filtering if needed
                # This could be based on crawl sessions or other criteria
                
                query = text(base_query)
                result = session.execute(query)
                
                # Convert to DataFrame
                df = pd.DataFrame([dict(row._mapping) for row in result.fetchall()])
                
                if df.empty:
                    return {}
                
                # Partition data based on strategy
                if partition_strategy == 'by_domain':
                    for domain in df['domain'].dropna().unique():
                        partition_data = df[df['domain'] == domain].copy()
                        partitioned_data[f"domain={domain}"] = partition_data
                
                elif partition_strategy == 'by_date':
                    df['crawl_date'] = pd.to_datetime(df['crawled_at']).dt.date
                    for date in df['crawl_date'].dropna().unique():
                        partition_data = df[df['crawl_date'] == date].copy()
                        partitioned_data[f"date={date}"] = partition_data
                
                elif partition_strategy == 'by_network':
                    for network_type in df['network_type'].dropna().unique():
                        partition_data = df[df['network_type'] == network_type].copy()
                        partitioned_data[f"network_type={network_type}"] = partition_data
                
                else:
                    # Default: single partition
                    partitioned_data['default'] = df
                
                return partitioned_data
                
        except Exception as e:
            logger.error(f"Failed to load partitioned data: {e}")
            return {}
    
    def _export_partition(self, export_path: str, partition_key: str, 
                         data: pd.DataFrame, partition_strategy: str) -> Optional[str]:
        """Export a single partition to Parquet format."""
        try:
            # Create partition directory
            partition_dir = os.path.join(export_path, partition_key)
            os.makedirs(partition_dir, exist_ok=True)
            
            # Clean data for Parquet export
            cleaned_data = self._clean_data_for_parquet(data)
            
            # Convert to PyArrow table
            table = pa.Table.from_pandas(cleaned_data)
            
            # Write to Parquet
            parquet_file = os.path.join(partition_dir, 'data.parquet')
            pq.write_table(table, parquet_file, compression='snappy')
            
            # Create partition metadata
            metadata = {
                'partition_key': partition_key,
                'partition_strategy': partition_strategy,
                'record_count': len(cleaned_data),
                'file_size': os.path.getsize(parquet_file),
                'created_at': datetime.now().isoformat(),
                'schema': cleaned_data.dtypes.to_dict()
            }
            
            metadata_file = os.path.join(partition_dir, '_partition_metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.debug(f"Exported partition {partition_key} with {len(cleaned_data)} records")
            return partition_dir
            
        except Exception as e:
            logger.error(f"Failed to export partition {partition_key}: {e}")
            return None
    
    def _clean_data_for_parquet(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean DataFrame for Parquet export."""
        cleaned_df = df.copy()
        
        # Handle datetime columns
        datetime_columns = ['site_last_crawled', 'crawled_at']
        for col in datetime_columns:
            if col in cleaned_df.columns:
                cleaned_df[col] = pd.to_datetime(cleaned_df[col], errors='coerce')
        
        # Handle numeric columns
        numeric_columns = ['crawl_count', 'page_count', 'status_code', 'content_length', 
                          'response_time', 'sentiment_score', 'file_size', 'analysis_score']
        for col in numeric_columns:
            if col in cleaned_df.columns:
                cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
        
        # Handle boolean columns
        boolean_columns = ['is_flagged']
        for col in boolean_columns:
            if col in cleaned_df.columns:
                cleaned_df[col] = cleaned_df[col].astype(bool)
        
        # Handle text columns - ensure they're strings and handle nulls
        text_columns = ['url', 'domain', 'network_type', 'site_status', 'title', 
                       'content', 'content_hash', 'content_type', 'language', 
                       'sentiment_label', 'media_filename', 'file_type', 'mime_type', 
                       'media_description']
        for col in text_columns:
            if col in cleaned_df.columns:
                cleaned_df[col] = cleaned_df[col].astype(str).replace('nan', '')
        
        return cleaned_df
    
    def _create_hive_metadata(self, export_path: str, dataset_info: Dict[str, Any], 
                             partition_paths: List[str]) -> None:
        """Create HIVE-compatible metadata files."""
        try:
            # Create main metadata file
            metadata = {
                'dataset_id': dataset_info.get('id'),
                'dataset_name': dataset_info.get('name'),
                'export_timestamp': datetime.now().isoformat(),
                'partition_strategy': dataset_info.get('partition_strategy'),
                'partition_count': len(partition_paths),
                'partitions': []
            }
            
            # Add partition information
            for partition_path in partition_paths:
                partition_name = os.path.basename(partition_path)
                
                # Read partition metadata if available
                partition_metadata_file = os.path.join(partition_path, '_partition_metadata.json')
                if os.path.exists(partition_metadata_file):
                    with open(partition_metadata_file, 'r') as f:
                        partition_metadata = json.load(f)
                    metadata['partitions'].append(partition_metadata)
                else:
                    metadata['partitions'].append({'partition_key': partition_name})
            
            # Write main metadata
            metadata_file = os.path.join(export_path, '_metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            # Create HIVE-style _SUCCESS file
            success_file = os.path.join(export_path, '_SUCCESS')
            with open(success_file, 'w') as f:
                f.write(f"Export completed at {datetime.now().isoformat()}\n")
            
        except Exception as e:
            logger.error(f"Failed to create HIVE metadata: {e}")
    
    def _upload_to_storage(self, export_path: str, dataset_id: int) -> None:
        """Upload exported data to MinIO storage."""
        try:
            if not self.storage_manager:
                return
            
            export_dir = Path(export_path)
            
            # Upload all files recursively
            for file_path in export_dir.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(export_dir)
                    object_name = f"hive_exports/dataset_{dataset_id}/{relative_path}"
                    
                    self.storage_manager.upload_file(str(file_path), object_name)
            
            logger.info(f"Uploaded HIVE export for dataset {dataset_id} to storage")
            
        except Exception as e:
            logger.error(f"Failed to upload HIVE export to storage: {e}")
    
    def _update_dataset_export_info(self, dataset_id: int, export_path: str) -> None:
        """Update dataset record with export information."""
        try:
            with get_db_session() as session:
                query = text("""
                    UPDATE datasets 
                    SET updated_at = NOW()
                    WHERE id = :dataset_id
                """)
                
                session.execute(query, {'dataset_id': dataset_id})
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update dataset export info: {e}")
    
    def _generate_column_definitions(self, schema: Dict[str, Any]) -> List[str]:
        """Generate column definitions for CREATE TABLE DDL."""
        columns = []
        
        # Standard columns
        standard_columns = [
            "site_id BIGINT",
            "url STRING",
            "domain STRING", 
            "network_type STRING",
            "site_last_crawled TIMESTAMP",
            "crawl_count BIGINT",
            "page_count BIGINT",
            "site_status STRING",
            "page_id BIGINT",
            "title STRING",
            "content STRING",
            "content_hash STRING",
            "status_code BIGINT",
            "crawled_at TIMESTAMP",
            "content_type STRING",
            "content_length BIGINT",
            "response_time DOUBLE",
            "language STRING",
            "sentiment_score DOUBLE",
            "sentiment_label STRING",
            "media_id BIGINT",
            "media_filename STRING",
            "file_type STRING",
            "mime_type STRING",
            "file_size BIGINT",
            "media_description STRING",
            "analysis_score DOUBLE",
            "is_flagged BOOLEAN"
        ]
        
        columns.extend(standard_columns)
        
        # Add custom columns from schema
        if 'columns' in schema:
            for col_name, col_def in schema['columns'].items():
                col_type = self._map_column_type(col_def.get('type', 'string'))
                columns.append(f"{col_name} {col_type}")
        
        return columns
    
    def _generate_partition_columns(self, partition_strategy: str) -> List[str]:
        """Generate partition column definitions."""
        if partition_strategy == 'by_domain':
            return ["domain STRING"]
        elif partition_strategy == 'by_date':
            return ["date STRING"]
        elif partition_strategy == 'by_network':
            return ["network_type STRING"]
        else:
            return []
    
    def _map_column_type(self, pandas_type: str) -> str:
        """Map pandas/Python types to HIVE types."""
        type_mapping = {
            'string': 'STRING',
            'text': 'STRING',
            'integer': 'BIGINT',
            'int': 'BIGINT',
            'float': 'DOUBLE',
            'boolean': 'BOOLEAN',
            'bool': 'BOOLEAN',
            'datetime': 'TIMESTAMP',
            'timestamp': 'TIMESTAMP',
            'date': 'DATE'
        }
        
        return type_mapping.get(pandas_type.lower(), 'STRING')
    
    def _build_create_table_ddl(self, table_name: str, columns: List[str], 
                               partition_columns: List[str], storage_path: str, 
                               dataset_id: int) -> str:
        """Build CREATE EXTERNAL TABLE DDL statement."""
        
        # Build column list
        column_list = ",\n  ".join(columns)
        
        # Build partition clause
        partition_clause = ""
        if partition_columns:
            partition_list = ",\n  ".join(partition_columns)
            partition_clause = f"\nPARTITIONED BY (\n  {partition_list}\n)"
        
        # Build storage location
        if self.storage_manager:
            bucket_name = getattr(self.settings, 'minio_bucket_name', 'noctipede-data')
            location = f"s3a://{bucket_name}/hive_exports/dataset_{dataset_id}/"
        else:
            location = f"file://{storage_path}"
        
        ddl = f"""
CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
  {column_list}
){partition_clause}
STORED AS PARQUET
LOCATION '{location}'
TBLPROPERTIES (
  'parquet.compression'='SNAPPY',
  'created_by'='noctipede_hive_exporter',
  'created_at'='{datetime.now().isoformat()}'
);
"""
        
        return ddl.strip()
    
    def _validate_schema_consistency(self, partition_dirs: List[Path]) -> Dict[str, Any]:
        """Validate schema consistency across partitions."""
        try:
            schemas = []
            
            for partition_dir in partition_dirs:
                parquet_files = list(partition_dir.glob('*.parquet'))
                if parquet_files:
                    # Read schema from first parquet file
                    table = pq.read_table(parquet_files[0])
                    schemas.append(table.schema)
            
            if not schemas:
                return {'schema_consistent': True, 'schema_errors': []}
            
            # Check if all schemas are the same
            base_schema = schemas[0]
            schema_errors = []
            
            for i, schema in enumerate(schemas[1:], 1):
                if not schema.equals(base_schema):
                    schema_errors.append(f"Schema mismatch in partition {i}")
            
            return {
                'schema_consistent': len(schema_errors) == 0,
                'schema_errors': schema_errors
            }
            
        except Exception as e:
            return {
                'schema_consistent': False,
                'schema_errors': [f"Schema validation failed: {e}"]
            }
