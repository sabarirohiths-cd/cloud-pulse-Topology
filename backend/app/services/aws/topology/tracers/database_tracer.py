from .base_tracer import BaseTracer
import logging

logger = logging.getLogger(__name__)

class DatabaseTracer(BaseTracer):
    def trace(self, vpc_id, sg_ids, root_id, root_tags=None, root_name=None):
        """
        Traces downstream databases (RDS, ElastiCache) connected via Security Groups or Tags.
        """
        if not vpc_id or not sg_ids:
            return

        root_tags = root_tags or {}
        root_name = root_name or root_id

        # 1. Check RDS Databases
        try:
            rds_client = getattr(self.fetcher, 'rds_client', self.session.client('rds', region_name=self.region))
            rds_instances = rds_client.describe_db_instances()
            
            for rds in rds_instances.get('DBInstances', []):
                rds_id = rds.get('DBInstanceIdentifier')
                rds_sgs = [sg.get('VpcSecurityGroupId') for sg in rds.get('VpcSecurityGroups', []) if sg.get('Status') == 'active']
                
                if rds.get('DBSubnetGroup', {}).get('VpcId') == vpc_id:
                    db_status = rds.get('DBInstanceStatus', 'available')
                    rds_health = "CRITICAL" if db_status != 'available' else "HEALTHY"
                    rds_diag = f"Database is {db_status}" if rds_health == "CRITICAL" else None
                    
                    try:
                        if not rds_sgs: continue
                        sg_response = self.ec2_client.describe_security_groups(GroupIds=rds_sgs)
                        linked = False
                        for sg in sg_response.get('SecurityGroups', []):
                            for rule in sg.get('IpPermissions', []):
                                for pair in rule.get('UserIdGroupPairs', []):
                                    if pair.get('GroupId') in sg_ids:
                                        linked = True
                                        break
                                if linked: break
                            if linked: break
                            
                        # Tag check for intent
                        rds_tags = {t['Key']: t['Value'] for t in rds.get('TagList', [])}
                        shared_tag = False
                        for key in ['Project', 'Environment', 'App', 'Application']:
                            if key in root_tags and key in rds_tags and root_tags[key] == rds_tags[key]:
                                shared_tag = True
                                break
                        if not shared_tag:
                            if root_name and (root_name.lower() in rds_id.lower() or rds_id.lower() in root_name.lower()):
                                shared_tag = True
                                
                        if linked:
                            self.add_node(rds_id, 'RDS', rds_id, db_status, {
                                "Engine": rds.get('Engine'),
                                "AllocatedStorage": rds.get('AllocatedStorage'),
                                "InstanceClass": rds.get('DBInstanceClass'),
                                "MultiAZ": rds.get('MultiAZ'),
                                "PubliclyAccessible": rds.get('PubliclyAccessible'),
                                "DBClusterIdentifier": rds.get('DBClusterIdentifier') # For Aurora
                            }, health_state=rds_health, diagnostic=rds_diag)
                            self.add_edge(root_id, rds_id, 'QUERIES')
                            
                            # Add the RDS Security Groups to the graph
                            for sg_id in rds_sgs:
                                self.add_node(sg_id, 'SECURITY_GROUP', sg_id, 'available', {
                                    "Type": "Security Group",
                                    "GroupId": sg_id
                                })
                                self.add_edge(sg_id, rds_id, 'PROTECTS')
                        elif shared_tag:
                            self.add_node(rds_id, 'RDS', rds_id, db_status, {
                                "Engine": rds.get('Engine'),
                                "AllocatedStorage": rds.get('AllocatedStorage'),
                                "InstanceClass": rds.get('DBInstanceClass'),
                                "MultiAZ": rds.get('MultiAZ'),
                                "PubliclyAccessible": rds.get('PubliclyAccessible'),
                                "DBClusterIdentifier": rds.get('DBClusterIdentifier')
                            }, health_state=rds_health, diagnostic=rds_diag)
                            self.add_edge(root_id, rds_id, 'QUERIES', health_state="BLOCKED", diagnostic="Missing SG Ingress Rule on Port 3306")
                            
                            for sg_id in rds_sgs:
                                self.add_node(sg_id, 'SECURITY_GROUP', sg_id, 'available', {
                                    "Type": "Security Group",
                                    "GroupId": sg_id
                                })
                                self.add_edge(sg_id, rds_id, 'PROTECTS')
                    except Exception as e:
                        logger.warning(f"Failed to trace RDS SG {rds_sgs}: {e}")
        except Exception as e:
            logger.warning(f"Failed to trace RDS for {root_id}: {e}")

        # 2. Check ElastiCache
        try:
            elasticache = getattr(self.fetcher, 'elasticache_client', self.session.client('elasticache', region_name=self.region))
            clusters_resp = elasticache.describe_cache_clusters()
            for cluster in clusters_resp.get('CacheClusters', []):
                cluster_sgs = [sg.get('SecurityGroupId') for sg in cluster.get('SecurityGroups', [])]
                if cluster_sgs and sg_ids:
                    try:
                        sg_response = self.ec2_client.describe_security_groups(GroupIds=cluster_sgs)
                        linked = False
                        for sg_obj in sg_response.get('SecurityGroups', []):
                            for rule in sg_obj.get('IpPermissions', []):
                                for pair in rule.get('UserIdGroupPairs', []):
                                    if pair.get('GroupId') in sg_ids:
                                        linked = True
                                        break
                                if linked: break
                            if linked: break
                        
                        if linked:
                            cluster_id = cluster.get('CacheClusterId')
                            self.add_node(cluster_id, 'ELASTICACHE', cluster_id, cluster.get('CacheClusterStatus'), {
                                "Engine": cluster.get('Engine'),
                                "CacheNodeType": cluster.get('CacheNodeType'),
                                "NumCacheNodes": cluster.get('NumCacheNodes'),
                                "EngineVersion": cluster.get('EngineVersion')
                            })
                            self.add_edge(root_id, cluster_id, 'QUERIES')
                    except Exception as e:
                        logger.warning(f"Failed to trace ElastiCache SG: {e}")
        except Exception as e:
            logger.warning(f"Failed to trace ElastiCache for {root_id}: {e}")
