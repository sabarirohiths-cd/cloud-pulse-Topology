import re
import logging

logger = logging.getLogger(__name__)

def extract_granular_locations(logs):
    """Extract file paths, line numbers, and structured exception names from logs."""
    locations = set()
    # Matches patterns like Connector.java:42, app.py:104, utils.js:22
    file_pattern = re.compile(r'([a-zA-Z0-9_\-\.]+\.(?:java|py|js|ts|go|rb|cs|php|cpp|c|h)):(\d+)')
    # Matches exceptions like java.lang.NullPointerException, KeyError, etc.
    exc_pattern = re.compile(r'\b([a-zA-Z0-9_\.]+(?:Exception|Error))\b')
    
    for log in logs:
        # Files
        for match in file_pattern.findall(log):
            locations.add(f"{match[0]}:{match[1]}")
        # Exceptions
        for match in exc_pattern.findall(log):
            locations.add(match)
            
    return list(locations)

def apply_why_inference_rules(logs, metrics, flow_logs, locations, diagnostic_details):
    """Apply heuristic rules to deduce root cause."""
    tags = set()
    reasoning = []
    remediation = []
    
    cpu_max = metrics.get('cpu_max', 0)
    mem_used = metrics.get('mem_used_percent', 0)
    errors_5xx = metrics.get('errors_5xx', 0)
    reject_count = flow_logs.get('reject_count', 0)
    
    log_text = " ".join(logs).lower() if logs else ""
    infra_details = diagnostic_details.get('infrastructure', {}).get('details', {})
    
    # Rule 1: High CPU / Memory issues
    if cpu_max > 90 or mem_used > 90 or 'oom' in log_text or 'outofmemory' in log_text:
        tags.add('RESOURCE_EXHAUSTION')
        reasons = []
        if cpu_max > 90: reasons.append(f"High CPU utilization ({cpu_max:.1f}%).")
        if mem_used > 90: reasons.append(f"Memory exhaustion ({mem_used:.1f}%).")
        if 'oom' in log_text or 'outofmemory' in log_text: reasons.append("Out of Memory logs detected.")
        reasoning.append(" ".join(reasons) + " The instance may be undersized for the current load.")
        
        remediation.append("Consider upgrading the instance type (e.g., from t3.micro to t3.small).")
        remediation.append("Set up or adjust Auto Scaling to handle increased load.")
        remediation.append("Profile the application for memory leaks.")
        
    # Rule 2: Flow Log Rejects + Timeouts/Connection Errors
    if reject_count > 0:
        tags.add('NETWORK_BLOCKED')
        if 'timeout' in log_text or 'connection refused' in log_text or 'failed to query' in log_text or 'failed to connect' in log_text:
            reasoning.append(f"Network flow logs indicate {reject_count} REJECTED packets, and application logs show connection/timeout errors. A Security Group or NACL is likely blocking outbound/inbound traffic.")
            remediation.append("Verify the Security Group attached to the resource allows inbound/outbound traffic on the required ports.")
        else:
            reasoning.append(f"Network flow logs indicate {reject_count} REJECTED packets. Check Security Group and NACL rules.")
            remediation.append("Review VPC Flow Logs to identify the specific source IP and port being rejected.")
            remediation.append("Update Security Group or Network ACL rules to allow legitimate traffic.")
            
    # Rule 3: Target Group / Load Balancer Health
    tgs = infra_details.get('target_groups', [])
    unhealthy_tg_count = sum(1 for tg in tgs if tg.get('unhealthy_count', 0) > 0)
    if unhealthy_tg_count > 0:
        tags.add('TARGET_GROUP_UNHEALTHY')
        reasoning.append(f"{unhealthy_tg_count} target group(s) have unhealthy instances failing health checks.")
        remediation.append("Ensure the application is running and listening on the target port on the registered instances.")
        remediation.append("Verify the load balancer health check path (e.g. /health) returns a 200 OK status.")
        remediation.append("Check if a Security Group on the target instances is blocking the Load Balancer from reaching them.")

    # Rule 4: X-Ray / App Issues
    app_details = diagnostic_details.get('application', {}).get('details', {}) if isinstance(diagnostic_details.get('application'), dict) else {}
    xray_details = app_details.get('xray', {})
    if xray_details.get('faulty_trace_count', 0) > 0:
        tags.add('APPLICATION_ERROR')
        failing_services = xray_details.get('failing_services', [])
        if failing_services:
            reasoning.append(f"AWS X-Ray indicates downstream failures caused by: {', '.join(failing_services)}.")
            remediation.append("Review X-Ray Service Map for the specific downstream bottlenecks identified.")
        else:
            reasoning.append("AWS X-Ray detected faulty or slow application traces.")
            remediation.append("Review X-Ray Service Map and individual traces to identify the exact code path causing high latency or faults.")

    # Rule 4: Application Exceptions
    if 'nullreferenceexception' in log_text or 'nullpointerexception' in log_text:
        tags.add('CODE_EXCEPTION')
        reasoning.append("A Null Reference/Pointer exception was detected in the application logs, indicating an unhandled code-level error.")
        remediation.append("Review the application code stack traces to fix the unhandled exception.")
        
    # Rule 5: HTTP 5XX Errors
    if errors_5xx > 0:
        tags.add('HTTP_5XX')
        reasoning.append(f"Load balancer reported {int(errors_5xx)} HTTP 5XX server errors.")
        remediation.append("Check the backend application logs for crashes or unhandled exceptions.")
        remediation.append("Verify that the backend database or dependencies are reachable and not timing out.")
        
    # Fallback Rule
    if not tags:
        if logs:
            tags.add('APPLICATION_ERROR')
            reasoning.append("Application error logs were detected, but no specific network or resource bottlenecks were identified.")
            remediation.append("Review application logs to identify specific failure modes.")
            
    return {
        "tags": list(tags),
        "reasoning": " ".join(reasoning) if reasoning else "",
        "remediation_steps": remediation
    }

