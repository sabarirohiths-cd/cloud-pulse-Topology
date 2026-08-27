from .base_tracer import BaseTracer
import logging

logger = logging.getLogger(__name__)

class SecurityTracer(BaseTracer):
    def trace(self, sg_ids):
        """
        Fetches and parses rules for the given Security Groups.
        Only keeps rules that reference CIDRs (e.g. 0.0.0.0/0, 10.0.0.0/16) or other SGs in the sg_ids list.
        Injects the parsed rules into the SG node metadata.
        """
        if not sg_ids:
            return

        # Deduplicate to avoid redundant calls
        sg_ids = list(set(sg_ids))
        
        try:
            # Chunking to avoid API limits if sg_ids is large (max 100 per call, usually we have < 10)
            for i in range(0, len(sg_ids), 100):
                chunk = sg_ids[i:i+100]
                resp = self.ec2_client.describe_security_groups(GroupIds=chunk)
                
                for sg in resp.get('SecurityGroups', []):
                    sg_id = sg['GroupId']
                    
                    inbound_rules = []
                    for perm in sg.get('IpPermissions', []):
                        protocol = perm.get('IpProtocol', '-1')
                        port = 'All' if protocol == '-1' else f"{perm.get('FromPort', 'Any')}-{perm.get('ToPort', 'Any')}"
                        if perm.get('FromPort') == perm.get('ToPort') and perm.get('FromPort') is not None:
                            port = str(perm.get('FromPort'))
                        
                        protocol_name = 'All' if protocol == '-1' else protocol.upper()
                        
                        for cidr in perm.get('IpRanges', []):
                            if cidr.get('CidrIp') == '0.0.0.0/0':
                                inbound_rules.append(f"Allow {protocol_name} {port} from Public (0.0.0.0/0)")
                            else:
                                inbound_rules.append(f"Allow {protocol_name} {port} from {cidr.get('CidrIp')}")
                                
                        for pair in perm.get('UserIdGroupPairs', []):
                            target_sg = pair.get('GroupId')
                            inbound_rules.append(f"Allow {protocol_name} {port} from {target_sg}")
                                
                    outbound_rules = []
                    for perm in sg.get('IpPermissionsEgress', []):
                        protocol = perm.get('IpProtocol', '-1')
                        port = 'All' if protocol == '-1' else f"{perm.get('FromPort', 'Any')}-{perm.get('ToPort', 'Any')}"
                        if perm.get('FromPort') == perm.get('ToPort') and perm.get('FromPort') is not None:
                            port = str(perm.get('FromPort'))
                        
                        protocol_name = 'All' if protocol == '-1' else protocol.upper()
                        
                        for cidr in perm.get('IpRanges', []):
                            if cidr.get('CidrIp') == '0.0.0.0/0':
                                outbound_rules.append(f"Allow {protocol_name} {port} to Public (0.0.0.0/0)")
                            else:
                                outbound_rules.append(f"Allow {protocol_name} {port} to {cidr.get('CidrIp')}")
                                
                        for pair in perm.get('UserIdGroupPairs', []):
                            target_sg = pair.get('GroupId')
                            outbound_rules.append(f"Allow {protocol_name} {port} to {target_sg}")

                    metadata_update = {
                        "Type": "Security Group",
                        "GroupId": sg_id
                    }
                    if inbound_rules:
                        metadata_update["InboundRules"] = inbound_rules
                    if outbound_rules:
                        metadata_update["OutboundRules"] = outbound_rules
                        
                    self.add_node(sg_id, 'SECURITY_GROUP', sg.get('GroupName', sg_id), 'available', metadata_update)

        except Exception as e:
            logger.warning(f"Failed to deeply trace Security Groups: {e}")
