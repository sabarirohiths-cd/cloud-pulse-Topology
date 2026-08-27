import logging

logger = logging.getLogger(__name__)

class BaseTracer:
    """
    Base class for all modular tracers (Network, Traffic, Storage, etc.).
    Expects a parent fetcher instance (like EC2FlowFetcher or ECSFlowFetcher)
    that implements _add_node, _add_edge, and provides session/region clients.
    """
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.session = fetcher.session
        self.region = fetcher.region
        
        # Share AWS clients from the parent fetcher if they exist, else initialize
        self.ec2_client = getattr(fetcher, 'ec2_client', self.session.client('ec2', region_name=self.region))
        self.elbv2_client = getattr(fetcher, 'elbv2_client', self.session.client('elbv2', region_name=self.region))
        self.route53_client = getattr(fetcher, 'route53_client', self.session.client('route53', region_name=self.region))
        
    def add_node(self, node_id, node_type, label, status, metadata=None, health_state="HEALTHY", diagnostic=None):
        self.fetcher._add_node(node_id, node_type, label, status, metadata, health_state, diagnostic)
        
    def add_edge(self, source, target, relation, health_state="HEALTHY", diagnostic=None):
        self.fetcher._add_edge(source, target, relation, health_state, diagnostic)
