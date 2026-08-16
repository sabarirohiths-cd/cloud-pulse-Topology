from .base import BaseTopologyBuilder

class DatabaseMixin(BaseTopologyBuilder):
    def _fetch_rds(self):
        print("Fetching RDS...")
        try:
            rds_resp = self.rds.describe_db_instances()
            for db in rds_resp.get('DBInstances', []):
                sub_group = db.get('DBSubnetGroup', {})
                vpc_id = sub_group.get('VpcId')
                if vpc_id in self.vpcs:
                    self.vpcs[vpc_id]['RDSInstances'].append({
                        'DBInstanceIdentifier': db.get('DBInstanceIdentifier'),
                        'Engine': db.get('Engine'),
                        'DBInstanceStatus': db.get('DBInstanceStatus'),
                        'Endpoint': db.get('Endpoint', {}).get('Address')
                    })
        except Exception:
            pass

    def _fetch_elasticache(self):
        print("Fetching ElastiCache...")
        subnet_map = self._get_subnet_map()
        try:
            cache_clusters = self.elasticache.describe_cache_clusters().get('CacheClusters', [])
            for cluster in cache_clusters:
                subnet_group = cluster.get('CacheSubnetGroupName')
                if subnet_group:
                    try:
                        g_info = self.elasticache.describe_cache_subnet_groups(CacheSubnetGroupName=subnet_group)
                        subnets = g_info.get('CacheSubnetGroups', [{}])[0].get('Subnets', [])
                        c_info = {
                            'CacheClusterId': cluster.get('CacheClusterId'),
                            'Engine': cluster.get('Engine'),
                            'CacheNodeType': cluster.get('CacheNodeType')
                        }
                        for sn in subnets:
                            sid = sn.get('SubnetIdentifier')
                            if sid in subnet_map:
                                subnet_map[sid]['ElastiCacheNodes'].append(c_info)
                    except Exception:
                        pass
        except Exception:
            pass

    def _fetch_documentdb(self):
        print("Fetching DocumentDB...")
        subnet_map = self._get_subnet_map()
        try:
            docdb_resp = self.docdb.describe_db_clusters()
            for cluster in docdb_resp.get('DBClusters', []):
                subnet_group = cluster.get('DBSubnetGroup')
                info = {
                    'DBClusterIdentifier': cluster.get('DBClusterIdentifier'),
                    'Engine': cluster.get('Engine'),
                    'Status': cluster.get('Status')
                }
                if subnet_group:
                    try:
                        g_info = self.docdb.describe_db_subnet_groups(DBSubnetGroupName=subnet_group)
                        subnets = g_info.get('DBSubnetGroups', [{}])[0].get('Subnets', [])
                        for sn in subnets:
                            sid = sn.get('SubnetIdentifier')
                            if sid in subnet_map:
                                subnet_map[sid]['DocumentDBClusters'].append(info)
                    except Exception:
                        pass
        except Exception:
            pass

    def _fetch_redshift(self):
        print("Fetching Redshift...")
        subnet_map = self._get_subnet_map()
        try:
            rs_resp = self.redshift.describe_clusters()
            for cluster in rs_resp.get('Clusters', []):
                subnet_group_name = cluster.get('ClusterSubnetGroupName')
                info = {
                    'ClusterIdentifier': cluster.get('ClusterIdentifier'),
                    'NodeType': cluster.get('NodeType'),
                    'ClusterStatus': cluster.get('ClusterStatus')
                }
                if subnet_group_name:
                    try:
                        g_info = self.redshift.describe_cluster_subnet_groups(ClusterSubnetGroupName=subnet_group_name)
                        subnets = g_info.get('ClusterSubnetGroups', [{}])[0].get('Subnets', [])
                        for sn in subnets:
                            sid = sn.get('SubnetIdentifier')
                            if sid in subnet_map:
                                subnet_map[sid]['RedshiftClusters'].append(info)
                    except Exception:
                        pass
        except Exception:
            pass