def synthesize_root_cause(diagnostic_details):
    """
    Orchestrates synthesis by extracting raw data from the diagnostic details,
    running location extraction and inference rules.
    """
    try:
        app_layer = diagnostic_details.get('application')
        app_details = app_layer.get('details', {}) if isinstance(app_layer, dict) else {}
        
        net_layer = diagnostic_details.get('network_flow')
        net_details = net_layer.get('details', {}) if isinstance(net_layer, dict) else {}
        
        logs = app_details.get('logs', {}).get('traces', [])
        metrics = app_details.get('metrics', {})
        flow_logs = net_details if net_details else {}
        
        locations = extract_granular_locations(logs)
        inference = apply_why_inference_rules(logs, metrics, flow_logs, locations, diagnostic_details)
        
        # Determine overall health to skip synthesis if fully healthy
        app_status = app_layer.get('status') if isinstance(app_layer, dict) else None
        net_status = net_layer.get('status') if isinstance(net_layer, dict) else None
        infra_layer = diagnostic_details.get('infrastructure')
        infra_status = infra_layer.get('status') if isinstance(infra_layer, dict) else None
        
        is_healthy = app_status in [None, 'HEALTHY'] and \
                     net_status in [None, 'HEALTHY'] and \
                     infra_status in [None, 'HEALTHY']
                     
        if is_healthy and not inference['tags'] and not logs and not locations:
            statement = "All telemetry streams indicate the resource is operating normally."
            inference['tags'] = ['HEALTHY']
            inference['reasoning'] = "No anomalies detected in infrastructure, network flow, or application metrics/logs."
            inference['remediation_steps'] = ["No action required. Architecture is healthy."]
        else:
            if not inference['tags'] and not inference['reasoning']:
                inference['tags'].append('UNKNOWN')
                inference['reasoning'] = "Telemetry indicates potential issues, but no definitive root cause could be synthesized."
                inference['remediation_steps'] = ["Manually review CloudWatch metrics and logs for the resource.", "Ensure application tracers are properly configured."]
                
            # Build synthesis statement based on highest severity tag
            if 'NETWORK_BLOCKED' in inference['tags']:
                statement = "Network configuration is blocking traffic, leading to connectivity failures."
            elif 'RESOURCE_EXHAUSTION' in inference['tags']:
                statement = "Resource exhaustion (CPU/Memory) is degrading application performance."
            elif 'TARGET_GROUP_UNHEALTHY' in inference['tags']:
                statement = "Load balancer targets are unhealthy, disrupting traffic distribution."
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
            "why_analysis_reasoning": inference['reasoning'],
            "remediation_steps": inference['remediation_steps']
        }
    except Exception as e:
        logger.error(f"Failed to synthesize root cause: {e}")
        return {
            "synthesis_statement": "Failed to run synthesis engine.",
            "error_classification_tags": ["SYNTHESIS_ERROR"],
            "extracted_code_locations": [],
            "why_analysis_reasoning": str(e),
            "remediation_steps": ["Check backend system logs for synthesis engine errors."]
        }
