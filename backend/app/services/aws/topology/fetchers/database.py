import logging
logger = logging.getLogger(__name__)

from ..core.base import BaseTopologyBuilder

class DatabaseMixin(BaseTopologyBuilder):
    def _fetch_rds(self):
        logger.debug("Fetching RDS...")
        try:
            rds_resp = self.rds.describe_db_instances()
            for db in rds_resp.get('DBInstances', []):
                sub_group = db.get('DBSubnetGroup', {})
                db_obj = db.copy()
                db_obj['VpcId'] = sub_group.get('VpcId')
                self.raw_data['RDSInstances'].append(db_obj)
                
            cluster_resp = self.rds.describe_db_clusters()
            for cluster in cluster_resp.get('DBClusters', []):
                sub_group = cluster.get('DBSubnetGroup', {})
                vpc_id = None
                if isinstance(sub_group, dict):
                    vpc_id = sub_group.get('VpcId')
                elif isinstance(sub_group, str):
                    try:
                        g_info = self.rds.describe_db_subnet_groups(DBSubnetGroupName=sub_group)
                        vpc_id = g_info.get('DBSubnetGroups', [{}])[0].get('VpcId')
                    except Exception as e:
                        logger.warning(f"Error during AWS discovery: {e}")
                
                # Some serverless clusters don't have VPC networking enabled directly
                # but users expect to see them. Let mapper handle it or fallback later.
                self.raw_data['RDSInstances'].append({
                    'VpcId': vpc_id or "FALLBACK_TO_FIRST_VPC",
                    'DBClusterIdentifier': cluster.get('DBClusterIdentifier'),
                    'Engine': cluster.get('Engine'),
                    'DBInstanceStatus': cluster.get('Status'),
                    'Endpoint': cluster.get('Endpoint')
                })
        except Exception as e:
            logger.debug(f"Error fetching RDS: {e}")

    def _fetch_elasticache(self):
        logger.debug("Fetching ElastiCache...")
        try:
            cache_clusters = self.elasticache.describe_cache_clusters().get('CacheClusters', [])
            for cluster in cache_clusters:
                subnet_group = cluster.get('CacheSubnetGroupName')
                if subnet_group:
                    try:
                        g_info = self.elasticache.describe_cache_subnet_groups(CacheSubnetGroupName=subnet_group)
                        subnets = g_info.get('CacheSubnetGroups', [{}])[0].get('Subnets', [])
                        for sn in subnets:
                            self.raw_data['ElastiCacheNodes'].append({
                                'SubnetId': sn.get('SubnetIdentifier'),
                                'CacheClusterId': cluster.get('CacheClusterId'),
                                'Engine': cluster.get('Engine'),
                                'CacheNodeType': cluster.get('CacheNodeType')
                            })
                    except Exception as e:
                        logger.warning(f"Error during AWS discovery: {e}")
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_documentdb(self):
        logger.debug("Fetching DocumentDB...")
        try:
            docdb_resp = self.docdb.describe_db_clusters()
            for cluster in docdb_resp.get('DBClusters', []):
                subnet_group = cluster.get('DBSubnetGroup')
                if subnet_group:
                    try:
                        g_info = self.docdb.describe_db_subnet_groups(DBSubnetGroupName=subnet_group)
                        subnets = g_info.get('DBSubnetGroups', [{}])[0].get('Subnets', [])
                        sids = [sn.get('SubnetIdentifier') for sn in subnets]
                        self.raw_data['DocumentDBClusters'].append({
                            'SubnetIds': sids,
                            'DBClusterIdentifier': cluster.get('DBClusterIdentifier'),
                            'Engine': cluster.get('Engine'),
                            'Status': cluster.get('Status')
                        })
                    except Exception as e:
                        logger.warning(f"Error during AWS discovery: {e}")
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_redshift(self):
        logger.debug("Fetching Redshift...")
        try:
            rs_resp = self.redshift.describe_clusters()
            for cluster in rs_resp.get('Clusters', []):
                subnet_group_name = cluster.get('ClusterSubnetGroupName')
                if subnet_group_name:
                    try:
                        g_info = self.redshift.describe_cluster_subnet_groups(ClusterSubnetGroupName=subnet_group_name)
                        subnets = g_info.get('ClusterSubnetGroups', [{}])[0].get('Subnets', [])
                        sids = [sn.get('SubnetIdentifier') for sn in subnets]
                        self.raw_data['RedshiftClusters'].append({
                            'SubnetIds': sids,
                            'ClusterIdentifier': cluster.get('ClusterIdentifier'),
                            'NodeType': cluster.get('NodeType'),
                            'ClusterStatus': cluster.get('ClusterStatus')
                        })
                    except Exception as e:
                        logger.warning(f"Error during AWS discovery: {e}")
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_neptune(self):
        logger.debug("Fetching Neptune...")
        try:
            nep_resp = self.neptune.describe_db_clusters()
            for cluster in nep_resp.get('DBClusters', []):
                subnet_group = cluster.get('DBSubnetGroup')
                if subnet_group:
                    try:
                        g_info = self.neptune.describe_db_subnet_groups(DBSubnetGroupName=subnet_group)
                        subnets = g_info.get('DBSubnetGroups', [{}])[0].get('Subnets', [])
                        sids = [sn.get('SubnetIdentifier') for sn in subnets]
                        self.raw_data['NeptuneClusters'].append({
                            'SubnetIds': sids,
                            'DBClusterIdentifier': cluster.get('DBClusterIdentifier'),
                            'Status': cluster.get('Status'),
                            'Endpoint': cluster.get('Endpoint'),
                            'ReaderEndpoint': cluster.get('ReaderEndpoint')
                        })
                    except Exception as e:
                        logger.warning(f"Error during AWS discovery: {e}")
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_memorydb(self):
        logger.debug("Fetching MemoryDB...")
        try:
            mem_resp = self.memorydb.describe_clusters()
            for cluster in mem_resp.get('Clusters', []):
                subnet_group_name = cluster.get('SubnetGroupName')
                if subnet_group_name:
                    try:
                        g_info = self.memorydb.describe_subnet_groups(SubnetGroupName=subnet_group_name)
                        subnets = g_info.get('SubnetGroups', [{}])[0].get('Subnets', [])
                        sids = [sn.get('Identifier') for sn in subnets]
                        self.raw_data['MemoryDBClusters'].append({
                            'SubnetIds': sids,
                            'Name': cluster.get('Name'),
                            'Status': cluster.get('Status'),
                            'NodeType': cluster.get('NodeType'),
                            'EngineVersion': cluster.get('EngineVersion')
                        })
                    except Exception as e:
                        logger.warning(f"Error during AWS discovery: {e}")
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")
