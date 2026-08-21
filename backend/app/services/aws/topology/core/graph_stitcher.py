import logging
logger = logging.getLogger(__name__)

class GraphStitcher:
    def __init__(self, regional_data, global_data=None):
        self.regional_data = regional_data
        self.global_data = global_data or {}
        self.all_vpcs = {}
        self.edges = []
        for region, vpcs in self.regional_data.items():
            for vpc in vpcs:
                self.all_vpcs[vpc['VpcId']] = vpc

    def stitch(self):
        logger.info("Stitching cross-region connections and extracting graph edges...")
        for region, vpcs in self.regional_data.items():
            for vpc in vpcs:
                self._validate_peering(vpc)
                self._extract_edges(vpc)
        
        self._extract_global_edges()
        return self.regional_data, self.edges

    def _validate_peering(self, vpc):
        for peer in vpc.get('PeeringConnections', []):
            accepter_id = peer.get('AccepterVpcId')
            if accepter_id and accepter_id not in self.all_vpcs:
                peer['IsExternal'] = True
            else:
                peer['IsExternal'] = False

    def _extract_edges(self, vpc):
        vpc_id = vpc.get('VpcId')
        # We can extract relationships from what we already have
        for subnet in vpc.get('Subnets', []):
            # EC2 Instances -> Security Groups
            for ec2 in subnet.get('Instances', []):
                for sg in ec2.get('SecurityGroups', []):
                    sg_id = sg.get('GroupId')
                    if sg_id:
                        self.edges.append({
                            'id': f"edge-{ec2.get('InstanceId')}-{sg_id}",
                            'source': ec2.get('InstanceId'),
                            'target': sg_id,
                            'type': 'security-attachment'
                        })
            # Subnet -> Network ACL
            network_acl = subnet.get('NetworkAclId')
            if network_acl:
                self.edges.append({
                    'id': f"edge-{subnet.get('SubnetId')}-{network_acl}",
                    'source': subnet.get('SubnetId'),
                    'target': network_acl,
                    'type': 'acl-attachment'
                })
                
            # Lambda -> SG
            for func in subnet.get('LambdaFunctions', []):
                for sg_id in func.get('SecurityGroupIds', []):
                    if sg_id:
                        self.edges.append({'id': f"edge-{func.get('FunctionName')}-{sg_id}", 'source': func.get('FunctionName'), 'target': sg_id, 'type': 'security-attachment'})
                        
            # EKS -> SG
            for eks in subnet.get('EKSClusters', []):
                for sg_id in eks.get('SecurityGroupIds', []):
                    if sg_id:
                        self.edges.append({'id': f"edge-{eks.get('ClusterName')}-{sg_id}", 'source': eks.get('ClusterName'), 'target': sg_id, 'type': 'security-attachment'})
                        
            # ECS -> SG
            for ecs in subnet.get('ECSClusters', []):
                for sg_id in ecs.get('SecurityGroupIds', []):
                    if sg_id:
                        self.edges.append({'id': f"edge-{ecs.get('ClusterName')}-{sg_id}", 'source': ecs.get('ClusterName'), 'target': sg_id, 'type': 'security-attachment'})
                        
        # Load Balancer -> Target Group -> EC2 Instances
        for elb in vpc.get('LoadBalancers', []):
            elb_arn = elb.get('LoadBalancerArn')
            elb_dns = elb.get('DNSName', '').lower()
            if not elb_arn: continue
            
            for tg in elb.get('TargetGroups', []):
                tg_arn = tg.get('TargetGroupArn')
                if tg_arn:
                    self.edges.append({
                        'id': f"edge-{elb_arn}-{tg_arn}",
                        'source': elb_arn,
                        'target': tg_arn,
                        'type': 'alb-tg-attachment'
                    })
                    
                    for target in tg.get('Targets', []):
                        inst_id = target.get('Id')
                        if inst_id:
                            self.edges.append({
                                'id': f"edge-{tg_arn}-{inst_id}",
                                'source': tg_arn,
                                'target': inst_id,
                                'type': 'tg-ec2-attachment'
                            })

        # ASG -> EC2
        for asg in vpc.get('AutoScalingGroups', []):
            asg_name = asg.get('AutoScalingGroupName')
            for inst_id in asg.get('InstanceIds', []):
                if inst_id:
                    self.edges.append({'id': f"edge-{asg_name}-{inst_id}", 'source': asg_name, 'target': inst_id, 'type': 'asg-attachment'})

        # Route Tables -> Subnets
        for rt in vpc.get('RouteTables', []):
            rt_id = rt.get('RouteTableId')
            for assoc in rt.get('Associations', []):
                subnet_id = assoc.get('SubnetId')
                if rt_id and subnet_id:
                    self.edges.append({
                        'id': f"edge-{rt_id}-{subnet_id}",
                        'source': rt_id,
                        'target': subnet_id,
                        'type': 'route-attachment'
                    })

        # RDS -> SG
        for rds in vpc.get('RDSInstances', []):
            rds_id = rds.get('DBInstanceIdentifier') or rds.get('DBClusterIdentifier')
            for sg_wrapper in rds.get('VpcSecurityGroups', []):
                sg_id = sg_wrapper.get('VpcSecurityGroupId')
                if rds_id and sg_id:
                    self.edges.append({
                        'id': f"edge-{rds_id}-{sg_id}",
                        'source': rds_id,
                        'target': sg_id,
                        'type': 'security-attachment'
                    })

        # Security Group -> Security Group (Rules)
        for sg in vpc.get('SecurityGroups', []):
            for rule in sg.get('IpPermissions', []):
                for pair in rule.get('UserIdGroupPairs', []):
                    ref_sg = pair.get('GroupId')
                    if ref_sg:
                        self.edges.append({
                            'id': f"edge-{sg.get('GroupId')}-{ref_sg}",
                            'source': sg.get('GroupId'),
                            'target': ref_sg,
                            'type': 'traffic-flow'
                        })

    def _extract_global_edges(self):
        # Build map of all ELB DNS names to their ARNs
        elb_dns_map = {}
        for region, vpcs in self.regional_data.items():
            for vpc in vpcs:
                for elb in vpc.get('LoadBalancers', []):
                    dns = elb.get('DNSName')
                    arn = elb.get('LoadBalancerArn')
                    if dns and arn:
                        elb_dns_map[dns.lower()] = arn

        # Route53 -> Load Balancer (or other targets)
        for zone in self.global_data.get('Route53HostedZones', []):
            zone_id = zone.get('Id')
            for record in zone.get('Records', []):
                for target in record.get('Targets', []):
                    target_lower = target.lower()
                    # Check if target matches any ELB DNS name
                    for elb_dns, elb_arn in elb_dns_map.items():
                        if elb_dns in target_lower or target_lower in elb_dns:
                            self.edges.append({
                                'id': f"edge-{zone_id}-{elb_arn}",
                                'source': zone_id,
                                'target': elb_arn,
                                'type': 'route53-alb-attachment'
                            })
                            break
