"""Dataset management for AI Reports component."""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core import get_logger
from database import get_db_session, execute_with_retry
from storage import get_storage_manager
from .hive_exporter import HiveExporter
from .partitioning import PartitionManager

logger = get_logger(__name__)


class DatasetManager:
    """Manages dataset creation, updates, and operations."""
    
    def __init__(self):
        self.storage_manager = get_storage_manager()
        self.hive_exporter = HiveExporter()
        self.partition_manager = PartitionManager()
        self.base_storage_path = "/app/datasets"
    
    def create_dataset(self, config: Dict[str, Any]) -> int:
        """
        Create a new dataset with specified configuration.
        
        Args:
            config: Dataset configuration including name, description, schema, etc.
            
        Returns:
            Dataset ID
        """
        try:
            # Validate configuration
            self._validate_config(config)
            
            # Generate storage path
            storage_path = self._generate_storage_path(config['name'])
            
            # Create dataset record
            with get_db_session() as session:
                query = text("""
                    INSERT INTO datasets (
                        name, description, schema_definition, partition_strategy,
                        storage_path, created_by, status
                    ) VALUES (
                        :name, :description, :schema_definition, :partition_strategy,
                        :storage_path, :created_by, 'active'
                    )
                """)
                
                result = session.execute(query, {
                    'name': config['name'],
                    'description': config.get('description', ''),
                    'schema_definition': json.dumps(config.get('schema', {})),
                    'partition_strategy': config.get('partition_strategy', 'by_domain'),
                    'storage_path': storage_path,
                    'created_by': config.get('created_by', 'system')
                })
                
                dataset_id = result.lastrowid
                session.commit()
                
                logger.info(f"Created dataset {config['name']} with ID {dataset_id}")
                
                # Initialize partitions if specified
                if config.get('auto_partition', True):
                    self._initialize_partitions(dataset_id, config)
                
                return dataset_id
                
        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            raise
    
    def get_dataset(self, dataset_id: int) -> Optional[Dict[str, Any]]:
        """Get dataset details by ID."""
        try:
            with get_db_session() as session:
                query = text("""
                    SELECT * FROM datasets WHERE id = :dataset_id
                """)
                
                result = session.execute(query, {'dataset_id': dataset_id}).fetchone()
                
                if result:
                    return dict(result._mapping)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get dataset {dataset_id}: {e}")
            return None
    
    def list_datasets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all datasets, optionally filtered by status."""
        try:
            with get_db_session() as session:
                if status:
                    query = text("""
                        SELECT * FROM datasets 
                        WHERE status = :status 
                        ORDER BY created_at DESC
                    """)
                    result = session.execute(query, {'status': status})
                else:
                    query = text("""
                        SELECT * FROM datasets 
                        ORDER BY created_at DESC
                    """)
                    result = session.execute(query)
                
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []
    
    def update_dataset(self, dataset_id: int, config: Dict[str, Any]) -> bool:
        """Update dataset configuration."""
        try:
            with get_db_session() as session:
                # Build update query dynamically
                update_fields = []
                params = {'dataset_id': dataset_id}
                
                if 'description' in config:
                    update_fields.append("description = :description")
                    params['description'] = config['description']
                
                if 'schema' in config:
                    update_fields.append("schema_definition = :schema_definition")
                    params['schema_definition'] = json.dumps(config['schema'])
                
                if 'status' in config:
                    update_fields.append("status = :status")
                    params['status'] = config['status']
                
                if not update_fields:
                    return True
                
                update_fields.append("updated_at = NOW()")
                
                query = text(f"""
                    UPDATE datasets 
                    SET {', '.join(update_fields)}
                    WHERE id = :dataset_id
                """)
                
                result = session.execute(query, params)
                session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Updated dataset {dataset_id}")
                    return True
                else:
                    logger.warning(f"Dataset {dataset_id} not found for update")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to update dataset {dataset_id}: {e}")
            return False
    
    def delete_dataset(self, dataset_id: int) -> bool:
        """Delete dataset and cleanup storage."""
        try:
            # Get dataset info first
            dataset = self.get_dataset(dataset_id)
            if not dataset:
                logger.warning(f"Dataset {dataset_id} not found for deletion")
                return False
            
            with get_db_session() as session:
                # Delete related records first (foreign key constraints)
                cleanup_queries = [
                    "DELETE FROM dataset_partitions WHERE dataset_id = :dataset_id",
                    "DELETE FROM memeclip_analysis WHERE dataset_id = :dataset_id",
                    "DELETE FROM site_screenshots WHERE dataset_id = :dataset_id",
                    "DELETE FROM datasets WHERE id = :dataset_id"
                ]
                
                for query_text in cleanup_queries:
                    query = text(query_text)
                    session.execute(query, {'dataset_id': dataset_id})
                
                session.commit()
                
                # Cleanup storage
                self._cleanup_storage(dataset['storage_path'])
                
                logger.info(f"Deleted dataset {dataset_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete dataset {dataset_id}: {e}")
            return False
    
    def export_to_hive(self, dataset_id: int) -> Optional[str]:
        """Export dataset to HIVE format."""
        try:
            dataset = self.get_dataset(dataset_id)
            if not dataset:
                return None
            
            return self.hive_exporter.export_dataset(dataset_id, dataset)
            
        except Exception as e:
            logger.error(f"Failed to export dataset {dataset_id} to HIVE: {e}")
            return None
    
    def populate_from_crawl_data(self, dataset_id: int, filters: Dict[str, Any] = None) -> int:
        """Populate dataset with crawled data based on filters."""
        try:
            dataset = self.get_dataset(dataset_id)
            if not dataset:
                return 0
            
            # Build query based on filters
            base_query = """
                SELECT s.*, p.*, m.*
                FROM sites s
                LEFT JOIN pages p ON s.id = p.site_id
                LEFT JOIN media_files m ON p.id = m.page_id
                WHERE 1=1
            """
            
            params = {}
            
            if filters:
                if 'network_type' in filters:
                    base_query += " AND s.network_type = :network_type"
                    params['network_type'] = filters['network_type']
                
                if 'date_from' in filters:
                    base_query += " AND p.crawled_at >= :date_from"
                    params['date_from'] = filters['date_from']
                
                if 'date_to' in filters:
                    base_query += " AND p.crawled_at <= :date_to"
                    params['date_to'] = filters['date_to']
                
                if 'domains' in filters:
                    placeholders = ','.join([f':domain_{i}' for i in range(len(filters['domains']))])
                    base_query += f" AND s.domain IN ({placeholders})"
                    for i, domain in enumerate(filters['domains']):
                        params[f'domain_{i}'] = domain
            
            with get_db_session() as session:
                query = text(base_query)
                result = session.execute(query, params)
                
                # Process results and create partitions
                records_processed = 0
                for row in result:
                    # Create partition if needed
                    partition_value = self._get_partition_value(dict(row._mapping), dataset['partition_strategy'])
                    self.partition_manager.ensure_partition(dataset_id, partition_value)
                    
                    # Store data in appropriate format
                    # This would involve writing to MinIO in the correct partition structure
                    records_processed += 1
                
                # Update dataset record count
                update_query = text("""
                    UPDATE datasets 
                    SET record_count = :record_count, updated_at = NOW()
                    WHERE id = :dataset_id
                """)
                session.execute(update_query, {
                    'record_count': records_processed,
                    'dataset_id': dataset_id
                })
                session.commit()
                
                logger.info(f"Populated dataset {dataset_id} with {records_processed} records")
                return records_processed
                
        except Exception as e:
            logger.error(f"Failed to populate dataset {dataset_id}: {e}")
            return 0
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate dataset configuration."""
        required_fields = ['name']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate name uniqueness
        with get_db_session() as session:
            query = text("SELECT COUNT(*) as count FROM datasets WHERE name = :name")
            result = session.execute(query, {'name': config['name']}).fetchone()
            if result.count > 0:
                raise ValueError(f"Dataset name '{config['name']}' already exists")
    
    def _generate_storage_path(self, name: str) -> str:
        """Generate unique storage path for dataset."""
        # Create hash-based path to avoid conflicts
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.base_storage_path}/{name_hash}_{timestamp}"
    
    def _initialize_partitions(self, dataset_id: int, config: Dict[str, Any]) -> None:
        """Initialize partitions for new dataset."""
        strategy = config.get('partition_strategy', 'by_domain')
        
        if strategy == 'by_domain':
            # Create partitions for existing domains
            with get_db_session() as session:
                query = text("SELECT DISTINCT domain FROM sites WHERE domain IS NOT NULL")
                domains = session.execute(query).fetchall()
                
                for domain_row in domains:
                    self.partition_manager.create_partition(
                        dataset_id, 'domain', domain_row.domain
                    )
    
    def _get_partition_value(self, record: Dict[str, Any], strategy: str) -> str:
        """Get partition value for a record based on strategy."""
        if strategy == 'by_domain':
            return record.get('domain', 'unknown')
        elif strategy == 'by_date':
            crawled_at = record.get('crawled_at')
            if crawled_at:
                return crawled_at.strftime('%Y-%m-%d')
            return 'unknown'
        elif strategy == 'by_network':
            return record.get('network_type', 'unknown')
        else:
            return 'default'
    
    def _cleanup_storage(self, storage_path: str) -> None:
        """Cleanup storage files for deleted dataset."""
        try:
            # Remove from MinIO if applicable
            if self.storage_manager:
                # Implementation depends on storage structure
                pass
            
            # Remove local files if any
            path = Path(storage_path)
            if path.exists():
                import shutil
                shutil.rmtree(path)
                
        except Exception as e:
            logger.warning(f"Failed to cleanup storage at {storage_path}: {e}")
