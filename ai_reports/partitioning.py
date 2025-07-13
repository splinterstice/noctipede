"""Partitioning manager for datasets."""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core import get_logger
from database import get_db_session
from storage import get_storage_manager

logger = get_logger(__name__)


class PartitionManager:
    """Manages dataset partitioning for efficient querying and storage."""
    
    def __init__(self):
        self.storage_manager = get_storage_manager()
        self.supported_strategies = ['by_domain', 'by_date', 'by_network', 'by_content_type']
    
    def create_partition(self, dataset_id: int, partition_key: str, partition_value: str) -> Optional[int]:
        """
        Create a new partition for a dataset.
        
        Args:
            dataset_id: Dataset ID
            partition_key: Partition key (e.g., 'domain', 'date')
            partition_value: Partition value (e.g., 'example.com', '2024-01-01')
            
        Returns:
            Partition ID or None if failed
        """
        try:
            # Generate storage path for partition
            storage_path = self._generate_partition_path(dataset_id, partition_key, partition_value)
            
            with get_db_session() as session:
                # Check if partition already exists
                check_query = text("""
                    SELECT id FROM dataset_partitions
                    WHERE dataset_id = :dataset_id 
                    AND partition_key = :partition_key 
                    AND partition_value = :partition_value
                """)
                
                existing = session.execute(check_query, {
                    'dataset_id': dataset_id,
                    'partition_key': partition_key,
                    'partition_value': partition_value
                }).fetchone()
                
                if existing:
                    logger.debug(f"Partition already exists: {partition_key}={partition_value}")
                    return existing.id
                
                # Create new partition
                insert_query = text("""
                    INSERT INTO dataset_partitions (
                        dataset_id, partition_key, partition_value, storage_path, record_count
                    ) VALUES (
                        :dataset_id, :partition_key, :partition_value, :storage_path, 0
                    )
                """)
                
                result = session.execute(insert_query, {
                    'dataset_id': dataset_id,
                    'partition_key': partition_key,
                    'partition_value': partition_value,
                    'storage_path': storage_path
                })
                
                partition_id = result.lastrowid
                session.commit()
                
                # Create storage directory
                self._create_partition_storage(storage_path)
                
                logger.info(f"Created partition {partition_key}={partition_value} for dataset {dataset_id}")
                return partition_id
                
        except Exception as e:
            logger.error(f"Failed to create partition: {e}")
            return None
    
    def ensure_partition(self, dataset_id: int, partition_value: str, 
                        partition_strategy: str = 'by_domain') -> Optional[int]:
        """
        Ensure partition exists, create if it doesn't.
        
        Args:
            dataset_id: Dataset ID
            partition_value: Value to partition by
            partition_strategy: Partitioning strategy
            
        Returns:
            Partition ID or None if failed
        """
        try:
            partition_key = self._get_partition_key_from_strategy(partition_strategy)
            return self.create_partition(dataset_id, partition_key, partition_value)
            
        except Exception as e:
            logger.error(f"Failed to ensure partition: {e}")
            return None
    
    def get_dataset_partitions(self, dataset_id: int) -> List[Dict[str, Any]]:
        """Get all partitions for a dataset."""
        try:
            with get_db_session() as session:
                query = text("""
                    SELECT * FROM dataset_partitions
                    WHERE dataset_id = :dataset_id
                    ORDER BY partition_key, partition_value
                """)
                
                result = session.execute(query, {'dataset_id': dataset_id})
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get partitions for dataset {dataset_id}: {e}")
            return []
    
    def update_partition_stats(self, partition_id: int, record_count: int, 
                              size_bytes: Optional[int] = None) -> bool:
        """Update partition statistics."""
        try:
            with get_db_session() as session:
                update_fields = ["record_count = :record_count"]
                params = {
                    'partition_id': partition_id,
                    'record_count': record_count
                }
                
                if size_bytes is not None:
                    # Add size_bytes column if it doesn't exist
                    try:
                        session.execute(text("ALTER TABLE dataset_partitions ADD COLUMN size_bytes BIGINT"))
                        session.commit()
                    except:
                        pass  # Column might already exist
                    
                    update_fields.append("size_bytes = :size_bytes")
                    params['size_bytes'] = size_bytes
                
                query = text(f"""
                    UPDATE dataset_partitions 
                    SET {', '.join(update_fields)}
                    WHERE id = :partition_id
                """)
                
                result = session.execute(query, params)
                session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update partition stats: {e}")
            return False
    
    def delete_partition(self, partition_id: int) -> bool:
        """Delete a partition and cleanup storage."""
        try:
            # Get partition info first
            partition_info = self.get_partition_info(partition_id)
            if not partition_info:
                return False
            
            with get_db_session() as session:
                # Delete partition record
                query = text("DELETE FROM dataset_partitions WHERE id = :partition_id")
                result = session.execute(query, {'partition_id': partition_id})
                session.commit()
                
                if result.rowcount > 0:
                    # Cleanup storage
                    self._cleanup_partition_storage(partition_info['storage_path'])
                    logger.info(f"Deleted partition {partition_id}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete partition {partition_id}: {e}")
            return False
    
    def get_partition_info(self, partition_id: int) -> Optional[Dict[str, Any]]:
        """Get partition information by ID."""
        try:
            with get_db_session() as session:
                query = text("SELECT * FROM dataset_partitions WHERE id = :partition_id")
                result = session.execute(query, {'partition_id': partition_id}).fetchone()
                
                if result:
                    return dict(result._mapping)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get partition info: {e}")
            return None
    
    def optimize_partitions(self, dataset_id: int) -> Dict[str, Any]:
        """
        Optimize partitions by analyzing data distribution and suggesting improvements.
        
        Args:
            dataset_id: Dataset ID to optimize
            
        Returns:
            Optimization results and recommendations
        """
        try:
            partitions = self.get_dataset_partitions(dataset_id)
            
            if not partitions:
                return {'optimized': False, 'message': 'No partitions found'}
            
            # Analyze partition sizes
            partition_stats = []
            total_records = 0
            
            for partition in partitions:
                stats = {
                    'partition_id': partition['id'],
                    'partition_key': partition['partition_key'],
                    'partition_value': partition['partition_value'],
                    'record_count': partition['record_count'],
                    'size_bytes': partition.get('size_bytes', 0)
                }
                partition_stats.append(stats)
                total_records += partition['record_count']
            
            # Calculate statistics
            avg_records_per_partition = total_records / len(partitions) if partitions else 0
            
            # Find imbalanced partitions
            imbalanced_partitions = []
            for stats in partition_stats:
                if stats['record_count'] > avg_records_per_partition * 2:
                    imbalanced_partitions.append({
                        'partition': f"{stats['partition_key']}={stats['partition_value']}",
                        'record_count': stats['record_count'],
                        'recommendation': 'Consider sub-partitioning'
                    })
                elif stats['record_count'] < avg_records_per_partition * 0.1:
                    imbalanced_partitions.append({
                        'partition': f"{stats['partition_key']}={stats['partition_value']}",
                        'record_count': stats['record_count'],
                        'recommendation': 'Consider merging with other small partitions'
                    })
            
            # Generate recommendations
            recommendations = []
            
            if len(partitions) > 1000:
                recommendations.append("Consider using a different partitioning strategy - too many partitions")
            
            if len(partitions) < 5 and total_records > 100000:
                recommendations.append("Consider more granular partitioning for better query performance")
            
            if imbalanced_partitions:
                recommendations.append(f"Found {len(imbalanced_partitions)} imbalanced partitions")
            
            return {
                'optimized': True,
                'total_partitions': len(partitions),
                'total_records': total_records,
                'avg_records_per_partition': avg_records_per_partition,
                'imbalanced_partitions': imbalanced_partitions,
                'recommendations': recommendations,
                'partition_stats': partition_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize partitions for dataset {dataset_id}: {e}")
            return {'optimized': False, 'error': str(e)}
    
    def suggest_partitioning_strategy(self, dataset_id: int) -> Dict[str, Any]:
        """
        Analyze data and suggest optimal partitioning strategy.
        
        Args:
            dataset_id: Dataset ID to analyze
            
        Returns:
            Partitioning strategy recommendations
        """
        try:
            # Analyze data distribution
            with get_db_session() as session:
                # Analyze domain distribution
                domain_query = text("""
                    SELECT domain, COUNT(*) as count
                    FROM sites s
                    JOIN pages p ON s.id = p.site_id
                    GROUP BY domain
                    ORDER BY count DESC
                    LIMIT 20
                """)
                
                domain_result = session.execute(domain_query).fetchall()
                domain_distribution = [dict(row._mapping) for row in domain_result]
                
                # Analyze date distribution
                date_query = text("""
                    SELECT DATE(crawled_at) as crawl_date, COUNT(*) as count
                    FROM pages
                    WHERE crawled_at IS NOT NULL
                    GROUP BY DATE(crawled_at)
                    ORDER BY count DESC
                    LIMIT 20
                """)
                
                date_result = session.execute(date_query).fetchall()
                date_distribution = [dict(row._mapping) for row in date_result]
                
                # Analyze network type distribution
                network_query = text("""
                    SELECT network_type, COUNT(*) as count
                    FROM sites s
                    JOIN pages p ON s.id = p.site_id
                    GROUP BY network_type
                    ORDER BY count DESC
                """)
                
                network_result = session.execute(network_query).fetchall()
                network_distribution = [dict(row._mapping) for row in network_result]
            
            # Analyze distributions and make recommendations
            recommendations = []
            
            # Domain-based partitioning analysis
            if domain_distribution:
                max_domain_count = domain_distribution[0]['count']
                min_domain_count = domain_distribution[-1]['count']
                domain_ratio = max_domain_count / min_domain_count if min_domain_count > 0 else float('inf')
                
                if domain_ratio < 10 and len(domain_distribution) > 5:
                    recommendations.append({
                        'strategy': 'by_domain',
                        'score': 8,
                        'reason': 'Good domain distribution balance',
                        'estimated_partitions': len(domain_distribution)
                    })
                elif domain_ratio > 100:
                    recommendations.append({
                        'strategy': 'by_domain',
                        'score': 3,
                        'reason': 'Highly imbalanced domain distribution',
                        'estimated_partitions': len(domain_distribution)
                    })
            
            # Date-based partitioning analysis
            if date_distribution and len(date_distribution) > 3:
                recommendations.append({
                    'strategy': 'by_date',
                    'score': 7,
                    'reason': 'Good temporal distribution for time-series analysis',
                    'estimated_partitions': len(date_distribution)
                })
            
            # Network-based partitioning analysis
            if len(network_distribution) > 1:
                recommendations.append({
                    'strategy': 'by_network',
                    'score': 6,
                    'reason': 'Multiple network types present',
                    'estimated_partitions': len(network_distribution)
                })
            
            # Sort recommendations by score
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'analysis_completed': True,
                'domain_distribution': domain_distribution,
                'date_distribution': date_distribution,
                'network_distribution': network_distribution,
                'recommendations': recommendations,
                'suggested_strategy': recommendations[0]['strategy'] if recommendations else 'by_domain'
            }
            
        except Exception as e:
            logger.error(f"Failed to suggest partitioning strategy: {e}")
            return {
                'analysis_completed': False,
                'error': str(e),
                'suggested_strategy': 'by_domain'  # Default fallback
            }
    
    def rebalance_partitions(self, dataset_id: int, new_strategy: str) -> bool:
        """
        Rebalance existing partitions with a new strategy.
        
        Args:
            dataset_id: Dataset ID to rebalance
            new_strategy: New partitioning strategy
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if new_strategy not in self.supported_strategies:
                logger.error(f"Unsupported partitioning strategy: {new_strategy}")
                return False
            
            # Get current partitions
            current_partitions = self.get_dataset_partitions(dataset_id)
            
            if not current_partitions:
                logger.info("No existing partitions to rebalance")
                return True
            
            # Create backup of current partition info
            backup_info = {
                'timestamp': datetime.now().isoformat(),
                'dataset_id': dataset_id,
                'old_partitions': current_partitions,
                'new_strategy': new_strategy
            }
            
            # TODO: Implement actual data migration logic
            # This would involve:
            # 1. Reading data from existing partitions
            # 2. Re-partitioning according to new strategy
            # 3. Writing data to new partition structure
            # 4. Updating partition records
            # 5. Cleaning up old partitions
            
            logger.info(f"Rebalancing partitions for dataset {dataset_id} with strategy {new_strategy}")
            
            # For now, just update the dataset's partition strategy
            with get_db_session() as session:
                query = text("""
                    UPDATE datasets 
                    SET partition_strategy = :new_strategy, updated_at = NOW()
                    WHERE id = :dataset_id
                """)
                
                session.execute(query, {
                    'dataset_id': dataset_id,
                    'new_strategy': new_strategy
                })
                session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rebalance partitions: {e}")
            return False
    
    def _generate_partition_path(self, dataset_id: int, partition_key: str, partition_value: str) -> str:
        """Generate storage path for partition."""
        # Clean partition value for filesystem
        clean_value = partition_value.replace('/', '_').replace('\\', '_').replace(':', '_')
        return f"/app/datasets/dataset_{dataset_id}/{partition_key}={clean_value}"
    
    def _create_partition_storage(self, storage_path: str) -> None:
        """Create storage directory for partition."""
        try:
            os.makedirs(storage_path, exist_ok=True)
            
            # Create partition metadata file
            metadata = {
                'created_at': datetime.now().isoformat(),
                'storage_path': storage_path,
                'format': 'parquet'
            }
            
            metadata_file = os.path.join(storage_path, '_partition_info.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to create partition storage: {e}")
    
    def _cleanup_partition_storage(self, storage_path: str) -> None:
        """Cleanup partition storage directory."""
        try:
            if os.path.exists(storage_path):
                import shutil
                shutil.rmtree(storage_path)
                logger.debug(f"Cleaned up partition storage: {storage_path}")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup partition storage: {e}")
    
    def _get_partition_key_from_strategy(self, strategy: str) -> str:
        """Get partition key from strategy name."""
        strategy_mapping = {
            'by_domain': 'domain',
            'by_date': 'date',
            'by_network': 'network_type',
            'by_content_type': 'content_type'
        }
        
        return strategy_mapping.get(strategy, 'domain')
    
    def get_partition_statistics(self, dataset_id: int) -> Dict[str, Any]:
        """Get comprehensive partition statistics."""
        try:
            partitions = self.get_dataset_partitions(dataset_id)
            
            if not partitions:
                return {
                    'total_partitions': 0,
                    'total_records': 0,
                    'total_size_bytes': 0,
                    'partition_keys': [],
                    'largest_partition': None,
                    'smallest_partition': None
                }
            
            total_records = sum(p['record_count'] for p in partitions)
            total_size = sum(p.get('size_bytes', 0) for p in partitions)
            
            # Find largest and smallest partitions
            largest = max(partitions, key=lambda p: p['record_count'])
            smallest = min(partitions, key=lambda p: p['record_count'])
            
            # Get unique partition keys
            partition_keys = list(set(p['partition_key'] for p in partitions))
            
            return {
                'total_partitions': len(partitions),
                'total_records': total_records,
                'total_size_bytes': total_size,
                'partition_keys': partition_keys,
                'largest_partition': {
                    'key': f"{largest['partition_key']}={largest['partition_value']}",
                    'record_count': largest['record_count']
                },
                'smallest_partition': {
                    'key': f"{smallest['partition_key']}={smallest['partition_value']}",
                    'record_count': smallest['record_count']
                },
                'avg_records_per_partition': total_records / len(partitions),
                'partitions': partitions
            }
            
        except Exception as e:
            logger.error(f"Failed to get partition statistics: {e}")
            return {
                'total_partitions': 0,
                'total_records': 0,
                'error': str(e)
            }
