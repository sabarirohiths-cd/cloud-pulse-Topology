from .base_tracer import BaseTracer
import logging

logger = logging.getLogger(__name__)

class NetworkTracer(BaseTracer):
    def trace(self, vpc_id, subnet_ids, root_id):
        """
        Traces the physical network topology: VPC -> Subnets -> IGW / NAT
        """
        if not vpc_id:
            return

        try:
            # 1. Fetch VPC
            vpc_resp = self.ec2_client.describe_vpcs(VpcIds=[vpc_id])
            if vpc_resp.get('Vpcs'):
                vpc = vpc_resp['Vpcs'][0]
                vpc_name = next((t['Value'] for t in vpc.get('Tags', []) if t['Key'] == 'Name'), vpc_id)
                self.add_node(vpc_id, 'VPC', vpc_name, vpc.get('State', 'available'), {
                    "CidrBlock": vpc.get('CidrBlock'),
                    "InstanceTenancy": vpc.get('InstanceTenancy'),
                    "IsDefault": vpc.get('IsDefault')
                })
                
            # 2. Fetch Subnets
            if subnet_ids:
                sub_resp = self.ec2_client.describe_subnets(SubnetIds=subnet_ids)
                for sub in sub_resp.get('Subnets', []):
                    sub_id = sub['SubnetId']
                    sub_name = next((t['Value'] for t in sub.get('Tags', []) if t['Key'] == 'Name'), sub_id)
                    self.add_node(sub_id, 'SUBNET', sub_name, sub.get('State', 'available'), {
                        "CidrBlock": sub.get('CidrBlock'),
                        "AvailabilityZone": sub.get('AvailabilityZone'),
                        "AvailableIpAddressCount": sub.get('AvailableIpAddressCount'),
                        "MapPublicIpOnLaunch": sub.get('MapPublicIpOnLaunch')
                    })
                    
                    # Link VPC -> Subnet -> Resource
                    self.add_edge(vpc_id, sub_id, 'CONTAINS')
                    self.add_edge(sub_id, root_id, 'CONTAINS')
                    
            # 2.5 Fetch NACLs for the subnets
            if subnet_ids:
                try:
                    nacl_resp = self.ec2_client.describe_network_acls(
                        Filters=[{'Name': 'association.subnet-id', 'Values': subnet_ids}]
                    )
                    for nacl in nacl_resp.get('NetworkAcls', []):
                        nacl_id = nacl['NetworkAclId']
                        
                        inbound_rules = []
                        outbound_rules = []
                        
                        for entry in sorted(nacl.get('Entries', []), key=lambda x: x.get('RuleNumber', 0)):
                            rule_num = entry.get('RuleNumber')
                            if rule_num == 32767: # Default deny all
                                continue
                            
                            action = entry.get('RuleAction', '').upper()
                            protocol_num = str(entry.get('Protocol', '-1'))
                            protocol = 'ALL TRAFFIC' if protocol_num == '-1' else ('TCP' if protocol_num == '6' else ('UDP' if protocol_num == '17' else ('ICMP' if protocol_num == '1' else protocol_num)))
                            
                            if protocol == 'ALL TRAFFIC':
                                port_str = ""
                            else:
                                port = 'All Ports'
                                if 'PortRange' in entry:
                                    from_port = entry['PortRange'].get('From')
                                    to_port = entry['PortRange'].get('To')
                                    port = str(from_port) if from_port == to_port else f"{from_port}-{to_port}"
                                port_str = f" {port}"
                            
                            cidr = entry.get('CidrBlock', '0.0.0.0/0')
                            rule_str = f"#{rule_num} {action} {protocol}{port_str} {'to' if entry.get('Egress') else 'from'} {cidr}"
                            
                            if entry.get('Egress'):
                                outbound_rules.append(rule_str)
                            else:
                                inbound_rules.append(rule_str)
                                
                        for assoc in nacl.get('Associations', []):
                            assoc_subnet_id = assoc.get('SubnetId')
                            if assoc_subnet_id in subnet_ids:
                                self.add_node(assoc_subnet_id, 'SUBNET', assoc_subnet_id, 'available', {
                                    "NACL_Id": nacl_id,
                                    "InboundRules": inbound_rules,
                                    "OutboundRules": outbound_rules
                                })
                except Exception as e:
                    logger.warning(f"Failed to fetch Network ACLs (possibly missing ec2:DescribeNetworkAcls permission): {e}")
                            
            # 2.6 Fetch Route Tables for the subnets
            if subnet_ids:
                try:
                    rt_resp = self.ec2_client.describe_route_tables(
                        Filters=[{'Name': 'association.subnet-id', 'Values': subnet_ids}]
                    )
                    for rt in rt_resp.get('RouteTables', []):
                        rt_id = rt['RouteTableId']
                        routes = []
                        for route in rt.get('Routes', []):
                            dest = route.get('DestinationCidrBlock') or route.get('DestinationIpv6CidrBlock')
                            target = route.get('GatewayId') or route.get('NatGatewayId') or route.get('InstanceId') or route.get('VpcPeeringConnectionId') or route.get('TransitGatewayId') or "Local"
                            routes.append(f"{dest} -> {target}")
                            
                        for assoc in rt.get('Associations', []):
                            assoc_subnet_id = assoc.get('SubnetId')
                            if assoc_subnet_id in subnet_ids:
                                self.add_node(assoc_subnet_id, 'SUBNET', assoc_subnet_id, 'available', {
                                    "RouteTable_Id": rt_id,
                                    "Routes": routes
                                })
                except Exception as e:
                    logger.warning(f"Failed to fetch Route Tables (possibly missing ec2:DescribeRouteTables permission): {e}")
                    
            # 3. Fetch Internet Gateways (IGW)
            igw_resp = self.ec2_client.describe_internet_gateways(
                Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
            )
            for igw in igw_resp.get('InternetGateways', []):
                igw_id = igw['InternetGatewayId']
                igw_name = next((t['Value'] for t in igw.get('Tags', []) if t['Key'] == 'Name'), igw_id)
                attachment = next((a for a in igw.get('Attachments', []) if a.get('VpcId') == vpc_id), {})
                self.add_node(igw_id, 'IGW', igw_name, 'available', {
                    "AttachmentState": attachment.get('State')
                })
                self.add_edge(vpc_id, igw_id, 'ATTACHED_TO')
                
            # 4. Fetch NAT Gateways
            nat_resp = self.ec2_client.describe_nat_gateways(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            for nat in nat_resp.get('NatGateways', []):
                nat_id = nat['NatGatewayId']
                nat_state = nat.get('State', 'available')
                nat_name = next((t['Value'] for t in nat.get('Tags', []) if t['Key'] == 'Name'), nat_id)
                nat_subnet = nat.get('SubnetId')
                
                nat_ips = nat.get('NatGatewayAddresses', [])
                public_ip = nat_ips[0].get('PublicIp') if nat_ips else None
                private_ip = nat_ips[0].get('PrivateIp') if nat_ips else None
                
                self.add_node(nat_id, 'NAT', nat_name, nat_state, {
                    "PublicIp": public_ip,
                    "PrivateIp": private_ip
                })
                # Link it to the subnet it resides in
                if nat_subnet:
                    self.add_edge(nat_subnet, nat_id, 'ROUTES_TO')
                else:
                    self.add_edge(vpc_id, nat_id, 'ROUTES_TO')
                    
        except Exception as e:
            logger.warning(f"Failed to trace Environment/Networking resources for {root_id}: {e}")
