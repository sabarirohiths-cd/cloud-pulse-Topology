import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .base_layer import DiagnosticLayer

logger = logging.getLogger(__name__)

class NetworkFlowLayer(DiagnosticLayer):
    @property
    def layer_name(self) -> str:
        return "network_flow"

    def analyze(self, instance_id: str, fetcher: Any, options: List[str], lookback_minutes: int) -> Dict[str, Any]:
        logger.info(f"Running Network Flow Layer analysis for {instance_id}")
        
        node = next((n for n in fetcher.nodes if n['id'] == instance_id), None)
        if not node:
            return {"status": "UNKNOWN", "summary": "Node not found"}
            
        eni_id = None
        vpc_id = None
        
        # Extract ENI and VPC
        meta = node.get('metadata', {})
        vpc_id = meta.get('VpcId')
        interfaces = meta.get('NetworkInterfaces', [])
        if interfaces:
            eni_id = interfaces[0].get('NetworkInterfaceId')
            
        if not eni_id or not vpc_id:
            return {
                "status": "UNKNOWN",
                "summary": "Could not identify Network Interface (ENI) or VPC ID for this instance.",
                "details": {"eni_id": eni_id, "vpc_id": vpc_id}
            }
            
        # Discover Flow Log Group
        ec2 = fetcher.session.client('ec2', region_name=fetcher.region)
        logs = fetcher.session.client('logs', region_name=fetcher.region)
        
        log_group_name = None
        try:
            # Check for Flow Logs on the ENI or VPC
            flow_resp = ec2.describe_flow_logs(
                Filters=[
                    {'Name': 'resource-id', 'Values': [eni_id, vpc_id]}
                ]
            )
            for fl in flow_resp.get('FlowLogs', []):
                if fl.get('FlowLogStatus') == 'ACTIVE' and fl.get('LogGroupName'):
                    log_group_name = fl.get('LogGroupName')
                    break
        except Exception as e:
            logger.warning(f"Failed to describe flow logs: {e}")
            
        if not log_group_name:
            return {
                "status": "UNKNOWN", 
                "summary": f"VPC Flow Logs are not enabled or pushing to CloudWatch Logs for ENI {eni_id} / VPC {vpc_id}.",
                "details": {"eni_id": eni_id, "vpc_id": vpc_id, "flow_logs_enabled": False}
            }
            
        # Query Logs for REJECT
        end_time = int(time.time())
        start_time = end_time - (lookback_minutes * 60)
        
        # VPC Flow Logs default format: 
        # version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status
        query = f"fields @timestamp, @message | filter @message like '{eni_id}' | filter @message like 'REJECT' | sort @timestamp desc | limit 10"
        
        try:
            start_resp = logs.start_query(
                logGroupName=log_group_name,
                startTime=start_time,
                endTime=end_time,
                queryString=query
            )
            
            query_id = start_resp['queryId']
            results = []
            
            for _ in range(5):
                time.sleep(1)
                res = logs.get_query_results(queryId=query_id)
                if res['status'] == 'Complete':
                    results = res.get('results', [])
                    break
                    
            if results:
                return {
                    "status": "CRITICAL",
                    "summary": f"Found {len(results)} REJECTED flow log entries for {eni_id}. Firewall or NACL is blocking traffic.",
                    "details": {
                        "eni_id": eni_id,
                        "log_group": log_group_name,
                        "reject_count": len(results),
                        "sample_logs": [next((f['value'] for f in r if f['field'] == '@message'), '') for r in results]
                    }
                }
            else:
                return {
                    "status": "HEALTHY",
                    "summary": f"No REJECTED packets detected for {eni_id} in the last {lookback_minutes}m.",
                    "details": {
                        "eni_id": eni_id,
                        "log_group": log_group_name,
                        "reject_count": 0
                    }
                }
                
        except Exception as e:
            logger.warning(f"Failed to query CloudWatch Logs Insights for Flow Logs: {e}")
            return {
                "status": "UNKNOWN",
                "summary": f"Failed to query Flow Logs: {e}"
            }
