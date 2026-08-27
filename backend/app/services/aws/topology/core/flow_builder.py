import logging
import importlib
import boto3

logger = logging.getLogger(__name__)

class ComputeFlowBuilder:
    def __init__(self, session: boto3.Session, region: str, compute_type: str, resource_id: str, observability_options: list[str] = None, lookback_minutes: int = 15):
        self.session = session
        self.region = region
        self.compute_type = compute_type.upper()
        self.resource_id = resource_id
        self.observability_options = observability_options or []
        self.lookback_minutes = lookback_minutes
        
        self.nodes = []
        self.edges = []
        
    def build(self):
        logger.info(f"Dynamically loading fetcher for {self.compute_type}...")
        
        try:
            # Map EC2 to ec2_flow
            fetcher_module_name = f"app.services.aws.topology.fetchers.{self.compute_type.lower()}_flow"
            fetcher_module = importlib.import_module(fetcher_module_name)
            
            # Expect class like EC2FlowFetcher
            fetcher_class_name = f"{self.compute_type.upper()}FlowFetcher"
            fetcher_class = getattr(fetcher_module, fetcher_class_name)
            
            fetcher_instance = fetcher_class(self.session, self.region, self.resource_id, self.observability_options, self.lookback_minutes)
            nodes, edges = fetcher_instance.fetch()
            
            self.nodes.extend(nodes)
            self.edges.extend(edges)
            
        except ImportError:
            raise NotImplementedError(f"Flow tracing fetcher for {self.compute_type} is not yet implemented.")
        except AttributeError:
            raise NotImplementedError(f"Fetcher class for {self.compute_type} is not properly defined.")
            
        return {
            "compute_id": self.resource_id,
            "nodes": self.nodes,
            "edges": self.edges
        }
