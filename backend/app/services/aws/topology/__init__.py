from concurrent.futures import ThreadPoolExecutor

from .base import BaseTopologyBuilder
from .networking import NetworkingMixin
from .compute import ComputeMixin
from .database import DatabaseMixin
from .storage import StorageMixin
from .messaging import MessagingMixin
from .topology_mapper import TopologyMapper

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
        
        # 1. Fetch synchronous skeleton (VPCs/Subnets)
        self._fetch_vpcs_and_subnets()
        
        if not self.raw_data['Vpcs']:
            print("No VPCs found. Exiting.")
            return

        # 2. Run workers in parallel
        worker_methods = [
            self._fetch_ec2,
            self._fetch_routes_nat,
            self._fetch_elb,
            self._fetch_rds,
            self._fetch_eks_ecs,
            self._fetch_lambda,
            self._fetch_endpoints_peering,
            self._fetch_tgw,
            self._fetch_elasticache,
            self._fetch_efs,
            self._fetch_asg_ebs,
            self._fetch_vgw_vpn_eni,
            self._fetch_messaging_queues,
            self._fetch_documentdb,
            self._fetch_redshift,
            self._fetch_sagemaker,
            self._fetch_workspaces,
            self._fetch_fsx,
            self._fetch_opensearch,
            self._fetch_network_firewall,
            self._fetch_route53_resolvers,
            self._fetch_neptune,
            self._fetch_directory_service,
            self._fetch_app_runner_vpc_connectors,
            self._fetch_emr,
            self._fetch_glue_connections,
            self._fetch_gateway_load_balancers,
            self._fetch_tgw_route_tables,
            self._fetch_memorydb,
            self._fetch_advanced_gateways_and_dhcp,
            self._fetch_flow_logs,
            self._fetch_hybrid_connectivity,
            self._fetch_security_compliance,
            self._fetch_batch,
            self._fetch_security_groups,
            self._fetch_network_acls,
            self._fetch_elastic_ips
        ]
        
        print(f"Spawning {len(worker_methods)} worker threads for concurrent fetching...")
        with ThreadPoolExecutor(max_workers=len(worker_methods)) as executor:
            for method in worker_methods:
                executor.submit(method)

        print("Data fetching complete. Mapping topology...")
        mapper = TopologyMapper(self.raw_data)
        self.vpcs = mapper.map()
        print("Topology fully assembled!")

    def print_summary(self):
        print("\n=== AWS Topology Summary ===")
        total_vpcs = len(self.vpcs)
        total_subnets = sum(len(vpc.get('Subnets', [])) for vpc in self.vpcs.values())
        print(f"VPCs Found: {total_vpcs}")
        print(f"Subnets Found: {total_subnets}")
        print(f"Security Groups Found: {len(self.raw_data.get('SecurityGroups', []))}")
        print(f"Network ACLs Found: {len(self.raw_data.get('NetworkAcls', []))}")
        print(f"Elastic IPs Found: {len(self.raw_data.get('ElasticIps', []))}")
        print(f"Neptune Clusters Found: {len(self.raw_data.get('NeptuneClusters', []))}")
        print(f"Directory Services Found: {len(self.raw_data.get('DirectoryServices', []))}")
        print(f"App Runner Connectors Found: {len(self.raw_data.get('AppRunnerVpcConnectors', []))}")
        print(f"EMR Clusters Found: {len(self.raw_data.get('EMRClusters', []))}")
        print(f"Glue Connections Found: {len(self.raw_data.get('GlueConnections', []))}")
        print(f"Gateway Load Balancers Found: {len(self.raw_data.get('GatewayLoadBalancers', []))}")
        print(f"TGW Route Tables Found: {len(self.raw_data.get('TransitGatewayRouteTables', []))}")
        print(f"MemoryDB Clusters Found: {len(self.raw_data.get('MemoryDBClusters', []))}")
        print(f"Batch Environments Found: {len(self.raw_data.get('BatchComputeEnvironments', []))}")
        print(f"Flow Logs Found: {len(self.raw_data.get('FlowLogs', []))}")
        print(f"Hybrid Connections Found: {len(self.raw_data.get('HybridConnectivity', []))}")
        print(f"Security Compliance Added: {'Yes' if self.raw_data.get('SecurityAndCompliance') else 'No'}")
        print(f"Resources Mapped: {sum([len(x) for x in self.raw_data.values()])}")
        print("============================\n")

from .global_discovery import GlobalDiscoveryEngine
from .graph_stitcher import GraphStitcher
import concurrent.futures
import os
import json

class MultiRegionTopologyBuilder:
    def __init__(self, session, regions):
        self.session = session
        self.regions = regions
        self.global_data = {}
        self.regional_data = {}

    def build(self):
        # 1. Global Discovery
        global_engine = GlobalDiscoveryEngine(self.session)
        self.global_data = global_engine.run()

        # 2. Regional Workers
        print(f"Starting Regional Workers for regions: {self.regions}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(self.regions))) as executor:
            future_to_region = {
                executor.submit(self._run_regional_worker, region): region 
                for region in self.regions
            }
            for future in concurrent.futures.as_completed(future_to_region):
                region = future_to_region[future]
                try:
                    self.regional_data[region] = future.result()
                except Exception as exc:
                    print(f"Region {region} generated an exception: {exc}")

        # 3. Stitch Graph
        stitcher = GraphStitcher(self.regional_data)
        self.regional_data = stitcher.stitch()

    def _run_regional_worker(self, region):
        print(f"--- Worker for {region} starting ---")
        builder = ModularTopologyBuilder(self.session, region=region)
        builder.build()
        return list(builder.vpcs.values())

    def get_topology(self):
        return {
            "Regions": self.regional_data,
            "GlobalResources": self.global_data
        }
        
    def save_output(self, output_dir='output', filename='final_complete_topology.json'):
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, filename)
        with open(path, 'w') as f:
            json.dump(self.get_topology(), f, indent=4)
        print(f"Multi-Region Topology JSON exported to {path}")

