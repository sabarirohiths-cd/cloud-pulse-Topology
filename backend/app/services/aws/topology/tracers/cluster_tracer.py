import logging
from app.services.aws.topology.tracers.base_tracer import BaseTracer

logger = logging.getLogger(__name__)

class ClusterTracer(BaseTracer):
    def __init__(self, fetcher):
        super().__init__(fetcher)
        self.ecs_client = self.session.client('ecs', region_name=self.region)

    def trace(self, ec2_tags: dict, instance_id: str):
        """
        Traces cluster orchestrator relationships (EKS, ECS).
        ASG logic is mostly handled natively in ec2_flow, but we map cluster nodes here.
        """
        logger.info(f"Tracing Cluster Orchestrators for {instance_id}...")
        
        # 1. EKS Tracing
        # EKS uses tags: `eks:cluster-name` and `eks:nodegroup-name`
        eks_cluster = ec2_tags.get('eks:cluster-name')
        eks_nodegroup = ec2_tags.get('eks:nodegroup-name')
        
        # Sometimes kubernetes.io/cluster/<cluster-name> is used
        if not eks_cluster:
            for k, v in ec2_tags.items():
                if k.startswith('kubernetes.io/cluster/'):
                    eks_cluster = k.split('/')[-1]
                    break
                    
        if eks_cluster:
            cluster_node_id = f"eks-cluster-{eks_cluster}"
            
            self.add_node(cluster_node_id, 'EKS_CLUSTER', eks_cluster, 'active', {
                "Type": "EKS Cluster",
                "ClusterName": eks_cluster
            })
            
            if eks_nodegroup:
                nodegroup_id = f"eks-nodegroup-{eks_nodegroup}"
                self.add_node(nodegroup_id, 'EKS_NODEGROUP', eks_nodegroup, 'active', {
                    "Type": "EKS NodeGroup",
                    "NodeGroupName": eks_nodegroup,
                    "ClusterName": eks_cluster
                })
                # Link Cluster -> NodeGroup
                self.add_edge(cluster_node_id, nodegroup_id, 'CONTAINS')
                # Link NodeGroup -> EC2
                self.add_edge(nodegroup_id, instance_id, 'MANAGES')
            else:
                # Link Cluster -> EC2 directly if no nodegroup tag
                self.add_edge(cluster_node_id, instance_id, 'MANAGES')
                
        # 2. ECS Tracing
        # Look for AmazonECSManaged or ECS cluster tags first
        ecs_cluster = ec2_tags.get('aws:ecs:clusterName')
        
        # If no tag is found, query ECS APIs to see if this EC2 instance is an ECS container instance
        if not ecs_cluster:
            try:
                # This scans ALL ECS clusters in the region to see if the instance is registered.
                # It's an API hit, but usually regions don't have thousands of clusters.
                cluster_paginator = self.ecs_client.get_paginator('list_clusters')
                for c_page in cluster_paginator.paginate():
                    for cluster_arn in c_page.get('clusterArns', []):
                        if ecs_cluster: break
                        try:
                            # We can list container instances and filter by ec2InstanceId
                            ci_paginator = self.ecs_client.get_paginator('list_container_instances')
                            for ci_page in ci_paginator.paginate(cluster=cluster_arn, filter=f"ec2InstanceId=={instance_id}"):
                                if ci_page.get('containerInstanceArns'):
                                    ecs_cluster = cluster_arn.split('/')[-1]
                                    break
                        except Exception as e:
                            logger.warning(f"Failed to list ECS container instances for {cluster_arn}: {e}")
            except Exception as e:
                logger.warning(f"Failed to list ECS clusters: {e}")
                
        if ecs_cluster:
            cluster_node_id = f"ecs-cluster-{ecs_cluster}"
            self.add_node(cluster_node_id, 'ECS_CLUSTER', ecs_cluster, 'active', {
                "Type": "ECS Cluster",
                "ClusterName": ecs_cluster
            })
            # Link ECS Cluster -> EC2
            self.add_edge(cluster_node_id, instance_id, 'MANAGES')
