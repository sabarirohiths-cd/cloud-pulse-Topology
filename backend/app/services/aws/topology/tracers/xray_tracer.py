import logging
from datetime import datetime, timedelta
from .base_tracer import BaseTracer

logger = logging.getLogger(__name__)

class XRayTracer(BaseTracer):
    def __init__(self, fetcher):
        super().__init__(fetcher)
        self.xray_client = getattr(fetcher, 'xray_client', self.session.client('xray', region_name=self.region))

    def trace(self, lookback_minutes: int):
        logger.info("Tracing dynamic service dependencies via X-Ray")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)
        
        try:
            resp = self.xray_client.get_service_graph(
                StartTime=start_time,
                EndTime=end_time
            )
            
            all_services = resp.get('Services', [])
            
            # Find all relevant services by traversing from known nodes
            known_ids = {n['id'] for n in self.fetcher.nodes}
            known_ids.add(self.fetcher.resource_id)
            
            # Since XRay node names might not exactly match our IDs (e.g. they might just be "my-service-name"),
            # we also do partial/substring matching against known resource names/labels.
            known_names = {n['label'].lower() for n in self.fetcher.nodes if 'label' in n}
            
            relevant_service_refs = set()
            
            # Initial pass: find services that directly match known EC2/resources
            for svc in all_services:
                svc_name = svc.get('Name', '').lower()
                # Match by ARN, Instance ID, or Label
                if svc_name in known_ids or any(svc_name in kn or kn in svc_name for kn in known_names if kn):
                    relevant_service_refs.add(svc.get('ReferenceId'))
                    
            # Second pass: iteratively add services that are connected to our relevant services
            # This builds the exact sub-graph connected to our EC2 trace.
            added_new = True
            while added_new:
                added_new = False
                for svc in all_services:
                    ref_id = svc.get('ReferenceId')
                    if ref_id in relevant_service_refs:
                        continue
                        
                    # Check if this service calls any relevant service
                    for edge in svc.get('Edges', []):
                        if edge.get('ReferenceId') in relevant_service_refs:
                            relevant_service_refs.add(ref_id)
                            added_new = True
                            break
                            
                    if ref_id in relevant_service_refs: continue
                    
                    # Check if any relevant service calls this service
                    for r_svc in all_services:
                        if r_svc.get('ReferenceId') in relevant_service_refs:
                            if any(e.get('ReferenceId') == ref_id for e in r_svc.get('Edges', [])):
                                relevant_service_refs.add(ref_id)
                                added_new = True
                                break
            
            # Filter the services list down to just the relevant sub-graph
            services = [s for s in all_services if s.get('ReferenceId') in relevant_service_refs]
            
            # 1. Map service IDs to readable names
            service_map = {}
            for svc in services:
                ref_id = svc.get('ReferenceId')
                name = svc.get('Name', 'UnknownService')
                svc_type = svc.get('Type', 'MICROSERVICE')
                state = svc.get('State', 'active')
                
                # Check for faults to mark health
                summary = svc.get('SummaryStatistics', {})
                faults = summary.get('FaultStatistics', {}).get('TotalCount', 0)
                errors = summary.get('ErrorStatistics', {}).get('TotalCount', 0)
                
                health = "HEALTHY"
                diag = None
                if faults > 0:
                    health = "CRITICAL"
                    diag = f"X-Ray reported {faults} faults for this service."
                elif errors > 0:
                    health = "DEGRADED"
                    diag = f"X-Ray reported {errors} errors for this service."
                    
                service_map[ref_id] = {
                    "name": name,
                    "type": "MICROSERVICE" if svc_type == 'client' else svc_type.upper(),
                    "state": state,
                    "health": health,
                    "diag": diag
                }
                
                node_id = name if name.startswith('arn:') or name.startswith('i-') else f"xray-{name}"
                
                self.add_node(
                    node_id=node_id,
                    node_type=service_map[ref_id]['type'],
                    label=name,
                    status=state,
                    metadata={"XRayReferenceId": ref_id, "Faults": faults, "Errors": errors},
                    health_state=health,
                    diagnostic=diag
                )
                
            # 2. Build edges based on service calls
            for svc in services:
                src_ref = svc.get('ReferenceId')
                src_name = svc.get('Name', '')
                src_node_id = src_name if src_name.startswith('arn:') or src_name.startswith('i-') else f"xray-{src_name}"
                
                edges = svc.get('Edges', [])
                for edge in edges:
                    target_ref = edge.get('ReferenceId')
                    target_info = service_map.get(target_ref)
                    
                    if target_info:
                        target_name = target_info['name']
                        target_node_id = target_name if target_name.startswith('arn:') or target_name.startswith('i-') else f"xray-{target_name}"
                        
                        # Edge level health based on fault/error stats in the edge itself
                        edge_health = "HEALTHY"
                        edge_summary = edge.get('SummaryStatistics', {})
                        edge_faults = edge_summary.get('FaultStatistics', {}).get('TotalCount', 0)
                        if edge_faults > 0:
                            edge_health = "CRITICAL"
                            
                        self.add_edge(src_node_id, target_node_id, 'INVOKES', health_state=edge_health)
                        
        except Exception as e:
            logger.warning(f"Failed to fetch X-Ray service graph: {e}")
