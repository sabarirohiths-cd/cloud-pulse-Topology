import re
import logging

logger = logging.getLogger(__name__)

def extract_granular_locations(logs):
    """Extract file paths and line numbers from logs."""
    locations = set()
    # Matches patterns like Connector.java:42, app.py:104, utils.js:22
    pattern = re.compile(r'([a-zA-Z0-9_\-\.]+\.(?:java|py|js|ts|go|rb|cs|php|cpp|c|h)):(\d+)')
    
    for log in logs:
        matches = pattern.findall(log)
        for match in matches:
            locations.add(f"{match[0]}:{match[1]}")
            
    return list(locations)

def apply_why_inference_rules(logs, metrics, flow_logs, locations):
    """Apply heuristic rules to deduce root cause."""
    tags = set()
    reasoning = []
    
    cpu_max = metrics.get('cpu_max', 0)
    errors_5xx = metrics.get('errors_5xx', 0)
    reject_count = flow_logs.get('reject_count', 0)
    
    log_text = " ".join(logs).lower() if logs else ""
    
    # Rule 1: High CPU + OOM/Memory issues
    if cpu_max > 90 or 'oom' in log_text or 'outofmemory' in log_text or 'out of memory' in log_text:
        tags.add('RESOURCE_EXHAUSTION')
        reasoning.append("High CPU utilization or OutOfMemory errors detected. The instance may be undersized for the current load.")
        
    # Rule 2: Flow Log Rejects + Timeouts/Connection Errors
    if reject_count > 0:
        tags.add('NETWORK_BLOCKED')
        if 'timeout' in log_text or 'connection refused' in log_text or 'failed to query' in log_text or 'failed to connect' in log_text:
            reasoning.append(f"Network flow logs indicate {reject_count} REJECTED packets, and application logs show connection/timeout errors. A Security Group or NACL is likely blocking outbound/inbound traffic.")
        else:
            reasoning.append(f"Network flow logs indicate {reject_count} REJECTED packets. Check Security Group and NACL rules.")
            
    # Rule 3: Application Exceptions
    if 'nullreferenceexception' in log_text or 'nullpointerexception' in log_text:
        tags.add('CODE_EXCEPTION')
        reasoning.append("A Null Reference/Pointer exception was detected in the application logs, indicating an unhandled code-level error.")
        
    if errors_5xx > 0:
        tags.add('HTTP_5XX')
        reasoning.append(f"Load balancer reported {int(errors_5xx)} HTTP 5XX server errors.")
        
    if not tags:
        if logs:
            tags.add('APPLICATION_ERROR')
            reasoning.append("Application error logs were detected, but no specific network or resource bottlenecks were identified.")
        else:
            # Check if there's any anomaly in xray
            pass
            
    return {
        "tags": list(tags),
        "reasoning": " ".join(reasoning) if reasoning else ""
    }

def synthesize_root_cause(diagnostic_details):
    """
    Orchestrates synthesis by extracting raw data from the diagnostic details,
    running location extraction and inference rules.
    """
    try:
        app_details = diagnostic_details.get('application', {}).get('details', {})
        net_details = diagnostic_details.get('network_flow', {}).get('details', {})
        
        logs = app_details.get('logs', {}).get('traces', [])
        metrics = app_details.get('metrics', {})
        flow_logs = net_details if net_details else {}
        
        locations = extract_granular_locations(logs)
        inference = apply_why_inference_rules(logs, metrics, flow_logs, locations)
        
        # Determine overall health to skip synthesis if fully healthy
        is_healthy = diagnostic_details.get('application', {}).get('status') in [None, 'HEALTHY'] and \
                     diagnostic_details.get('network_flow', {}).get('status') in [None, 'HEALTHY'] and \
                     diagnostic_details.get('infrastructure', {}).get('status') in [None, 'HEALTHY']
                     
        if is_healthy and not inference['tags'] and not logs and not locations:
            statement = "All telemetry streams indicate the resource is operating normally."
            inference['tags'] = ['HEALTHY']
            inference['reasoning'] = "No anomalies detected in infrastructure, network flow, or application metrics/logs."
        else:
            if not inference['tags'] and not inference['reasoning']:
                inference['tags'].append('UNKNOWN')
                inference['reasoning'] = "Telemetry indicates potential issues, but no definitive root cause could be synthesized."
                
            # Build synthesis statement based on highest severity tag
            if 'NETWORK_BLOCKED' in inference['tags']:
                statement = "Network configuration is blocking traffic, leading to application connectivity failures."
            elif 'RESOURCE_EXHAUSTION' in inference['tags']:
                statement = "Resource exhaustion (CPU/Memory) is degrading application performance."
            elif 'CODE_EXCEPTION' in inference['tags'] or 'APPLICATION_ERROR' in inference['tags']:
                statement = "An application-level code exception is causing failures."
            elif 'HTTP_5XX' in inference['tags']:
                statement = "Backend servers are returning 5XX errors to clients."
            else:
                statement = "Anomalies detected across telemetry layers."
        
        return {
            "synthesis_statement": statement,
            "error_classification_tags": inference['tags'],
            "extracted_code_locations": locations,
            "why_analysis_reasoning": inference['reasoning']
        }
    except Exception as e:
        logger.error(f"Failed to synthesize root cause: {e}")
        return {
            "synthesis_statement": "Failed to run synthesis engine.",
            "error_classification_tags": ["SYNTHESIS_ERROR"],
            "extracted_code_locations": [],
            "why_analysis_reasoning": str(e)
        }
