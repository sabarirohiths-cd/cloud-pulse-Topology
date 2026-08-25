import logging

logger = logging.getLogger(__name__)

class EC2FlowFetcher:
    def __init__(self, session, region: str, resource_id: str):
        self.session = session
        self.region = region
        self.resource_id = resource_id
        
        self.ec2_client = self.session.client('ec2', region_name=self.region)
        self.elbv2_client = self.session.client('elbv2', region_name=self.region)
        self.route53_client = self.session.client('route53', region_name=self.region)
        self.rds_client = self.session.client('rds', region_name=self.region)
        self.autoscaling_client = self.session.client('autoscaling', region_name=self.region)
        
        self.nodes = []
        self.edges = []
        
    def _add_node(self, node_id, node_type, label, status, metadata=None, health_state="HEALTHY", diagnostic=None):
        if not any(n['id'] == node_id for n in self.nodes):
            self.nodes.append({
                "id": node_id,
                "type": node_type,
                "label": label,
                "status": status,
                "metadata": metadata or {},
                "health_state": health_state,
                "diagnostic": diagnostic
            })
            
    def _add_edge(self, source, target, relation, health_state="HEALTHY", diagnostic=None):
        if not any(e['source'] == source and e['target'] == target and e['relation'] == relation for e in self.edges):
            self.edges.append({
                "source": source,
                "target": target,
                "relation": relation,
                "health_state": health_state,
                "diagnostic": diagnostic
            })

    def fetch(self):
        logger.info(f"Tracing EC2 Flow for instance {self.resource_id}")
        
        # 1. Fetch EC2 Instance
        response = self.ec2_client.describe_instances(InstanceIds=[self.resource_id])
        if not response['Reservations'] or not response['Reservations'][0]['Instances']:
            raise ValueError(f"EC2 Instance {self.resource_id} not found.")
            
        instance = response['Reservations'][0]['Instances'][0]
        state = instance.get('State', {}).get('Name', 'unknown')
        private_ip = instance.get('PrivateIpAddress')
        vpc_id = instance.get('VpcId')
        
        # Extract Name tag for proper labeling
        name_tag = next((t['Value'] for t in instance.get('Tags', []) if t['Key'] == 'Name'), None)
        node_label = name_tag or self.resource_id
        
        sg_ids = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]
        
        ec2_health = "HEALTHY"
        ec2_diag = None
        try:
            status_resp = self.ec2_client.describe_instance_status(InstanceIds=[self.resource_id])
            if status_resp.get('InstanceStatuses'):
                st = status_resp['InstanceStatuses'][0]
                sys_st = st.get('SystemStatus', {}).get('Status')
                inst_st = st.get('InstanceStatus', {}).get('Status')
                if sys_st == 'impaired' or inst_st == 'impaired':
                    ec2_health = "CRITICAL"
                    ec2_diag = f"System: {sys_st}, Instance: {inst_st}. OS/Hardware status check failing."
        except Exception as e:
            logger.warning(f"Failed to fetch EC2 status: {e}")
            
        # Network Interfaces (ENI) & Elastic IPs
        enis = []
        for eni in instance.get('NetworkInterfaces', []):
            eni_info = {"NetworkInterfaceId": eni.get('NetworkInterfaceId')}
            if eni.get('Association', {}).get('PublicIp'):
                eni_info['ElasticIp'] = eni['Association']['PublicIp']
            enis.append(eni_info)
            
        self._add_node(self.resource_id, 'EC2', node_label, state, {
            "InstanceType": instance.get('InstanceType'),
            "PrivateIpAddress": private_ip,
            "PublicIpAddress": instance.get('PublicIpAddress'),
            "VpcId": vpc_id,
            "SubnetId": instance.get('SubnetId'),
            "NetworkInterfaces": enis
        }, health_state=ec2_health, diagnostic=ec2_diag)
        
        # 2. Fetch Attached EBS
        vol_ids = [mapping.get('Ebs', {}).get('VolumeId') for mapping in instance.get('BlockDeviceMappings', []) if mapping.get('Ebs', {}).get('VolumeId')]
        if vol_ids:
            try:
                vols_resp = self.ec2_client.describe_volumes(VolumeIds=vol_ids)
                for vol in vols_resp.get('Volumes', []):
                    vol_id = vol['VolumeId']
                    vol_state = vol.get('State', 'attached')
                    v_health = "HEALTHY"
                    v_diag = None
                    
                    if vol_state == 'error':
                        v_health = "CRITICAL"
                        v_diag = "EBS Volume IOPS degraded or failed."
                        
                    self._add_node(vol_id, 'EBS', vol_id, vol_state, {
                        "SizeGB": vol.get('Size'),
                        "VolumeType": vol.get('VolumeType'),
                        "IOPS": vol.get('Iops')
                    }, health_state=v_health, diagnostic=v_diag)
                    self._add_edge(self.resource_id, vol_id, 'MOUNTS')
            except Exception as e:
                logger.warning(f"Failed to describe EBS volumes: {e}")
                
        # 3. Trace Upstream (Target Groups -> ALBs -> Route53)
        target_groups = self.elbv2_client.describe_target_groups().get('TargetGroups', [])
        
        associated_tgs = []
        for tg in target_groups:
            if tg.get('VpcId') != vpc_id: continue
            
            tg_arn = tg['TargetGroupArn']
            try:
                health_response = self.elbv2_client.describe_target_health(TargetGroupArn=tg_arn)
                has_unhealthy = False
                for target_health in health_response.get('TargetHealthDescriptions', []):
                    if target_health.get('TargetHealth', {}).get('State') == 'unhealthy':
                        has_unhealthy = True
                    target_id = target_health.get('Target', {}).get('Id')
                    if target_id == self.resource_id or target_id == private_ip:
                        associated_tgs.append(tg)
                        tg_name = tg.get('TargetGroupName')
                        
                        tg_health = "CRITICAL" if has_unhealthy else "HEALTHY"
                        tg_diag = "Health check failed (502/Timeout). Web process may be down." if has_unhealthy else None
                        
                        self._add_node(tg_arn, 'TARGET_GROUP', tg_name, 'active', health_state=tg_health, diagnostic=tg_diag)
                        self._add_edge(tg_arn, self.resource_id, 'TARGETS')
                        break
            except Exception as e:
                logger.warning(f"Failed to fetch health for TG {tg_arn}: {e}")
                
        # Trace ALBs
        lb_dns_names = []
        alb_arns = []
        for tg in associated_tgs:
            for lb_arn in tg.get('LoadBalancerArns', []):
                if lb_arn in alb_arns: continue
                alb_arns.append(lb_arn)
                
                lbs = self.elbv2_client.describe_load_balancers(LoadBalancerArns=[lb_arn]).get('LoadBalancers', [])
                if lbs:
                    lb = lbs[0]
                    lb_name = lb.get('LoadBalancerName')
                    dns_name = lb.get('DNSName')
                    lb_dns_names.append(dns_name.lower())
                    
                    self._add_node(lb_arn, 'ALB', lb_name, lb.get('State', {}).get('Code', 'active'), {"DNSName": dns_name})
                    self._add_edge(lb_arn, tg['TargetGroupArn'], 'FORWARDS_TO')
                    
        # Trace Route53
        if lb_dns_names:
            zones = self.route53_client.list_hosted_zones().get('HostedZones', [])
            for zone in zones:
                zone_id = zone['Id']
                records = self.route53_client.list_resource_record_sets(HostedZoneId=zone_id).get('ResourceRecordSets', [])
                for record in records:
                    if record['Type'] in ['A', 'CNAME']:
                        match_found = False
                        
                        for val in record.get('ResourceRecords', []):
                            if any(lb_dns in val['Value'].lower() for lb_dns in lb_dns_names):
                                match_found = True
                                break
                                
                        if not match_found and 'AliasTarget' in record:
                            dns_name = record['AliasTarget'].get('DNSName', '').lower()
                            if any(lb_dns in dns_name for lb_dns in lb_dns_names):
                                match_found = True
                                
                        if match_found:
                            rec_name = record['Name'].strip('.')
                            self._add_node(rec_name, 'ROUTE53', rec_name, 'active')
                            for arn in alb_arns:
                                self._add_edge(rec_name, arn, 'ROUTES_TO')
        # --- Phase 1: Security Groups, IAM, and ASG ---
        # IAM Role
        iam_profile = instance.get('IamInstanceProfile', {})
        if iam_profile:
            iam_arn = iam_profile.get('Arn')
            if iam_arn:
                iam_id = iam_arn.split('/')[-1]
                self._add_node(iam_arn, 'IAM_ROLE', iam_id, 'available', {"Type": "Instance Profile"})
                self._add_edge(iam_arn, self.resource_id, 'GRANTS_ACCESS_TO')
        else:
            # Missing IAM Profile RCA
            ec2_tags = {t['Key']: t['Value'] for t in instance.get('Tags', [])}
            app_driven = any(k in ec2_tags for k in ['Project', 'App', 'Environment', 'Application'])
            if app_driven:
                # Flag degraded if an app might need permissions
                ec2_node = next((n for n in self.nodes if n['id'] == self.resource_id), None)
                if ec2_node:
                    ec2_node['health_state'] = "DEGRADED"
                    ec2_node['diagnostic'] = "No IAM Instance Profile attached. App may face AccessDenied errors."

        # Auto Scaling Group (ASG)
        asg_name = next((t['Value'] for t in instance.get('Tags', []) if t['Key'] == 'aws:autoscaling:groupName'), None)
        if asg_name:
            try:
                asg_resp = self.autoscaling_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
                for asg in asg_resp.get('AutoScalingGroups', []):
                    asg_health = "HEALTHY"
                    asg_diag = None
                    
                    # Check if this instance is terminating
                    for asg_inst in asg.get('Instances', []):
                        if asg_inst['InstanceId'] == self.resource_id:
                            if 'Terminating:Wait' in asg_inst['LifecycleState'] or asg_inst['HealthStatus'] == 'Unhealthy':
                                ec2_node = next((n for n in self.nodes if n['id'] == self.resource_id), None)
                                if ec2_node:
                                    ec2_node['health_state'] = "CRITICAL"
                                    ec2_node['diagnostic'] = "Instance is being terminated by ASG health checks."
                                asg_health = "CRITICAL"
                                asg_diag = f"Instance {self.resource_id} is unhealthy/terminating."
                            break
                            
                    self._add_node(asg_name, 'ASG', asg_name, 'active', {
                        "DesiredCapacity": asg.get('DesiredCapacity'),
                        "MinSize": asg.get('MinSize'),
                        "MaxSize": asg.get('MaxSize')
                    }, health_state=asg_health, diagnostic=asg_diag)
                    self._add_edge(asg_name, self.resource_id, 'MANAGES')
            except Exception as e:
                logger.warning(f"Failed to describe ASG {asg_name}: {e}")

        # Security Groups
        sg_ids = [sg.get('GroupId') for sg in instance.get('SecurityGroups', [])]
        for sg in instance.get('SecurityGroups', []):
            sg_id = sg.get('GroupId')
            sg_name = sg.get('GroupName')
            self._add_node(sg_id, 'SECURITY_GROUP', sg_name or sg_id, 'available', {"Type": "Security Group", "GroupId": sg_id})
            self._add_edge(sg_id, self.resource_id, 'PROTECTS')

        # Check RDS Databases (via SG)
        try:
            rds_client = self.session.client('rds')
            rds_instances = rds_client.describe_db_instances()
            
            for rds in rds_instances.get('DBInstances', []):
                rds_id = rds.get('DBInstanceIdentifier')
                rds_sgs = [sg.get('VpcSecurityGroupId') for sg in rds.get('VpcSecurityGroups', []) if sg.get('Status') == 'active']
                
                if rds.get('DBSubnetGroup', {}).get('VpcId') == vpc_id:
                    db_status = rds.get('DBInstanceStatus', 'available')
                    rds_health = "CRITICAL" if db_status != 'available' else "HEALTHY"
                    rds_diag = f"Database is {db_status}" if rds_health == "CRITICAL" else None
                    
                    try:
                        if not rds_sgs: continue
                        sg_response = self.ec2_client.describe_security_groups(GroupIds=rds_sgs)
                        linked = False
                        for sg in sg_response.get('SecurityGroups', []):
                            for rule in sg.get('IpPermissions', []):
                                for pair in rule.get('UserIdGroupPairs', []):
                                    if pair.get('GroupId') in sg_ids:
                                        linked = True
                                        break
                                if linked: break
                            if linked: break
                            
                        # Tag check for intent
                        ec2_tags = {t['Key']: t['Value'] for t in instance.get('Tags', [])}
                        rds_tags = {t['Key']: t['Value'] for t in rds.get('TagList', [])}
                        shared_tag = False
                        for key in ['Project', 'Environment', 'App', 'Application']:
                            if key in ec2_tags and key in rds_tags and ec2_tags[key] == rds_tags[key]:
                                shared_tag = True
                                break
                        if not shared_tag:
                            ec2_name = ec2_tags.get('Name', '').lower()
                            if ec2_name and (ec2_name in rds_id.lower() or rds_id.lower() in ec2_name):
                                shared_tag = True
                                
                        if linked:
                            self._add_node(rds_id, 'RDS', rds_id, db_status, {"Engine": rds.get('Engine')}, health_state=rds_health, diagnostic=rds_diag)
                            self._add_edge(self.resource_id, rds_id, 'QUERIES')
                        elif shared_tag:
                            self._add_node(rds_id, 'RDS', rds_id, db_status, {"Engine": rds.get('Engine')}, health_state=rds_health, diagnostic=rds_diag)
                            self._add_edge(self.resource_id, rds_id, 'QUERIES', health_state="BLOCKED", diagnostic="Missing SG Ingress Rule on Port 3306")
                    except Exception as e:
                        logger.warning(f"Failed to trace RDS SG {rds_sgs}: {e}")
        except Exception as e:
            logger.warning(f"Failed to trace RDS: {e}")
            
        # --- Phase 2: Caching & Shared Storage ---
        # Check ElastiCache
        try:
            elasticache = self.session.client('elasticache')
            clusters_resp = elasticache.describe_cache_clusters()
            for cluster in clusters_resp.get('CacheClusters', []):
                cluster_sgs = [sg.get('SecurityGroupId') for sg in cluster.get('SecurityGroups', [])]
                if cluster_sgs and sg_ids:
                    try:
                        sg_response = self.ec2_client.describe_security_groups(GroupIds=cluster_sgs)
                        linked = False
                        for sg_obj in sg_response.get('SecurityGroups', []):
                            for rule in sg_obj.get('IpPermissions', []):
                                for pair in rule.get('UserIdGroupPairs', []):
                                    if pair.get('GroupId') in sg_ids:
                                        linked = True
                                        break
                                if linked: break
                            if linked: break
                        
                        if linked:
                            cluster_id = cluster.get('CacheClusterId')
                            self._add_node(cluster_id, 'ELASTICACHE', cluster_id, cluster.get('CacheClusterStatus'), {"Engine": cluster.get('Engine')})
                            self._add_edge(self.resource_id, cluster_id, 'QUERIES')
                    except Exception as e:
                        logger.warning(f"Failed to trace ElastiCache SG: {e}")
        except Exception as e:
            logger.warning(f"Failed to trace ElastiCache: {e}")
            
        # Check EFS
        try:
            efs = self.session.client('efs')
            fs_resp = efs.describe_file_systems()
            for fs in fs_resp.get('FileSystems', []):
                fs_id = fs.get('FileSystemId')
                try:
                    mt_resp = efs.describe_mount_targets(FileSystemId=fs_id)
                    linked = False
                    for mt in mt_resp.get('MountTargets', []):
                        mt_sg_resp = efs.describe_mount_target_security_groups(MountTargetId=mt.get('MountTargetId'))
                        mt_sgs = mt_sg_resp.get('SecurityGroups', [])
                        
                        if mt_sgs and sg_ids:
                            sg_response = self.ec2_client.describe_security_groups(GroupIds=mt_sgs)
                            for sg_obj in sg_response.get('SecurityGroups', []):
                                for rule in sg_obj.get('IpPermissions', []):
                                    for pair in rule.get('UserIdGroupPairs', []):
                                        if pair.get('GroupId') in sg_ids:
                                            linked = True
                                            break
                                    if linked: break
                                if linked: break
                        if linked: break
                    
                    if linked:
                        self._add_node(fs_id, 'EFS', fs_id, fs.get('LifeCycleState'), {"CreationTime": str(fs.get('CreationTime'))})
                        self._add_edge(self.resource_id, fs_id, 'MOUNTS')
                except Exception as e:
                    logger.warning(f"Failed to trace EFS Mount Targets for {fs_id}: {e}")
        except Exception as e:
            logger.warning(f"Failed to trace EFS: {e}")
            
        # --- Phase 3: The Environment (Networking) ---
        if vpc_id:
            try:
                # 1. Fetch VPC
                vpc_resp = self.ec2_client.describe_vpcs(VpcIds=[vpc_id])
                if vpc_resp.get('Vpcs'):
                    vpc = vpc_resp['Vpcs'][0]
                    vpc_name = next((t['Value'] for t in vpc.get('Tags', []) if t['Key'] == 'Name'), vpc_id)
                    self._add_node(vpc_id, 'VPC', vpc_name, vpc.get('State', 'available'), {"CidrBlock": vpc.get('CidrBlock')})
                    
                # 2. Fetch Subnet
                subnet_id = instance.get('SubnetId')
                if subnet_id:
                    sub_resp = self.ec2_client.describe_subnets(SubnetIds=[subnet_id])
                    if sub_resp.get('Subnets'):
                        sub = sub_resp['Subnets'][0]
                        sub_name = next((t['Value'] for t in sub.get('Tags', []) if t['Key'] == 'Name'), subnet_id)
                        self._add_node(subnet_id, 'SUBNET', sub_name, sub.get('State', 'available'), {
                            "CidrBlock": sub.get('CidrBlock'),
                            "AvailabilityZone": sub.get('AvailabilityZone')
                        })
                        
                        # Link VPC -> Subnet -> EC2
                        self._add_edge(vpc_id, subnet_id, 'CONTAINS')
                        self._add_edge(subnet_id, self.resource_id, 'CONTAINS')
                        
                # 3. Fetch Internet Gateways (IGW)
                igw_resp = self.ec2_client.describe_internet_gateways(
                    Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
                )
                for igw in igw_resp.get('InternetGateways', []):
                    igw_id = igw['InternetGatewayId']
                    igw_name = next((t['Value'] for t in igw.get('Tags', []) if t['Key'] == 'Name'), igw_id)
                    self._add_node(igw_id, 'IGW', igw_name, 'available')
                    self._add_edge(vpc_id, igw_id, 'ATTACHED_TO')
                    
                # 4. Fetch NAT Gateways
                nat_resp = self.ec2_client.describe_nat_gateways(
                    Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
                )
                for nat in nat_resp.get('NatGateways', []):
                    nat_id = nat['NatGatewayId']
                    nat_state = nat.get('State', 'available')
                    nat_name = next((t['Value'] for t in nat.get('Tags', []) if t['Key'] == 'Name'), nat_id)
                    nat_subnet = nat.get('SubnetId')
                    
                    self._add_node(nat_id, 'NAT', nat_name, nat_state)
                    # Link it to the subnet it resides in
                    if nat_subnet:
                        self._add_edge(nat_subnet, nat_id, 'ROUTES_TO')
                    else:
                        self._add_edge(vpc_id, nat_id, 'ROUTES_TO')
                        
            except Exception as e:
                logger.warning(f"Failed to trace Environment/Networking resources: {e}")

        return self.nodes, self.edges
