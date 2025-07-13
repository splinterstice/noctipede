"""Query engine for AI Reports - Athena/Presto-like functionality."""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from sqlalchemy import text
import tempfile
import os

from core import get_logger
from config import get_settings
from database import get_db_session
from storage import get_storage_manager

logger = get_logger(__name__)


class QueryEngine:
    """
    Athena/Presto-like query engine for analyzing partitioned data in MinIO/S3.
    Provides SQL interface for querying crawled data stored in various formats.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.storage_manager = get_storage_manager()
        self.query_cache = {}
        self.cache_ttl = 3600  # 1 hour cache TTL
        
        # Configuration
        self.engine_type = getattr(self.settings, 'query_engine_type', 'pandas')  # pandas, trino, presto
        self.max_result_size = getattr(self.settings, 'max_query_result_size', 10000)
        self.query_timeout = getattr(self.settings, 'query_timeout_seconds', 300)
        
        self.setup_engine()
    
    def setup_engine(self) -> None:
        """Setup the query engine based on configuration."""
        try:
            if self.engine_type == 'trino':
                self._setup_trino()
            elif self.engine_type == 'presto':
                self._setup_presto()
            else:
                # Default to pandas-based querying
                self._setup_pandas()
                
            logger.info(f"Query engine initialized with {self.engine_type}")
            
        except Exception as e:
            logger.error(f"Failed to setup query engine: {e}")
            # Fallback to pandas
            self._setup_pandas()
    
    def execute_query(self, sql: str, dataset_ids: List[int] = None, cache_key: str = None) -> Dict[str, Any]:
        """
        Execute SQL query against partitioned data.
        
        Args:
            sql: SQL query string
            dataset_ids: Optional list of dataset IDs to query
            cache_key: Optional cache key for result caching
            
        Returns:
            Query result dictionary with data, metadata, and statistics
        """
        try:
            # Generate cache key if not provided
            if not cache_key:
                cache_key = self._generate_cache_key(sql, dataset_ids)
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info("Returning cached query result")
                return cached_result
            
            # Validate and parse query
            parsed_query = self._parse_query(sql)
            if not parsed_query['valid']:
                return {
                    'success': False,
                    'error': parsed_query['error'],
                    'data': [],
                    'metadata': {}
                }
            
            # Execute query based on engine type
            start_time = datetime.now()
            
            if self.engine_type in ['trino', 'presto']:
                result = self._execute_distributed_query(sql, dataset_ids)
            else:
                result = self._execute_pandas_query(sql, dataset_ids)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Prepare result
            query_result = {
                'success': True,
                'data': result['data'],
                'metadata': {
                    'row_count': len(result['data']) if result['data'] else 0,
                    'execution_time_seconds': execution_time,
                    'engine_type': self.engine_type,
                    'datasets_queried': dataset_ids or [],
                    'query_hash': cache_key,
                    'timestamp': datetime.now().isoformat()
                },
                'columns': result.get('columns', []),
                'query': sql
            }
            
            # Cache result
            self._cache_result(cache_key, query_result)
            
            # Store query history
            self._store_query_history(sql, dataset_ids, query_result)
            
            return query_result
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'metadata': {'execution_time_seconds': 0}
            }
    
    def get_available_tables(self, dataset_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of available tables/datasets for querying."""
        try:
            with get_db_session() as session:
                if dataset_id:
                    query = text("""
                        SELECT d.*, 
                               COUNT(dp.id) as partition_count
                        FROM datasets d
                        LEFT JOIN dataset_partitions dp ON d.id = dp.dataset_id
                        WHERE d.id = :dataset_id AND d.status = 'active'
                        GROUP BY d.id
                    """)
                    result = session.execute(query, {'dataset_id': dataset_id})
                else:
                    query = text("""
                        SELECT d.*, 
                               COUNT(dp.id) as partition_count
                        FROM datasets d
                        LEFT JOIN dataset_partitions dp ON d.id = dp.dataset_id
                        WHERE d.status = 'active'
                        GROUP BY d.id
                        ORDER BY d.created_at DESC
                    """)
                    result = session.execute(query)
                
                tables = []
                for row in result.fetchall():
                    table_info = dict(row._mapping)
                    
                    # Get schema information
                    schema_def = json.loads(table_info.get('schema_definition', '{}'))
                    table_info['schema'] = schema_def
                    
                    # Get partition information
                    partitions = self._get_table_partitions(table_info['id'])
                    table_info['partitions'] = partitions
                    
                    tables.append(table_info)
                
                return tables
                
        except Exception as e:
            logger.error(f"Failed to get available tables: {e}")
            return []
    
    def get_table_schema(self, dataset_id: int) -> Dict[str, Any]:
        """Get detailed schema information for a dataset/table."""
        try:
            with get_db_session() as session:
                query = text("""
                    SELECT schema_definition, partition_strategy
                    FROM datasets 
                    WHERE id = :dataset_id
                """)
                
                result = session.execute(query, {'dataset_id': dataset_id}).fetchone()
                
                if result:
                    schema = json.loads(result.schema_definition or '{}')
                    
                    # Add partition information
                    partitions = self._get_table_partitions(dataset_id)
                    
                    return {
                        'dataset_id': dataset_id,
                        'schema': schema,
                        'partition_strategy': result.partition_strategy,
                        'partitions': partitions,
                        'queryable_columns': self._get_queryable_columns(schema)
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get table schema for dataset {dataset_id}: {e}")
            return {}
    
    def get_query_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent query history."""
        try:
            with get_db_session() as session:
                query = text("""
                    SELECT * FROM query_history
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                
                result = session.execute(query, {'limit': limit})
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get query history: {e}")
            return []
    
    def create_table_from_dataset(self, dataset_id: int) -> bool:
        """Create external table definition for dataset (for distributed engines)."""
        try:
            if self.engine_type not in ['trino', 'presto']:
                return True  # Not needed for pandas engine
            
            dataset_info = self.get_table_schema(dataset_id)
            if not dataset_info:
                return False
            
            # Generate CREATE TABLE statement
            create_sql = self._generate_create_table_sql(dataset_id, dataset_info)
            
            # Execute table creation
            if self.engine_type == 'trino':
                return self._execute_trino_ddl(create_sql)
            elif self.engine_type == 'presto':
                return self._execute_presto_ddl(create_sql)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to create table for dataset {dataset_id}: {e}")
            return False
    
    def _setup_pandas(self) -> None:
        """Setup pandas-based query engine."""
        self.engine_type = 'pandas'
        # No additional setup needed for pandas
    
    def _setup_trino(self) -> None:
        """Setup Trino query engine."""
        try:
            import trino
            
            trino_url = getattr(self.settings, 'trino_coordinator_url', 'http://trino:8080')
            self.trino_conn = trino.dbapi.connect(
                host=trino_url.split('://')[1].split(':')[0],
                port=int(trino_url.split(':')[-1]),
                user='noctipede',
                catalog='hive',
                schema='default'
            )
            
        except ImportError:
            logger.warning("Trino not available, falling back to pandas")
            self._setup_pandas()
        except Exception as e:
            logger.error(f"Failed to setup Trino: {e}")
            self._setup_pandas()
    
    def _setup_presto(self) -> None:
        """Setup Presto query engine."""
        try:
            import prestodb
            
            presto_url = getattr(self.settings, 'presto_coordinator_url', 'http://presto:8080')
            self.presto_conn = prestodb.dbapi.connect(
                host=presto_url.split('://')[1].split(':')[0],
                port=int(presto_url.split(':')[-1]),
                user='noctipede',
                catalog='hive',
                schema='default'
            )
            
        except ImportError:
            logger.warning("Presto not available, falling back to pandas")
            self._setup_pandas()
        except Exception as e:
            logger.error(f"Failed to setup Presto: {e}")
            self._setup_pandas()
    
    def _execute_pandas_query(self, sql: str, dataset_ids: List[int] = None) -> Dict[str, Any]:
        """Execute query using pandas on data loaded from MinIO."""
        try:
            # Load data from specified datasets
            dataframes = {}
            
            if dataset_ids:
                for dataset_id in dataset_ids:
                    df = self._load_dataset_as_dataframe(dataset_id)
                    if df is not None:
                        dataframes[f'dataset_{dataset_id}'] = df
            else:
                # Load all active datasets
                tables = self.get_available_tables()
                for table in tables:
                    df = self._load_dataset_as_dataframe(table['id'])
                    if df is not None:
                        dataframes[f'dataset_{table["id"]}'] = df
            
            if not dataframes:
                return {'data': [], 'columns': []}
            
            # Execute query using pandas
            # This is a simplified implementation - real implementation would need
            # a proper SQL parser and executor for pandas
            
            # For now, return sample data
            sample_df = list(dataframes.values())[0]
            
            return {
                'data': sample_df.head(self.max_result_size).to_dict('records'),
                'columns': list(sample_df.columns)
            }
            
        except Exception as e:
            logger.error(f"Pandas query execution failed: {e}")
            raise
    
    def _execute_distributed_query(self, sql: str, dataset_ids: List[int] = None) -> Dict[str, Any]:
        """Execute query using Trino/Presto."""
        try:
            if self.engine_type == 'trino':
                cursor = self.trino_conn.cursor()
            else:
                cursor = self.presto_conn.cursor()
            
            cursor.execute(sql)
            
            # Fetch results
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            data = []
            for row in rows[:self.max_result_size]:
                data.append(dict(zip(columns, row)))
            
            return {
                'data': data,
                'columns': columns
            }
            
        except Exception as e:
            logger.error(f"Distributed query execution failed: {e}")
            raise
    
    def _load_dataset_as_dataframe(self, dataset_id: int) -> Optional[pd.DataFrame]:
        """Load dataset from MinIO as pandas DataFrame."""
        try:
            # Get dataset information
            with get_db_session() as session:
                query = text("""
                    SELECT storage_path, partition_strategy
                    FROM datasets 
                    WHERE id = :dataset_id
                """)
                
                result = session.execute(query, {'dataset_id': dataset_id}).fetchone()
                
                if not result:
                    return None
                
                # Load data from storage
                # This is a placeholder - actual implementation would depend on
                # how data is stored in MinIO (Parquet, JSON, etc.)
                
                # For now, load from database as fallback
                data_query = text("""
                    SELECT s.url, s.domain, s.network_type, s.last_crawled,
                           p.title, p.content, p.crawled_at, p.status_code,
                           m.filename, m.file_type, m.file_size
                    FROM sites s
                    LEFT JOIN pages p ON s.id = p.site_id
                    LEFT JOIN media_files m ON p.id = m.page_id
                    LIMIT 1000
                """)
                
                df_result = session.execute(data_query)
                df = pd.DataFrame([dict(row._mapping) for row in df_result.fetchall()])
                
                return df
                
        except Exception as e:
            logger.error(f"Failed to load dataset {dataset_id} as DataFrame: {e}")
            return None
    
    def _parse_query(self, sql: str) -> Dict[str, Any]:
        """Parse and validate SQL query."""
        try:
            # Basic validation
            sql = sql.strip()
            if not sql:
                return {'valid': False, 'error': 'Empty query'}
            
            # Check for dangerous operations
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
            sql_upper = sql.upper()
            
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return {'valid': False, 'error': f'Operation {keyword} not allowed'}
            
            return {'valid': True, 'parsed_sql': sql}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _get_table_partitions(self, dataset_id: int) -> List[Dict[str, Any]]:
        """Get partition information for a dataset."""
        try:
            with get_db_session() as session:
                query = text("""
                    SELECT partition_key, partition_value, record_count, created_at
                    FROM dataset_partitions
                    WHERE dataset_id = :dataset_id
                    ORDER BY partition_key, partition_value
                """)
                
                result = session.execute(query, {'dataset_id': dataset_id})
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get partitions for dataset {dataset_id}: {e}")
            return []
    
    def _get_queryable_columns(self, schema: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract queryable columns from schema definition."""
        columns = []
        
        # Standard columns always available
        standard_columns = [
            {'name': 'url', 'type': 'string', 'description': 'Site URL'},
            {'name': 'domain', 'type': 'string', 'description': 'Site domain'},
            {'name': 'network_type', 'type': 'string', 'description': 'Network type (clearnet, tor, i2p)'},
            {'name': 'title', 'type': 'string', 'description': 'Page title'},
            {'name': 'content', 'type': 'text', 'description': 'Page content'},
            {'name': 'crawled_at', 'type': 'timestamp', 'description': 'Crawl timestamp'},
            {'name': 'status_code', 'type': 'integer', 'description': 'HTTP status code'}
        ]
        
        columns.extend(standard_columns)
        
        # Add schema-specific columns
        if 'columns' in schema:
            for col_name, col_def in schema['columns'].items():
                columns.append({
                    'name': col_name,
                    'type': col_def.get('type', 'string'),
                    'description': col_def.get('description', '')
                })
        
        return columns
    
    def _generate_cache_key(self, sql: str, dataset_ids: List[int] = None) -> str:
        """Generate cache key for query result."""
        cache_input = f"{sql}_{dataset_ids or []}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached query result if available and not expired."""
        if cache_key in self.query_cache:
            cached_data = self.query_cache[cache_key]
            if datetime.now().timestamp() - cached_data['timestamp'] < self.cache_ttl:
                return cached_data['result']
            else:
                # Remove expired cache
                del self.query_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache query result."""
        self.query_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now().timestamp()
        }
        
        # Limit cache size
        if len(self.query_cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(
                self.query_cache.keys(),
                key=lambda k: self.query_cache[k]['timestamp']
            )[:20]
            
            for key in oldest_keys:
                del self.query_cache[key]
    
    def _store_query_history(self, sql: str, dataset_ids: List[int], result: Dict[str, Any]) -> None:
        """Store query in history."""
        try:
            with get_db_session() as session:
                query_hash = hashlib.sha256(sql.encode()).hexdigest()
                
                query = text("""
                    INSERT INTO query_history (
                        query_text, query_hash, dataset_ids, execution_time_ms,
                        result_count, status, created_by
                    ) VALUES (
                        :query_text, :query_hash, :dataset_ids, :execution_time_ms,
                        :result_count, :status, :created_by
                    )
                """)
                
                session.execute(query, {
                    'query_text': sql,
                    'query_hash': query_hash,
                    'dataset_ids': json.dumps(dataset_ids or []),
                    'execution_time_ms': int(result['metadata']['execution_time_seconds'] * 1000),
                    'result_count': result['metadata']['row_count'],
                    'status': 'completed' if result['success'] else 'failed',
                    'created_by': 'system'
                })
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to store query history: {e}")
    
    def _generate_create_table_sql(self, dataset_id: int, dataset_info: Dict[str, Any]) -> str:
        """Generate CREATE TABLE SQL for external table."""
        # This would generate appropriate CREATE TABLE statement for Trino/Presto
        # based on the dataset schema and partition strategy
        
        table_name = f"dataset_{dataset_id}"
        
        # Basic CREATE TABLE template
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            url VARCHAR,
            domain VARCHAR,
            network_type VARCHAR,
            title VARCHAR,
            content VARCHAR,
            crawled_at TIMESTAMP,
            status_code INTEGER
        )
        WITH (
            external_location = 's3a://noctipede-data/datasets/{dataset_id}/',
            format = 'PARQUET'
        )
        """
        
        return create_sql
    
    def _execute_trino_ddl(self, sql: str) -> bool:
        """Execute DDL statement in Trino."""
        try:
            cursor = self.trino_conn.cursor()
            cursor.execute(sql)
            return True
        except Exception as e:
            logger.error(f"Trino DDL execution failed: {e}")
            return False
    
    def _execute_presto_ddl(self, sql: str) -> bool:
        """Execute DDL statement in Presto."""
        try:
            cursor = self.presto_conn.cursor()
            cursor.execute(sql)
            return True
        except Exception as e:
            logger.error(f"Presto DDL execution failed: {e}")
            return False
