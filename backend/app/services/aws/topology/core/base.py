import logging
logger = logging.getLogger(__name__)

import boto3
import json
import os
from concurrent.futures import ThreadPoolExecutor

class BaseTopologyBuilder:
    def __init__(self, session: boto3.Session, region: str = 'ap-south-1'):
        self.region = region
        self.session = session
        self.vpcs = {}
        
        self.raw_data = {
            'Vpcs': [], 'Subnets': [], 'InternetGateways': [], 'RouteTables': [], 'NatGateways': [],
            'VpcEndpoints': [], 'PeeringConnections': [], 'NetworkAcls': [], 'TransitGatewayAttachments': [],
            'VpnGateways': [], 'VpnConnections': [], 'UnclassifiedENIs': [], 'NetworkFirewalls': [],
            'NetworkFirewallEndpoints': [], 'Route53ResolverEndpoints': [], 'LoadBalancers': [],
            'SecurityGroups': [], 'Instances': [], 'AutoScalingGroups': [], 'ElasticIps': [],
            'EbsVolumes': [], 'EKSClusters': [], 'ECSClusters': [], 'LambdaFunctions': [],
            'SageMakerNotebooks': [], 'WorkSpaces': [], 'RDSInstances': [], 'ElastiCacheNodes': [],
            'DocumentDBClusters': [], 'RedshiftClusters': [], 'EFSMountTargets': [], 'FSxFileSystems': [],
            'RegionalQueues': [], 'AmazonMQBrokers': [], 'MSKClusters': [], 'OpenSearchDomains': [],
            'NeptuneClusters': [], 'DirectoryServices': [], 'AppRunnerVpcConnectors': [], 'EMRClusters': [],
            'GlueConnections': [], 'GatewayLoadBalancers': [], 'GWLBEndpoints': [],
            'TransitGatewayRouteTables': [], 'MemoryDBClusters': [],
            'EgressOnlyInternetGateways': [], 'CarrierGateways': [], 'DhcpOptions': [],
            'FlowLogs': [], 'BatchComputeEnvironments': [], 'SecurityAndCompliance': [],
            'HybridConnectivity': [], 'ElasticBeanstalkEnvironments': []
        }
        
        logger.info(f"Initializing AWS Clients for region {self.region} from session...")
        self.ec2 = self.session.client('ec2', region_name=self.region)
        self.elbv2 = self.session.client('elbv2', region_name=self.region)
        self.rds = self.session.client('rds', region_name=self.region)
        self.eks = self.session.client('eks', region_name=self.region)
        self.ecs = self.session.client('ecs', region_name=self.region)
        self.lmbda = self.session.client('lambda', region_name=self.region)
        self.elasticache = self.session.client('elasticache', region_name=self.region)
        self.efs = self.session.client('efs', region_name=self.region)
        self.asg = self.session.client('autoscaling', region_name=self.region)
        self.mq = self.session.client('mq', region_name=self.region)
        self.kafka = self.session.client('kafka', region_name=self.region)
        self.sqs = self.session.client('sqs', region_name=self.region)
        
        # New Clients
        self.docdb = self.session.client('docdb', region_name=self.region)
        self.redshift = self.session.client('redshift', region_name=self.region)
        self.sagemaker = self.session.client('sagemaker', region_name=self.region)
        self.workspaces = self.session.client('workspaces', region_name=self.region)
        self.fsx = self.session.client('fsx', region_name=self.region)
        self.opensearch = self.session.client('opensearch', region_name=self.region)
        self.neptune = self.session.client('neptune', region_name=self.region)
        self.eb = self.session.client('elasticbeanstalk', region_name=self.region)
        self.route53resolver = self.session.client('route53resolver', region_name=self.region)
        self.neptune = self.session.client('neptune', region_name=self.region)
        self.ds = self.session.client('ds', region_name=self.region)
        self.apprunner = self.session.client('apprunner', region_name=self.region)
        self.emr = self.session.client('emr', region_name=self.region)
        self.glue = self.session.client('glue', region_name=self.region)
        self.memorydb = self.session.client('memorydb', region_name=self.region)
        self.batch = self.session.client('batch', region_name=self.region)
        self.guardduty = self.session.client('guardduty', region_name=self.region)
        self.config = self.session.client('config', region_name=self.region)
        self.directconnect = self.session.client('directconnect', region_name=self.region)
        self.networkmanager = self.session.client('networkmanager', region_name=self.region)
        self.network_firewall = self.session.client('network-firewall', region_name=self.region)

    def _safe_get_tag(self, tags, key):
        if tags:
            for tag in tags:
                if tag.get('Key') == key:
                    return tag.get('Value')
        return None

    def get_topology(self):
        return list(self.vpcs.values())

    def save_output(self, output_dir='output', filename='final_complete_topology.json'):
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, filename)
        with open(path, 'w') as f:
            json.dump(list(self.vpcs.values()), f, indent=4)
        logger.info(f"Topology JSON exported to {path}")
