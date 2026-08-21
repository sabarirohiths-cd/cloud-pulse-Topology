import logging
logger = logging.getLogger(__name__)

from ..core.base import BaseTopologyBuilder

class NetworkingMixin(BaseTopologyBuilder):
    def _fetch_vpcs_and_subnets(self):
        logger.debug("Fetching Base VPCs and Subnets...")
        try:
            vpcs_resp = self.ec2.describe_vpcs()
            for vpc in vpcs_resp.get('Vpcs', []):
                self.raw_data['Vpcs'].append({
                    'VpcId': vpc.get('VpcId'),
                    'Name': self._safe_get_tag(vpc.get('Tags', []), 'Name'),
                    'CidrBlock': vpc.get('CidrBlock'),
                    'IsDefault': vpc.get('IsDefault'),
                    'State': vpc.get('State')
                })
        except Exception as e:
            logger.debug(f"Error fetching VPCs: {e}")
            
        try:
            igw_resp = self.ec2.describe_internet_gateways()
            for igw in igw_resp.get('InternetGateways', []):
                for attachment in igw.get('Attachments', []):
                    self.raw_data['InternetGateways'].append({
                        'VpcId': attachment.get('VpcId'),
                        'InternetGatewayId': igw.get('InternetGatewayId'),
                        'Name': self._safe_get_tag(igw.get('Tags', []), 'Name'),
                        'State': attachment.get('State')
                    })
        except Exception as e:
            logger.debug(f"Error fetching IGWs: {e}")

        try:
            subnets_resp = self.ec2.describe_subnets()
            for subnet in subnets_resp.get('Subnets', []):
                self.raw_data['Subnets'].append({
                    'VpcId': subnet.get('VpcId'),
                    'SubnetId': subnet.get('SubnetId'),
                    'Name': self._safe_get_tag(subnet.get('Tags', []), 'Name'),
                    'CidrBlock': subnet.get('CidrBlock'),
                    'AvailabilityZone': subnet.get('AvailabilityZone'),
                    'State': subnet.get('State'),
                    'MapPublicIpOnLaunch': subnet.get('MapPublicIpOnLaunch', False)
                })
        except Exception as e:
            logger.debug(f"Error fetching Subnets: {e}")

    def _fetch_routes_nat(self):
        logger.debug("Fetching Route Tables and NAT Gateways...")
        try:
            rt_resp = self.ec2.describe_route_tables()
            for rt in rt_resp.get('RouteTables', []):
                is_main = False
                assoc_subnets = []
                for assoc in rt.get('Associations', []):
                    if assoc.get('Main'):
                        is_main = True
                    sub_id = assoc.get('SubnetId')
                    if sub_id:
                        assoc_subnets.append(sub_id)
                
                self.raw_data['RouteTables'].append({
                    'VpcId': rt.get('VpcId'),
                    'RouteTableId': rt.get('RouteTableId'),
                    'Name': self._safe_get_tag(rt.get('Tags', []), 'Name'),
                    'Routes': rt.get('Routes', []),
                    'IsMain': is_main,
                    'AssociatedSubnetIds': assoc_subnets
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            nat_resp = self.ec2.describe_nat_gateways()
            for nat in nat_resp.get('NatGateways', []):
                self.raw_data['NatGateways'].append({
                    'SubnetId': nat.get('SubnetId'),
                    'NatGatewayId': nat.get('NatGatewayId'),
                    'State': nat.get('State'),
                    'NatGatewayAddresses': [a.get('PublicIp') for a in nat.get('NatGatewayAddresses', [])],
                    'Name': self._safe_get_tag(nat.get('Tags', []), 'Name')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_endpoints_peering(self):
        logger.debug("Fetching Endpoints and Peering...")
        try:
            eps_resp = self.ec2.describe_vpc_endpoints()
            for ep in eps_resp.get('VpcEndpoints', []):
                if ep.get('VpcEndpointType') == 'GatewayLoadBalancer':
                    self.raw_data['GWLBEndpoints'].append({
                        'SubnetIds': ep.get('SubnetIds', []),
                        'VpcEndpointId': ep.get('VpcEndpointId'),
                        'ServiceName': ep.get('ServiceName'),
                        'State': ep.get('State')
                    })
                else:
                    self.raw_data['VpcEndpoints'].append({
                        'VpcId': ep.get('VpcId'),
                        'SubnetIds': ep.get('SubnetIds', []),
                        'VpcEndpointId': ep.get('VpcEndpointId'),
                        'ServiceName': ep.get('ServiceName'),
                        'VpcEndpointType': ep.get('VpcEndpointType')
                    })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            peer_resp = self.ec2.describe_vpc_peering_connections()
            for peer in peer_resp.get('VpcPeeringConnections', []):
                self.raw_data['PeeringConnections'].append({
                    'VpcId': peer.get('RequesterVpcInfo', {}).get('VpcId'),
                    'VpcPeeringConnectionId': peer.get('VpcPeeringConnectionId'),
                    'Status': peer.get('Status', {}).get('Code'),
                    'AccepterVpcId': peer.get('AccepterVpcInfo', {}).get('VpcId')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_tgw(self):
        logger.debug("Fetching TGWs...")

        try:
            tgw_resp = self.ec2.describe_transit_gateway_vpc_attachments()
            for att in tgw_resp.get('TransitGatewayVpcAttachments', []):
                self.raw_data['TransitGatewayAttachments'].append({
                    'VpcId': att.get('VpcId'),
                    'SubnetIds': att.get('SubnetIds', []),
                    'TransitGatewayAttachmentId': att.get('TransitGatewayAttachmentId'),
                    'TransitGatewayId': att.get('TransitGatewayId'),
                    'State': att.get('State'),
                    'RouteTables': []
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_tgw_route_tables(self):
        logger.debug("Fetching TGW Route Tables...")
        try:
            rt_resp = self.ec2.describe_transit_gateway_route_tables()
            for rt in rt_resp.get('TransitGatewayRouteTables', []):
                rt_id = rt.get('TransitGatewayRouteTableId')
                assoc_resp = self.ec2.get_transit_gateway_route_table_associations(TransitGatewayRouteTableId=rt_id)
                for assoc in assoc_resp.get('Associations', []):
                    if assoc.get('ResourceType') == 'vpc':
                        self.raw_data['TransitGatewayRouteTables'].append({
                            'TransitGatewayAttachmentId': assoc.get('TransitGatewayAttachmentId'),
                            'TransitGatewayRouteTableId': rt_id,
                            'State': rt.get('State')
                        })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_vgw_vpn_eni(self):
        logger.debug("Fetching VGW, VPN, and ENIs...")
        try:
            vgw_resp = self.ec2.describe_vpn_gateways()
            for vgw in vgw_resp.get('VpnGateways', []):
                for att in vgw.get('VpcAttachments', []):
                    self.raw_data['VpnGateways'].append({
                        'VpcId': att.get('VpcId'),
                        'VpnGatewayId': vgw.get('VpnGatewayId'),
                        'State': vgw.get('State'),
                        'Type': vgw.get('Type')
                    })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            vpn_resp = self.ec2.describe_vpn_connections()
            for vpn in vpn_resp.get('VpnConnections', []):
                self.raw_data['VpnConnections'].append({
                    'VpnConnectionId': vpn.get('VpnConnectionId'),
                    'State': vpn.get('State'),
                    'VpnGatewayId': vpn.get('VpnGatewayId')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            eni_resp = self.ec2.describe_network_interfaces()
            for eni in eni_resp.get('NetworkInterfaces', []):
                type_ = eni.get('InterfaceType')
                desc = eni.get('Description', '').lower()
                
                if eni.get('Attachment', {}).get('InstanceId') or type_ in ['nat_gateway', 'vpc_endpoint', 'transit_gateway', 'network_load_balancer']:
                    continue
                if any(k in desc for k in ['elb', 'rds', 'lambda', 'efs', 'eks', 'ecs', 'autoscaling']):
                    continue
                    
                self.raw_data['UnclassifiedENIs'].append({
                    'SubnetId': eni.get('SubnetId'),
                    'NetworkInterfaceId': eni.get('NetworkInterfaceId'),
                    'PrivateIpAddress': eni.get('PrivateIpAddress'),
                    'InterfaceType': type_,
                    'Description': eni.get('Description')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_network_firewall(self):
        logger.debug("Fetching Network Firewall...")
        try:
            nfw_resp = self.network_firewall.list_firewalls()
            for fw in nfw_resp.get('Firewalls', []):
                fw_arn = fw.get('FirewallArn')
                fw_det = self.network_firewall.describe_firewall(FirewallArn=fw_arn)
                firewall = fw_det.get('Firewall', {})
                status = fw_det.get('FirewallStatus', {})
                
                self.raw_data['NetworkFirewalls'].append({
                    'VpcId': firewall.get('VpcId'),
                    'FirewallName': firewall.get('FirewallName'),
                    'FirewallId': firewall.get('FirewallId'),
                    'Status': status.get('Status')
                })
                
                for mapping in firewall.get('SubnetMappings', []):
                    self.raw_data['NetworkFirewallEndpoints'].append({
                        'SubnetId': mapping.get('SubnetId'),
                        'FirewallName': firewall.get('FirewallName'),
                        'IPAddressType': mapping.get('IPAddressType')
                    })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_route53_resolvers(self):
        logger.debug("Fetching Route53 Resolvers...")
        try:
            r53_resp = self.route53resolver.list_resolver_endpoints()
            for ep in r53_resp.get('ResolverEndpoints', []):
                ep_id = ep.get('Id')
                ips_resp = self.route53resolver.list_resolver_endpoint_ip_addresses(ResolverEndpointId=ep_id)
                for ip in ips_resp.get('IpAddresses', []):
                    self.raw_data['Route53ResolverEndpoints'].append({
                        'SubnetId': ip.get('SubnetId'),
                        'ResolverEndpointId': ep_id,
                        'Name': ep.get('Name'),
                        'Direction': ep.get('Direction'),
                        'IpId': ip.get('IpId'),
                        'Ip': ip.get('Ip')
                    })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_elb(self):
        logger.debug("Fetching Load Balancers and Target Groups...")
        try:
            elb_resp = self.elbv2.describe_load_balancers()
            for elb in elb_resp.get('LoadBalancers', []):
                elb_arn = elb.get('LoadBalancerArn')
                tgs = []
                try:
                    tg_resp = self.elbv2.describe_target_groups(LoadBalancerArn=elb_arn)
                    for tg in tg_resp.get('TargetGroups', []):
                        tg_arn = tg.get('TargetGroupArn')
                        targets = []
                        try:
                            health_resp = self.elbv2.describe_target_health(TargetGroupArn=tg_arn)
                            for th in health_resp.get('TargetHealthDescriptions', []):
                                target = th.get('Target', {})
                                targets.append({
                                    'Id': target.get('Id'),
                                    'Port': target.get('Port'),
                                    'Health': th.get('TargetHealth', {}).get('State')
                                })
                        except Exception as e:
                            logger.debug(f"Error fetching target health for {tg_arn}: {e}")
                            
                        tgs.append({
                            'TargetGroupName': tg.get('TargetGroupName'),
                            'TargetGroupArn': tg_arn,
                            'Targets': targets
                        })
                except Exception as e:
                    logger.debug(f"Error fetching target groups for {elb_arn}: {e}")
                    
                self.raw_data['LoadBalancers'].append({
                    'VpcId': elb.get('VpcId'),
                    'LoadBalancerName': elb.get('LoadBalancerName'),
                    'LoadBalancerArn': elb_arn,
                    'Scheme': elb.get('Scheme'),
                    'Type': elb.get('Type'),
                    'DNSName': elb.get('DNSName'),
                    'TargetGroups': tgs
                })
        except Exception as e:
            logger.debug(f"Error fetching ELB: {e}")

    def _fetch_gateway_load_balancers(self):
        logger.debug("Fetching Gateway Load Balancers...")
        try:
            elb_resp = self.elbv2.describe_load_balancers()
            for elb in elb_resp.get('LoadBalancers', []):
                if elb.get('Type') == 'gateway':
                    sids = [az.get('SubnetId') for az in elb.get('AvailabilityZones', []) if az.get('SubnetId')]
                    self.raw_data['GatewayLoadBalancers'].append({
                        'SubnetIds': sids,
                        'LoadBalancerArn': elb.get('LoadBalancerArn'),
                        'DNSName': elb.get('DNSName'),
                        'State': elb.get('State', {}).get('Code')
                    })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_directory_service(self):
        logger.debug("Fetching Directory Service...")
        try:
            ds_resp = self.ds.describe_directories()
            for ds in ds_resp.get('DirectoryDescriptions', []):
                vpc_settings = ds.get('VpcSettings', {})
                sids = vpc_settings.get('SubnetIds', [])
                self.raw_data['DirectoryServices'].append({
                    'SubnetIds': sids,
                    'DirectoryId': ds.get('DirectoryId'),
                    'Name': ds.get('Name'),
                    'Type': ds.get('Type'),
                    'Size': ds.get('Size')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_advanced_gateways_and_dhcp(self):
        logger.debug("Fetching Advanced Gateways and DHCP...")
        try:
            eigw_resp = self.ec2.describe_egress_only_internet_gateways()
            for eigw in eigw_resp.get('EgressOnlyInternetGateways', []):
                for att in eigw.get('Attachments', []):
                    self.raw_data['EgressOnlyInternetGateways'].append({
                        'VpcId': att.get('VpcId'),
                        'EgressOnlyInternetGatewayId': eigw.get('EgressOnlyInternetGatewayId'),
                        'State': att.get('State')
                    })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            cgs_resp = self.ec2.describe_carrier_gateways()
            for cg in cgs_resp.get('CarrierGateways', []):
                self.raw_data['CarrierGateways'].append({
                    'VpcId': cg.get('VpcId'),
                    'CarrierGatewayId': cg.get('CarrierGatewayId'),
                    'State': cg.get('State')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            dhcp_resp = self.ec2.describe_dhcp_options()
            for dhcp in dhcp_resp.get('DhcpOptions', []):
                self.raw_data['DhcpOptions'].append({
                    'DhcpOptionsId': dhcp.get('DhcpOptionsId'),
                    'DhcpConfigurations': dhcp.get('DhcpConfigurations', [])
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_flow_logs(self):
        logger.debug("Fetching Flow Logs...")
        try:
            fl_resp = self.ec2.describe_flow_logs()
            for fl in fl_resp.get('FlowLogs', []):
                self.raw_data['FlowLogs'].append({
                    'ResourceId': fl.get('ResourceId'),
                    'FlowLogId': fl.get('FlowLogId'),
                    'FlowLogStatus': fl.get('FlowLogStatus'),
                    'LogGroupName': fl.get('LogGroupName')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_hybrid_connectivity(self):
        logger.debug("Fetching Hybrid Connectivity...")
        try:
            dc_resp = self.directconnect.describe_connections()
            for conn in dc_resp.get('connections', []):
                self.raw_data['HybridConnectivity'].append({
                    'Type': 'DirectConnect',
                    'ConnectionId': conn.get('connectionId'),
                    'ConnectionName': conn.get('connectionName'),
                    'ConnectionState': conn.get('connectionState'),
                    'Bandwidth': conn.get('bandwidth')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            cn_resp = self.networkmanager.list_core_networks()
            for cn in cn_resp.get('CoreNetworks', []):
                self.raw_data['HybridConnectivity'].append({
                    'Type': 'CoreNetwork',
                    'CoreNetworkId': cn.get('CoreNetworkId'),
                    'State': cn.get('State')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_security_compliance(self):
        logger.debug("Fetching Security & Compliance...")
        status = {'GuardDutyStatus': 'NOT_ENABLED', 'ConfigStatus': 'NOT_RECORDING'}
        
        try:
            gd_resp = self.guardduty.list_detectors()
            detectors = gd_resp.get('DetectorIds', [])
            if detectors:
                det_info = self.guardduty.get_detector(DetectorId=detectors[0])
                if det_info.get('Status') == 'ENABLED':
                    status['GuardDutyStatus'] = 'ACTIVE'
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            cfg_resp = self.config.describe_configuration_recorder_status()
            for rec in cfg_resp.get('ConfigurationRecordersStatus', []):
                if rec.get('recording'):
                    status['ConfigStatus'] = 'RECORDING'
                    break
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        self.raw_data['SecurityAndCompliance'].append(status)

    def _fetch_security_groups(self):
        logger.debug("Fetching Security Groups...")
        try:
            sg_resp = self.ec2.describe_security_groups()
            for sg in sg_resp.get('SecurityGroups', []):
                self.raw_data['SecurityGroups'].append({
                    'GroupId': sg.get('GroupId'),
                    'GroupName': sg.get('GroupName'),
                    'Description': sg.get('Description'),
                    'VpcId': sg.get('VpcId'),
                    'InboundRules': sg.get('IpPermissions', []),
                    'OutboundRules': sg.get('IpPermissionsEgress', [])
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_network_acls(self):
        logger.debug("Fetching Network ACLs...")
        try:
            nacl_resp = self.ec2.describe_network_acls()
            for nacl in nacl_resp.get('NetworkAcls', []):
                self.raw_data['NetworkAcls'].append({
                    'NetworkAclId': nacl.get('NetworkAclId'),
                    'VpcId': nacl.get('VpcId'),
                    'Entries': nacl.get('Entries', []),
                    'Associations': nacl.get('Associations', [])
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_elastic_ips(self):
        logger.debug("Fetching Elastic IPs...")
        try:
            addr_resp = self.ec2.describe_addresses()
            for addr in addr_resp.get('Addresses', []):
                self.raw_data['ElasticIps'].append({
                    'PublicIp': addr.get('PublicIp'),
                    'AllocationId': addr.get('AllocationId'),
                    'InstanceId': addr.get('InstanceId'),
                    'NetworkInterfaceId': addr.get('NetworkInterfaceId'),
                    'PrivateIpAddress': addr.get('PrivateIpAddress')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")
