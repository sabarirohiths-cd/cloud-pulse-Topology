class TopologyMapper:
    def __init__(self, raw_data):
        self.raw = raw_data
        self.vpcs = {}
        self.subnet_map = {}

    def map(self):
        self._initialize_vpcs()
        self._initialize_subnets()
        
        self._map_vpc_level_resources()
        self._map_subnet_level_resources()
        self._map_cross_level_resources()
        
        return self.vpcs

    def _initialize_vpcs(self):
        for v in self.raw.get('Vpcs', []):
            self.vpcs[v['VpcId']] = {
                'VpcId': v['VpcId'],
                'Name': v['Name'],
                'CidrBlock': v['CidrBlock'],
                'IsDefault': v['IsDefault'],
                'State': v['State'],
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
                'NetworkFirewalls': [],
                'EgressOnlyInternetGateways': [],
                'CarrierGateways': [],
                'DhcpOptions': [],
                'FlowLogs': [],
                'SecurityAndCompliance': [],
                'HybridConnectivity': [],
                'SecurityGroups': [],
                'NetworkAcls': [],
                'ElasticIps': []
            }

    def _initialize_subnets(self):
        for s in self.raw.get('Subnets', []):
            vpc_id = s.get('VpcId')
            if vpc_id in self.vpcs:
                subnet_obj = {
                    'SubnetId': s['SubnetId'],
                    'Name': s['Name'],
                    'CidrBlock': s['CidrBlock'],
                    'AvailabilityZone': s['AvailabilityZone'],
                    'State': s['State'],
                    'MapPublicIpOnLaunch': s['MapPublicIpOnLaunch'],
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
                    'Route53ResolverEndpoints': [],
                    'NeptuneClusters': [],
                    'DirectoryServices': [],
                    'AppRunnerVpcConnectors': [],
                    'EMRClusters': [],
                    'GlueConnections': [],
                    'GatewayLoadBalancers': [],
                    'GWLBEndpoints': [],
                    'MemoryDBClusters': [],
                    'FlowLogs': [],
                    'BatchComputeEnvironments': []
                }
                self.vpcs[vpc_id]['Subnets'].append(subnet_obj)
                self.subnet_map[s['SubnetId']] = subnet_obj

    def _map_vpc_level_resources(self):
        for igw in self.raw.get('InternetGateways', []):
            vpc_id = igw.pop('VpcId', None)
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['InternetGateways'].append(igw)
                
        for rt in self.raw.get('RouteTables', []):
            vpc_id = rt.pop('VpcId', None)
            assoc_subnets = rt.pop('AssociatedSubnetIds', [])
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['RouteTables'].append(rt)
                for sid in assoc_subnets:
                    if sid in self.subnet_map:
                        self.subnet_map[sid]['RouteTableId'] = rt['RouteTableId']

        for peer in self.raw.get('PeeringConnections', []):
            vpc_id = peer.pop('VpcId', None)
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['PeeringConnections'].append(peer)
                
        for tgw in self.raw.get('TransitGatewayAttachments', []):
            vpc_id = tgw.pop('VpcId', None)
            subnets = tgw.pop('SubnetIds', [])
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['TransitGatewayAttachments'].append(tgw)
                for sid in subnets:
                    if sid in self.subnet_map:
                        self.subnet_map[sid]['TransitGatewayAttachments'].append(tgw.copy())
                        
        for vgw in self.raw.get('VpnGateways', []):
            vpc_id = vgw.pop('VpcId', None)
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['VpnGateways'].append(vgw)
                
        for vpn in self.raw.get('VpnConnections', []):
            vgw_id = vpn.get('VpnGatewayId')
            for vpc in self.vpcs.values():
                if any(v.get('VpnGatewayId') == vgw_id for v in vpc.get('VpnGateways', [])):
                    vpc['VpnConnections'].append(vpn)
                    break
                    
        for nfw in self.raw.get('NetworkFirewalls', []):
            vpc_id = nfw.pop('VpcId', None)
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['NetworkFirewalls'].append(nfw)
                
        for elb in self.raw.get('LoadBalancers', []):
            vpc_id = elb.pop('VpcId', None)
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['LoadBalancers'].append(elb)
                
        for rds in self.raw.get('RDSInstances', []):
            vpc_id = rds.pop('VpcId', None)
            if vpc_id == "FALLBACK_TO_FIRST_VPC":
                if self.vpcs:
                    first_vpc_id = list(self.vpcs.keys())[0]
                    self.vpcs[first_vpc_id]['RDSInstances'].append(rds)
            elif vpc_id in self.vpcs:
                self.vpcs[vpc_id]['RDSInstances'].append(rds)
                
        for eigw in self.raw.get('EgressOnlyInternetGateways', []):
            vpc_id = eigw.pop('VpcId', None)
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['EgressOnlyInternetGateways'].append(eigw)

        for sg in self.raw.get('SecurityGroups', []):
            vpc_id = sg.get('VpcId')
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['SecurityGroups'].append(sg.copy())

        for nacl in self.raw.get('NetworkAcls', []):
            vpc_id = nacl.get('VpcId')
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['NetworkAcls'].append(nacl.copy())

        for eip in self.raw.get('ElasticIps', []):
            for vpc in self.vpcs.values():
                vpc['ElasticIps'].append(eip.copy())

        for cg in self.raw.get('CarrierGateways', []):
            vpc_id = cg.pop('VpcId', None)
            if vpc_id in self.vpcs:
                self.vpcs[vpc_id]['CarrierGateways'].append(cg)

        # DHCP Options can apply to multiple VPCs if fetched holistically, but we just inject to all for now or we map it if it had vpcId
        # Actually DHCP Options are assigned to VPCs via Vpc's DhcpOptionsId. But we didn't extract that in Vpc. 
        # We will just inject all DhcpOptions to all VPCs as requested (account level or regional)
        for dhcp in self.raw.get('DhcpOptions', []):
            for vpc in self.vpcs.values():
                vpc['DhcpOptions'].append(dhcp.copy())

        for q in self.raw.get('RegionalQueues', []):
            for vpc in self.vpcs.values():
                vpc['RegionalQueues'].append(q.copy())

        for sec in self.raw.get('SecurityAndCompliance', []):
            for vpc in self.vpcs.values():
                vpc['SecurityAndCompliance'].append(sec.copy())

        for hc in self.raw.get('HybridConnectivity', []):
            for vpc in self.vpcs.values():
                vpc['HybridConnectivity'].append(hc.copy())

        # Map Transit Gateway Route Tables to the TGW Attachments
        tgw_rt_map = {}
        for rt in self.raw.get('TransitGatewayRouteTables', []):
            att_id = rt.get('TransitGatewayAttachmentId')
            if att_id not in tgw_rt_map:
                tgw_rt_map[att_id] = []
            tgw_rt_map[att_id].append(rt)

        for vpc in self.vpcs.values():
            for att in vpc['TransitGatewayAttachments']:
                att_id = att.get('TransitGatewayAttachmentId')
                if att_id in tgw_rt_map:
                    att['RouteTables'] = tgw_rt_map[att_id]

    def _map_subnet_level_resources(self):
        def add_to_subnet(resource_list_name, target_array_name, has_subnet_ids=False):
            for item in self.raw.get(resource_list_name, []):
                if has_subnet_ids:
                    sids = item.pop('SubnetIds', [])
                    for sid in sids:
                        if sid in self.subnet_map:
                            self.subnet_map[sid][target_array_name].append(item.copy())
                else:
                    sid = item.pop('SubnetId', None)
                    if sid in self.subnet_map:
                        self.subnet_map[sid][target_array_name].append(item)

        add_to_subnet('NatGateways', 'NatGateways')
        add_to_subnet('VpcEndpoints', 'VpcEndpoints', has_subnet_ids=True)
        add_to_subnet('UnclassifiedENIs', 'UnclassifiedENIs')
        add_to_subnet('NetworkFirewallEndpoints', 'NetworkFirewallEndpoints')
        add_to_subnet('Route53ResolverEndpoints', 'Route53ResolverEndpoints')
        
        add_to_subnet('EKSClusters', 'EKSClusters', has_subnet_ids=True)
        add_to_subnet('ECSClusters', 'ECSClusters', has_subnet_ids=True)
        add_to_subnet('LambdaFunctions', 'LambdaFunctions', has_subnet_ids=True)
        add_to_subnet('SageMakerNotebooks', 'SageMakerNotebooks')
        add_to_subnet('WorkSpaces', 'WorkSpaces')
        add_to_subnet('ElastiCacheNodes', 'ElastiCacheNodes')
        add_to_subnet('DocumentDBClusters', 'DocumentDBClusters', has_subnet_ids=True)
        add_to_subnet('RedshiftClusters', 'RedshiftClusters', has_subnet_ids=True)
        add_to_subnet('EFSMountTargets', 'EFSMountTargets')
        add_to_subnet('FSxFileSystems', 'FSxFileSystems', has_subnet_ids=True)
        add_to_subnet('AmazonMQBrokers', 'AmazonMQBrokers', has_subnet_ids=True)
        add_to_subnet('MSKClusters', 'MSKClusters', has_subnet_ids=True)
        add_to_subnet('OpenSearchDomains', 'OpenSearchDomains', has_subnet_ids=True)
        add_to_subnet('NeptuneClusters', 'NeptuneClusters', has_subnet_ids=True)
        add_to_subnet('DirectoryServices', 'DirectoryServices', has_subnet_ids=True)
        add_to_subnet('AppRunnerVpcConnectors', 'AppRunnerVpcConnectors', has_subnet_ids=True)
        add_to_subnet('EMRClusters', 'EMRClusters', has_subnet_ids=True)
        add_to_subnet('GlueConnections', 'GlueConnections')
        add_to_subnet('GatewayLoadBalancers', 'GatewayLoadBalancers', has_subnet_ids=True)
        add_to_subnet('GWLBEndpoints', 'GWLBEndpoints', has_subnet_ids=True)
        add_to_subnet('MemoryDBClusters', 'MemoryDBClusters', has_subnet_ids=True)
        add_to_subnet('BatchComputeEnvironments', 'BatchComputeEnvironments', has_subnet_ids=True)
        
        for nacl in self.raw.get('NetworkAcls', []):
            for assoc in nacl.get('Associations', []):
                sid = assoc.get('SubnetId')
                if sid in self.subnet_map:
                    self.subnet_map[sid]['NetworkAclId'] = nacl.get('NetworkAclId')

        for fl in self.raw.get('FlowLogs', []):
            res_id = fl.get('ResourceId')
            if res_id in self.vpcs:
                self.vpcs[res_id]['FlowLogs'].append(fl.copy())
            elif res_id in self.subnet_map:
                self.subnet_map[res_id]['FlowLogs'].append(fl.copy())

    def _map_cross_level_resources(self):
        # 1. Security Groups
        sg_map = {sg['GroupId']: sg for sg in self.raw.get('SecurityGroups', [])}
        
        # 2. Map Instances
        instance_map = {}
        for inst in self.raw.get('Instances', []):
            sid = inst.pop('SubnetId', None)
            if sid in self.subnet_map:
                resolved_sgs = []
                for sg_id in inst.get('SecurityGroupIds', []):
                    if sg_id in sg_map:
                        resolved_sgs.append(sg_map[sg_id])
                inst['SecurityGroups'] = resolved_sgs
                if 'SecurityGroupIds' in inst:
                    del inst['SecurityGroupIds']
                
                self.subnet_map[sid]['Instances'].append(inst)
                instance_map[inst['InstanceId']] = inst
                
        # 3. Map ASGs to Subnets and Instances
        for asg in self.raw.get('AutoScalingGroups', []):
            sids = asg.pop('SubnetIds', [])
            inst_ids = asg.pop('InstanceIds', [])
            
            for sid in sids:
                if sid in self.subnet_map:
                    self.subnet_map[sid]['AutoScalingGroups'].append(asg.copy())
            
            for iid in inst_ids:
                if iid in instance_map:
                    instance_map[iid]['AutoScalingGroupName'] = asg['AutoScalingGroupName']
                    
        # 4. Map EIPs to Instances
        for eip in self.raw.get('ElasticIps', []):
            iid = eip.get('InstanceId')
            if iid in instance_map:
                instance_map[iid].setdefault('ElasticIps', []).append({'PublicIp': eip.get('PublicIp')})
                
        # 5. Map EBS to Instances
        for ebs in self.raw.get('EbsVolumes', []):
            iid = ebs.pop('InstanceId', None)
            if iid in instance_map:
                instance_map[iid].setdefault('EbsVolumes', []).append(ebs)
