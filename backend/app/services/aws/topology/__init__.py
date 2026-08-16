from concurrent.futures import ThreadPoolExecutor

from .base import BaseTopologyBuilder
from .networking import NetworkingMixin
from .compute import ComputeMixin
from .database import DatabaseMixin
from .storage import StorageMixin
from .messaging import MessagingMixin

class ModularTopologyBuilder(
    NetworkingMixin, 
    ComputeMixin, 
    DatabaseMixin, 
    StorageMixin, 
    MessagingMixin, 
    BaseTopologyBuilder
):
    def build(self):
        print("Starting Modular AWSTopologyBuilder Process...")
        
        # 1. Fetch synchronous skeleton
        self._fetch_vpcs_and_subnets()
        
        if not self.vpcs:
            print("No VPCs found. Exiting.")
            return

        # 2. Run workers in parallel
        worker_methods = [
            self._fetch_ec2_and_sg,
            self._fetch_routes_nat,
            self._fetch_elb,
            self._fetch_rds,
            self._fetch_eks_ecs,
            self._fetch_lambda,
            self._fetch_endpoints_peering,
            self._fetch_tgw_nacl,
            self._fetch_elasticache,
            self._fetch_efs,
            self._fetch_asg_eip_ebs,
            self._fetch_vgw_vpn_eni,
            self._fetch_messaging_queues,
            self._fetch_documentdb,
            self._fetch_redshift,
            self._fetch_sagemaker,
            self._fetch_workspaces,
            self._fetch_fsx,
            self._fetch_opensearch,
            self._fetch_network_firewall,
            self._fetch_route53_resolvers
        ]
        
        print(f"Spawning {len(worker_methods)} worker threads for concurrent fetching...")
        with ThreadPoolExecutor(max_workers=len(worker_methods)) as executor:
            for method in worker_methods:
                executor.submit(method)

        print("Topology fully assembled!")

    def print_summary(self):
        print("\n=== AWS Topology Summary ===")
        total_vpcs = len(self.vpcs)
        total_subnets = 0
        total_ec2 = 0
        total_rds = 0
        total_lambdas = 0
        total_docdb = 0
        total_redshift = 0
        total_sagemaker = 0
        total_workspaces = 0
        total_fsx = 0
        total_opensearch = 0
        total_network_firewalls = 0
        total_route53_resolvers = 0
        
        for vpc in self.vpcs.values():
            total_subnets += len(vpc.get('Subnets', []))
            total_rds += len(vpc.get('RDSInstances', []))
            total_network_firewalls += len(vpc.get('NetworkFirewalls', []))
            
            for sub in vpc.get('Subnets', []):
                total_ec2 += len(sub.get('Instances', []))
                total_lambdas += len(sub.get('LambdaFunctions', []))
                total_docdb += len(sub.get('DocumentDBClusters', []))
                total_redshift += len(sub.get('RedshiftClusters', []))
                total_sagemaker += len(sub.get('SageMakerNotebooks', []))
                total_workspaces += len(sub.get('WorkSpaces', []))
                total_fsx += len(sub.get('FSxFileSystems', []))
                total_opensearch += len(sub.get('OpenSearchDomains', []))
                total_route53_resolvers += len(sub.get('Route53ResolverEndpoints', []))
                
        print(f"VPCs Found: {total_vpcs}")
        print(f"Subnets Found: {total_subnets}")
        print(f"EC2 Instances Found: {total_ec2}")
        print(f"RDS Instances Found: {total_rds}")
        print(f"Lambda Functions Found: {total_lambdas}")
        print(f"DocumentDB Clusters Found: {total_docdb}")
        print(f"Redshift Clusters Found: {total_redshift}")
        print(f"SageMaker Notebooks Found: {total_sagemaker}")
        print(f"WorkSpaces Found: {total_workspaces}")
        print(f"FSx File Systems Found: {total_fsx}")
        print(f"OpenSearch Domains Found: {total_opensearch}")
        print(f"Network Firewalls Found: {total_network_firewalls}")
        print(f"Route53 Resolver Endpoints Found: {total_route53_resolvers}")
        print("============================\n")
