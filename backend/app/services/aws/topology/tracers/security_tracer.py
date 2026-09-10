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
        
        import botocore.exceptions
        try:
            # Chunking to avoid API limits if sg_ids is large (max 100 per call, usually we have < 10)
            paginator = self.ec2_client.get_paginator('describe_security_groups')
            for i in range(0, len(sg_ids), 100):
                chunk = sg_ids[i:i+100]
                
                for page in paginator.paginate(GroupIds=chunk):
                    for sg in page.get('SecurityGroups', []):
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

                        node = next((n for n in self.fetcher.nodes if n['id'] == sg_id), None)
                        if node:
                            if 'metadata' not in node:
                                node['metadata'] = {}
                            node['metadata']['Inbound Rules'] = inbound_rules
                            node['metadata']['Outbound Rules'] = outbound_rules
                            if sg.get('GroupName'):
                                node['metadata']['GroupName'] = sg.get('GroupName')
                                node['label'] = f"{sg.get('GroupName')} ({sg_id})"
                                
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
                if hasattr(self.fetcher, 'warnings'):
                    self.fetcher.warnings.append("Warning: Could not fetch Security Group rules due to missing IAM permissions (ec2:DescribeSecurityGroups).")
            logger.warning(f"Failed to fetch Security Groups: {e}")
        except Exception as e:
            logger.warning(f"Failed to parse security groups: {e}")
