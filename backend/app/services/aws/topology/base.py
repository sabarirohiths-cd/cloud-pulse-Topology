import boto3
import json
import os
from concurrent.futures import ThreadPoolExecutor

class BaseTopologyBuilder:
    def __init__(self, session: boto3.Session, region: str = 'ap-south-1'):
        self.region = region
        self.session = session
        self.vpcs = {}
        
        print(f"Initializing AWS Clients for region {self.region} from session...")
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
        self.network_firewall = self.session.client('network-firewall', region_name=self.region)
        self.route53resolver = self.session.client('route53resolver', region_name=self.region)

    def _safe_get_tag(self, tags, key):
        if tags:
            for tag in tags:
                if tag.get('Key') == key:
                    return tag.get('Value')
        return None

    def _get_subnet_map(self):
        subnet_map = {}
        for vpc in self.vpcs.values():
            for sub in vpc.get('Subnets', []):
                subnet_map[sub['SubnetId']] = sub
        return subnet_map

    def get_topology(self):
        return list(self.vpcs.values())

    def save_output(self, output_dir='output', filename='final_complete_topology.json'):
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, filename)
        with open(path, 'w') as f:
            json.dump(list(self.vpcs.values()), f, indent=4)
        print(f"Topology JSON exported to {path}")
