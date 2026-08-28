import logging
from typing import Dict, Any, List
from .base_layer import DiagnosticLayer

logger = logging.getLogger(__name__)

class InfrastructureLayer(DiagnosticLayer):
    @property
    def layer_name(self) -> str:
        return "infrastructure"

    def analyze(self, instance_id: str, fetcher: Any, options: List[str], lookback_minutes: int) -> Dict[str, Any]:
        logger.info(f"Running Infrastructure Layer analysis for {instance_id}")
        
        node = next((n for n in fetcher.nodes if n['id'] == instance_id), None)
        if not node:
            return {"status": "UNKNOWN", "summary": "Node not found in topology graph."}
            
        details = {}
        status = "HEALTHY"
        issues = []
        checks_passed = 0
        total_checks = 4
        
        # 1. EC2 Status Checks (3/3)
        status_checks = node.get("metadata", {}).get("status_checks", {})
        if status_checks:
            details["ec2_status_checks"] = status_checks
            if status_checks.get("summary", "").startswith("3/3") or status_checks.get("summary", "").startswith("2/2"):
                checks_passed += 1
            else:
                issues.append("EC2 Status Checks failed (Impaired/Failing).")
                status = "CRITICAL"
        else:
            details["ec2_status_checks"] = {"summary": "Unknown - Not present"}
            issues.append("EC2 Status Checks data missing.")
            
        # Extract related infrastructure via edges
        sg_ids = []
        subnet_id = None
        
        for e in fetcher.edges:
            if e['target'] == instance_id:
                if e['relation'] == 'PROTECTS' and e['source'].startswith('sg-'):
                    sg_ids.append(e['source'])
                elif e['relation'] == 'CONTAINS' and e['source'].startswith('subnet-'):
                    subnet_id = e['source']
                    
        # 2. Security Groups
        details["security_groups"] = []
        if sg_ids:
            for sg_id in sg_ids:
                sg_node = next((n for n in fetcher.nodes if n['id'] == sg_id), None)
                if sg_node:
                    sg_meta = sg_node.get("metadata", {})
                    inbound = sg_meta.get("InboundRules", [])
                    outbound = sg_meta.get("OutboundRules", [])
                    details["security_groups"].append({
                        "id": sg_id,
                        "name": sg_node.get("label", sg_id),
                        "inbound_rules_count": len(inbound),
                        "outbound_rules_count": len(outbound)
                    })
                    if not inbound and not outbound:
                        issues.append(f"Security Group {sg_id} has no rules defined.")
                        status = "DEGRADED" if status != "CRITICAL" else status
            if details["security_groups"]:
                checks_passed += 1
        else:
            issues.append("No Security Groups found protecting this instance.")
            status = "DEGRADED" if status != "CRITICAL" else status
            
        # 3 & 4. Subnet NACLs and Route Tables
        details["subnet"] = {"id": subnet_id}
        if subnet_id:
            subnet_node = next((n for n in fetcher.nodes if n['id'] == subnet_id), None)
            if subnet_node:
                sub_meta = subnet_node.get("metadata", {})
                
                # NACLs
                if "NACL_Id" in sub_meta:
                    details["subnet"]["nacl"] = {
                        "id": sub_meta["NACL_Id"],
                        "inbound_rules_count": len(sub_meta.get("InboundRules", [])),
                        "outbound_rules_count": len(sub_meta.get("OutboundRules", []))
                    }
                    checks_passed += 1
                else:
                    details["subnet"]["nacl"] = "Not found"
                    issues.append(f"No NACL data for subnet {subnet_id}.")
                    
                # Route Tables
                if "RouteTable_Id" in sub_meta:
                    details["subnet"]["route_table"] = {
                        "id": sub_meta["RouteTable_Id"],
                        "routes_count": len(sub_meta.get("Routes", []))
                    }
                    checks_passed += 1
                else:
                    details["subnet"]["route_table"] = "Not found"
                    issues.append(f"No Route Table data for subnet {subnet_id}.")
        else:
            issues.append("Instance is not associated with any known Subnet.")
            
        summary = f"{checks_passed}/{total_checks} Infra pre-checks passed."
        if issues:
            summary += f" Issues: {'; '.join(issues)}"
            
        return {
            "status": status,
            "summary": summary,
            "details": details,
            "issues": issues
        }
