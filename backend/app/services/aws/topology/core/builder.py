import logging
logger = logging.getLogger(__name__)

from concurrent.futures import ThreadPoolExecutor

from .base import BaseTopologyBuilder
from ..fetchers.networking import NetworkingMixin
from ..fetchers.compute import ComputeMixin
from ..fetchers.database import DatabaseMixin
from ..fetchers.storage import StorageMixin
from ..fetchers.messaging import MessagingMixin
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
        logger.info("Starting Modular AWSTopologyBuilder Process...")
        
        # 1. Fetch synchronous skeleton (VPCs/Subnets)
        self._fetch_vpcs_and_subnets()
        
        if not self.raw_data['Vpcs']:
            logger.info("No VPCs found. Exiting.")
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
        
        logger.info(f"Spawning {len(worker_methods)} worker threads for concurrent fetching...")
        with ThreadPoolExecutor(max_workers=len(worker_methods)) as executor:
            for method in worker_methods:
                executor.submit(method)

        logger.info("Data fetching complete. Mapping topology...")
        mapper = TopologyMapper(self.raw_data)
        self.vpcs = mapper.map()
        logger.info("Topology fully assembled!")

    def print_summary(self):
        logger.info("\n=== AWS Topology Summary ===")
        total_vpcs = len(self.vpcs)
        total_subnets = sum(len(vpc.get('Subnets', [])) for vpc in self.vpcs.values())
        logger.info(f"VPCs Found: {total_vpcs}")
        logger.info(f"Subnets Found: {total_subnets}")
        logger.info(f"Security Groups Found: {len(self.raw_data.get('SecurityGroups', []))}")
        logger.info(f"Network ACLs Found: {len(self.raw_data.get('NetworkAcls', []))}")
        logger.info(f"Elastic IPs Found: {len(self.raw_data.get('ElasticIps', []))}")
        logger.info(f"Neptune Clusters Found: {len(self.raw_data.get('NeptuneClusters', []))}")
        logger.info(f"Directory Services Found: {len(self.raw_data.get('DirectoryServices', []))}")
        logger.info(f"App Runner Connectors Found: {len(self.raw_data.get('AppRunnerVpcConnectors', []))}")
        logger.info(f"EMR Clusters Found: {len(self.raw_data.get('EMRClusters', []))}")
        logger.info(f"Glue Connections Found: {len(self.raw_data.get('GlueConnections', []))}")
        logger.info(f"Gateway Load Balancers Found: {len(self.raw_data.get('GatewayLoadBalancers', []))}")
        logger.info(f"TGW Route Tables Found: {len(self.raw_data.get('TransitGatewayRouteTables', []))}")
        logger.info(f"MemoryDB Clusters Found: {len(self.raw_data.get('MemoryDBClusters', []))}")
        logger.info(f"Batch Environments Found: {len(self.raw_data.get('BatchComputeEnvironments', []))}")
        logger.info(f"Flow Logs Found: {len(self.raw_data.get('FlowLogs', []))}")
        logger.info(f"Hybrid Connections Found: {len(self.raw_data.get('HybridConnectivity', []))}")
        logger.info(f"Security Compliance Added: {'Yes' if self.raw_data.get('SecurityAndCompliance') else 'No'}")
        logger.info(f"Resources Mapped: {sum([len(x) for x in self.raw_data.values()])}")
        logger.info("============================\n")

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
        logger.info(f"Starting Regional Workers for regions: {self.regions}")
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
                    logger.info(f"Region {region} generated an exception: {exc}")

        global_res = {
            'Route53HostedZones': self.global_data.get('Route53HostedZones', []),
            'CloudFrontDistributions': self.global_data.get('CloudFrontDistributions', []),
            'S3Buckets': self.global_data.get('S3Buckets', []),
            'IAMRoles': self.global_data.get('IAMRoles', [])
        }
        
        # Cross-region connection stitching
        stitcher = GraphStitcher(self.regional_data, global_res)
        self.regional_data, self.edges = stitcher.stitch()

        return {
            'Regions': self.regional_data,
            'GlobalResources': global_res,
            'Edges': self.edges
        }

    def _run_regional_worker(self, region):
        logger.info(f"--- Worker for {region} starting ---")
        builder = ModularTopologyBuilder(self.session, region=region)
        builder.build()
        return list(builder.vpcs.values())

    def get_topology(self):
        return {
            "Regions": self.regional_data,
            "GlobalResources": self.global_data,
            "Edges": getattr(self, 'edges', [])
        }
        
    def save_output(self, output_dir='output', filename='final_complete_topology.json'):
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, filename)
        with open(path, 'w') as f:
            json.dump(self.get_topology(), f, indent=4)
        logger.info(f"Multi-Region Topology JSON exported to {path}")

