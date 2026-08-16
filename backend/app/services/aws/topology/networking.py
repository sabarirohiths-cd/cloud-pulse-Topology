from .base import BaseTopologyBuilder

class NetworkingMixin(BaseTopologyBuilder):
    def _fetch_vpcs_and_subnets(self):
        print("Fetching Base VPCs and Subnets...")
        try:
            vpcs_resp = self.ec2.describe_vpcs()
            for vpc in vpcs_resp.get('Vpcs', []):
                vpc_id = vpc.get('VpcId')
                self.vpcs[vpc_id] = {
                    'VpcId': vpc_id,
                    'Name': self._safe_get_tag(vpc.get('Tags', []), 'Name'),
                    'CidrBlock': vpc.get('CidrBlock'),
                    'IsDefault': vpc.get('IsDefault'),
                    'State': vpc.get('State'),
                    'Subnets': [],
                    'InternetGateways': [],
                    'RouteTables': [],
                    'LoadBalancers': [],
                    'RDSInstances': [],
                    'PeeringConnections': [],
                    'TransitGatewayAttachments': [],
                    'VpnGateways': [],
                    'VpnConnections': [],
                    'RegionalQueues': [],
                    'NetworkFirewalls': []
                }
        except Exception as e:
            print(f"Error fetching VPCs: {e}")
            
        try:
            igw_resp = self.ec2.describe_internet_gateways()
            for igw in igw_resp.get('InternetGateways', []):
                for attachment in igw.get('Attachments', []):
                    vpc_id = attachment.get('VpcId')
                    if vpc_id in self.vpcs:
                        self.vpcs[vpc_id]['InternetGateways'].append({
                            'InternetGatewayId': igw.get('InternetGatewayId'),
                            'Name': self._safe_get_tag(igw.get('Tags', []), 'Name'),
                            'State': attachment.get('State')
                        })
        except Exception as e:
            print(f"Error fetching IGWs: {e}")

        try:
            subnets_resp = self.ec2.describe_subnets()
            for subnet in subnets_resp.get('Subnets', []):
                vpc_id = subnet.get('VpcId')
                if vpc_id in self.vpcs:
                    self.vpcs[vpc_id]['Subnets'].append({
                        'SubnetId': subnet.get('SubnetId'),
                        'Name': self._safe_get_tag(subnet.get('Tags', []), 'Name'),
                        'CidrBlock': subnet.get('CidrBlock'),
                        'AvailabilityZone': subnet.get('AvailabilityZone'),
                        'State': subnet.get('State'),
                        'MapPublicIpOnLaunch': subnet.get('MapPublicIpOnLaunch', False),
                        'Instances': [],
                        'NatGateways': [],
                        'EKSClusters': [],
                        'ECSClusters': [],
                        'VpcEndpoints': [],
                        'LambdaFunctions': [],
                        'ElastiCacheNodes': [],
                        'EFSMountTargets': [],
                        'AutoScalingGroups': [],
                        'UnclassifiedENIs': [],
                        'AmazonMQBrokers': [],
                        'MSKClusters': [],
                        'DocumentDBClusters': [],
                        'RedshiftClusters': [],
                        'SageMakerNotebooks': [],
                        'WorkSpaces': [],
                        'FSxFileSystems': [],
                        'OpenSearchDomains': [],
                        'NetworkFirewallEndpoints': [],
                        'Route53ResolverEndpoints': []
                    })
        except Exception as e:
            print(f"Error fetching Subnets: {e}")

    def _fetch_routes_nat(self):
        print("Fetching Route Tables and NAT Gateways...")
        subnet_map = self._get_subnet_map()
        try:
            rt_resp = self.ec2.describe_route_tables()
            for rt in rt_resp.get('RouteTables', []):
                vpc_id = rt.get('VpcId')
                if vpc_id in self.vpcs:
                    is_main = False
                    for assoc in rt.get('Associations', []):
                        if assoc.get('Main'):
                            is_main = True
                        sub_id = assoc.get('SubnetId')
                        if sub_id in subnet_map:
                            subnet_map[sub_id]['RouteTableId'] = rt.get('RouteTableId')
                    
                    self.vpcs[vpc_id]['RouteTables'].append({
                        'RouteTableId': rt.get('RouteTableId'),
                        'Name': self._safe_get_tag(rt.get('Tags', []), 'Name'),
                        'Routes': rt.get('Routes', []),
                        'IsMain': is_main
                    })
        except Exception:
            pass

        try:
            nat_resp = self.ec2.describe_nat_gateways()
            for nat in nat_resp.get('NatGateways', []):
                sub_id = nat.get('SubnetId')
                if sub_id in subnet_map:
                    subnet_map[sub_id]['NatGateways'].append({
                        'NatGatewayId': nat.get('NatGatewayId'),
                        'State': nat.get('State'),
                        'NatGatewayAddresses': [a.get('PublicIp') for a in nat.get('NatGatewayAddresses', [])],
                        'Name': self._safe_get_tag(nat.get('Tags', []), 'Name')
                    })
        except Exception:
            pass

    def _fetch_endpoints_peering(self):
        print("Fetching Endpoints and Peering...")
        subnet_map = self._get_subnet_map()
        try:
            eps_resp = self.ec2.describe_vpc_endpoints()
            for ep in eps_resp.get('VpcEndpoints', []):
                vpc_id = ep.get('VpcId')
                if vpc_id in self.vpcs:
                    ep_info = {
                        'VpcEndpointId': ep.get('VpcEndpointId'),
                        'ServiceName': ep.get('ServiceName'),
                        'VpcEndpointType': ep.get('VpcEndpointType')
                    }
                    for sid in ep.get('SubnetIds', []):
                        if sid in subnet_map:
                            subnet_map[sid]['VpcEndpoints'].append(ep_info)
        except Exception:
            pass

        try:
            peer_resp = self.ec2.describe_vpc_peering_connections()
            for peer in peer_resp.get('VpcPeeringConnections', []):
                vpc_id = peer.get('RequesterVpcInfo', {}).get('VpcId')
                if vpc_id in self.vpcs:
                    self.vpcs[vpc_id]['PeeringConnections'].append({
                        'VpcPeeringConnectionId': peer.get('VpcPeeringConnectionId'),
                        'Status': peer.get('Status', {}).get('Code'),
                        'AccepterVpcId': peer.get('AccepterVpcInfo', {}).get('VpcId')
                    })
        except Exception:
            pass

    def _fetch_tgw_nacl(self):
        print("Fetching TGWs and NACLs...")
        subnet_map = self._get_subnet_map()
        try:
            nacl_resp = self.ec2.describe_network_acls()
            for nacl in nacl_resp.get('NetworkAcls', []):
                nacl_id = nacl.get('NetworkAclId')
                for assoc in nacl.get('Associations', []):
                    sid = assoc.get('SubnetId')
                    if sid in subnet_map:
                        subnet_map[sid]['NetworkAclId'] = nacl_id
        except Exception:
            pass

        try:
            tgw_resp = self.ec2.describe_transit_gateway_vpc_attachments()
            for att in tgw_resp.get('TransitGatewayVpcAttachments', []):
                vpc_id = att.get('VpcId')
                if vpc_id in self.vpcs:
                    att_info = {
                        'TransitGatewayAttachmentId': att.get('TransitGatewayAttachmentId'),
                        'TransitGatewayId': att.get('TransitGatewayId'),
                        'State': att.get('State')
                    }
                    self.vpcs[vpc_id]['TransitGatewayAttachments'].append(att_info)
                    for sid in att.get('SubnetIds', []):
                        if sid in subnet_map:
                            subnet_map[sid]['TransitGatewayAttachments'].append(att_info)
        except Exception:
            pass

    def _fetch_vgw_vpn_eni(self):
        print("Fetching VGW, VPN, and ENIs...")
        subnet_map = self._get_subnet_map()
        try:
            vgw_resp = self.ec2.describe_vpn_gateways()
            for vgw in vgw_resp.get('VpnGateways', []):
                for att in vgw.get('VpcAttachments', []):
                    vpc_id = att.get('VpcId')
                    if vpc_id in self.vpcs:
                        self.vpcs[vpc_id]['VpnGateways'].append({
                            'VpnGatewayId': vgw.get('VpnGatewayId'),
                            'State': vgw.get('State'),
                            'Type': vgw.get('Type')
                        })
        except Exception:
            pass

        try:
            vpn_resp = self.ec2.describe_vpn_connections()
            for vpn in vpn_resp.get('VpnConnections', []):
                vgw_id = vpn.get('VpnGatewayId')
                for vpc in self.vpcs.values():
                    if any(v.get('VpnGatewayId') == vgw_id for v in vpc.get('VpnGateways', [])):
                        vpc['VpnConnections'].append({
                            'VpnConnectionId': vpn.get('VpnConnectionId'),
                            'State': vpn.get('State'),
                            'VpnGatewayId': vgw_id
                        })
                        break
        except Exception:
            pass

        try:
            eni_resp = self.ec2.describe_network_interfaces()
            for eni in eni_resp.get('NetworkInterfaces', []):
                sid = eni.get('SubnetId')
                if sid not in subnet_map:
                    continue
                type_ = eni.get('InterfaceType')
                desc = eni.get('Description', '').lower()
                
                if eni.get('Attachment', {}).get('InstanceId') or type_ in ['nat_gateway', 'vpc_endpoint', 'transit_gateway', 'network_load_balancer', 'vpc_endpoint']:
                    continue
                if any(k in desc for k in ['elb', 'rds', 'lambda', 'efs', 'eks', 'ecs', 'autoscaling']):
                    continue
                    
                subnet_map[sid]['UnclassifiedENIs'].append({
                    'NetworkInterfaceId': eni.get('NetworkInterfaceId'),
                    'PrivateIpAddress': eni.get('PrivateIpAddress'),
                    'InterfaceType': type_,
                    'Description': eni.get('Description')
                })
        except Exception:
            pass

    def _fetch_network_firewall(self):
        print("Fetching Network Firewall...")
        subnet_map = self._get_subnet_map()
        try:
            nfw_resp = self.network_firewall.list_firewalls()
            for fw in nfw_resp.get('Firewalls', []):
                fw_arn = fw.get('FirewallArn')
                fw_det = self.network_firewall.describe_firewall(FirewallArn=fw_arn)
                firewall = fw_det.get('Firewall', {})
                status = fw_det.get('FirewallStatus', {})
                vpc_id = firewall.get('VpcId')
                
                if vpc_id in self.vpcs:
                    self.vpcs[vpc_id]['NetworkFirewalls'].append({
                        'FirewallName': firewall.get('FirewallName'),
                        'FirewallId': firewall.get('FirewallId'),
                        'Status': status.get('Status')
                    })
                
                for mapping in firewall.get('SubnetMappings', []):
                    sid = mapping.get('SubnetId')
                    if sid in subnet_map:
                        subnet_map[sid]['NetworkFirewallEndpoints'].append({
                            'FirewallName': firewall.get('FirewallName'),
                            'IPAddressType': mapping.get('IPAddressType')
                        })
        except Exception:
            pass

    def _fetch_route53_resolvers(self):
        print("Fetching Route53 Resolvers...")
        subnet_map = self._get_subnet_map()
        try:
            r53_resp = self.route53resolver.list_resolver_endpoints()
            for ep in r53_resp.get('ResolverEndpoints', []):
                vpc_id = ep.get('HostVPCId')
                if vpc_id in self.vpcs:
                    ep_id = ep.get('Id')
                    ips_resp = self.route53resolver.list_resolver_endpoint_ip_addresses(ResolverEndpointId=ep_id)
                    for ip in ips_resp.get('IpAddresses', []):
                        sid = ip.get('SubnetId')
                        if sid in subnet_map:
                            subnet_map[sid]['Route53ResolverEndpoints'].append({
                                'ResolverEndpointId': ep_id,
                                'Name': ep.get('Name'),
                                'Direction': ep.get('Direction'),
                                'IpId': ip.get('IpId'),
                                'Ip': ip.get('Ip')
                            })
        except Exception:
            pass

    def _fetch_elb(self):
        print("Fetching Load Balancers...")
        try:
            elb_resp = self.elbv2.describe_load_balancers()
            for elb in elb_resp.get('LoadBalancers', []):
                vpc_id = elb.get('VpcId')
                if vpc_id in self.vpcs:
                    elb_info = {
                        'LoadBalancerName': elb.get('LoadBalancerName'),
                        'Scheme': elb.get('Scheme'),
                        'Type': elb.get('Type'),
                        'DNSName': elb.get('DNSName')
                    }
                    self.vpcs[vpc_id]['LoadBalancers'].append(elb_info)
        except Exception:
            pass
