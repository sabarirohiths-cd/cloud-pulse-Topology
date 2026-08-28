import logging
from datetime import datetime, timedelta
from .base_tracer import BaseTracer

logger = logging.getLogger(__name__)

class XRayTracer(BaseTracer):
    def trace(self, lookback_minutes: int):
        logger.info("Tracing dynamic service dependencies via X-Ray")
        
        xray_client = self.session.client('xray', region_name=self.region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)
        
        try:
            resp = xray_client.get_service_graph(
                StartTime=start_time,
                EndTime=end_time
            )
            
            services = resp.get('Services', [])
            
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
