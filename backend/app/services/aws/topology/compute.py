from .base import BaseTopologyBuilder

class ComputeMixin(BaseTopologyBuilder):
    def _fetch_ec2_and_sg(self):
        print("Fetching EC2 and Security Groups...")
        subnet_map = self._get_subnet_map()
        sg_map = {}
        try:
            sg_resp = self.ec2.describe_security_groups()
            for sg in sg_resp.get('SecurityGroups', []):
                sg_map[sg['GroupId']] = {
                    'GroupId': sg['GroupId'],
                    'GroupName': sg['GroupName'],
                    'Description': sg.get('Description'),
                    'InboundRules': sg.get('IpPermissions', []),
                    'OutboundRules': sg.get('IpPermissionsEgress', [])
                }
        except Exception:
            pass

        try:
            instances_resp = self.ec2.describe_instances()
            for reservation in instances_resp.get('Reservations', []):
                for inst in reservation.get('Instances', []):
                    sub_id = inst.get('SubnetId')
                    if sub_id in subnet_map:
                        inst_sgs = []
                        for isg in inst.get('SecurityGroups', []):
                            if isg['GroupId'] in sg_map:
                                inst_sgs.append(sg_map[isg['GroupId']])
                        
                        subnet_map[sub_id]['Instances'].append({
                            'InstanceId': inst.get('InstanceId'),
                            'InstanceType': inst.get('InstanceType'),
                            'State': inst.get('State', {}).get('Name'),
                            'PrivateIpAddress': inst.get('PrivateIpAddress'),
                            'PublicIpAddress': inst.get('PublicIpAddress'),
                            'SecurityGroups': inst_sgs,
                            'Name': self._safe_get_tag(inst.get('Tags', []), 'Name'),
                            'AutoScalingGroupName': None,
                            'ElasticIps': [],
                            'EbsVolumes': []
                        })
        except Exception:
            pass

    def _fetch_asg_eip_ebs(self):
        print("Fetching ASG, EIP, EBS...")
        subnet_map = self._get_subnet_map()
        instance_map = {}
        for sub in subnet_map.values():
            for inst in sub.get('Instances', []):
                instance_map[inst['InstanceId']] = inst

        try:
            asg_resp = self.asg.describe_auto_scaling_groups()
            for asg in asg_resp.get('AutoScalingGroups', []):
                asg_info = {
                    'AutoScalingGroupName': asg.get('AutoScalingGroupName'),
                    'MinSize': asg.get('MinSize'),
                    'MaxSize': asg.get('MaxSize'),
                    'DesiredCapacity': asg.get('DesiredCapacity')
                }
                vpc_zone_id = asg.get('VPCZoneIdentifier', '')
                if vpc_zone_id:
                    for sid in vpc_zone_id.split(','):
                        sid = sid.strip()
                        if sid in subnet_map:
                            subnet_map[sid]['AutoScalingGroups'].append(asg_info)
                for inst in asg.get('Instances', []):
                    inst_id = inst.get('InstanceId')
                    if inst_id in instance_map:
                        instance_map[inst_id]['AutoScalingGroupName'] = asg.get('AutoScalingGroupName')
        except Exception:
            pass

        try:
            addresses_resp = self.ec2.describe_addresses()
            for addr in addresses_resp.get('Addresses', []):
                inst_id = addr.get('InstanceId')
                if inst_id and inst_id in instance_map:
                    instance_map[inst_id]['ElasticIps'].append({
                        'PublicIp': addr.get('PublicIp')
                    })
        except Exception:
            pass

        try:
            volumes_resp = self.ec2.describe_volumes()
            for vol in volumes_resp.get('Volumes', []):
                vol_info = {
                    'VolumeId': vol.get('VolumeId'),
                    'Size': vol.get('Size'),
                    'State': vol.get('State')
                }
                for att in vol.get('Attachments', []):
                    inst_id = att.get('InstanceId')
                    if inst_id in instance_map:
                        instance_map[inst_id]['EbsVolumes'].append(vol_info)
        except Exception:
            pass

    def _fetch_eks_ecs(self):
        print("Fetching EKS and ECS Clusters...")
        subnet_map = self._get_subnet_map()
        try:
            eks_list = self.eks.list_clusters().get('clusters', [])
            for cluster_name in eks_list:
                c_detail = self.eks.describe_cluster(name=cluster_name).get('cluster', {})
                subnets = c_detail.get('resourcesVpcConfig', {}).get('subnetIds', [])
                eks_info = {
                    'ClusterName': c_detail.get('name'),
                    'Status': c_detail.get('status'),
                    'Endpoint': c_detail.get('endpoint')
                }
                for sid in subnets:
                    if sid in subnet_map:
                        subnet_map[sid]['EKSClusters'].append(eks_info)
        except Exception:
            pass

        try:
            ecs_list = self.ecs.list_clusters().get('clusterArns', [])
            if ecs_list:
                clusters = self.ecs.describe_clusters(clusters=ecs_list).get('clusters', [])
                for cluster in clusters:
                    c_name = cluster.get('clusterName')
                    ecs_info = {
                        'ClusterName': c_name,
                        'Status': cluster.get('status'),
                        'Services': 0,
                        'Tasks': cluster.get('runningTasksCount', 0),
                        'ServiceTypes': []
                    }
                    services_list = self.ecs.list_services(cluster=c_name).get('serviceArns', [])
                    ecs_info['Services'] = len(services_list)
                    if services_list:
                        services = self.ecs.describe_services(cluster=c_name, services=services_list).get('services', [])
                        cluster_subnets = set()
                        for s in services:
                            ecs_info['ServiceTypes'].append({
                                'ServiceName': s.get('serviceName'),
                                'Status': s.get('status'),
                                'DesiredCount': s.get('desiredCount'),
                                'RunningCount': s.get('runningCount'),
                                'LaunchType': s.get('launchType', 'UNKNOWN')
                            })
                            vpc_conf = s.get('networkConfiguration', {}).get('awsvpcConfiguration', {})
                            cluster_subnets.update(vpc_conf.get('subnets', []))
                        for sid in cluster_subnets:
                            if sid in subnet_map:
                                subnet_map[sid]['ECSClusters'].append(ecs_info)
        except Exception:
            pass

    def _fetch_lambda(self):
        print("Fetching Lambda Functions...")
        subnet_map = self._get_subnet_map()
        try:
            lambda_resp = self.lmbda.list_functions()
            for func in lambda_resp.get('Functions', []):
                subnet_ids = func.get('VpcConfig', {}).get('SubnetIds', [])
                for sid in subnet_ids:
                    if sid in subnet_map:
                        subnet_map[sid]['LambdaFunctions'].append({
                            'FunctionName': func.get('FunctionName'),
                            'Runtime': func.get('Runtime')
                        })
        except Exception:
            pass

    def _fetch_sagemaker(self):
        print("Fetching SageMaker...")
        subnet_map = self._get_subnet_map()
        try:
            sm_resp = self.sagemaker.list_notebook_instances()
            for nb in sm_resp.get('NotebookInstances', []):
                name = nb.get('NotebookInstanceName')
                nb_det = self.sagemaker.describe_notebook_instance(NotebookInstanceName=name)
                sid = nb_det.get('SubnetId')
                if sid in subnet_map:
                    subnet_map[sid]['SageMakerNotebooks'].append({
                        'NotebookInstanceName': name,
                        'NotebookInstanceStatus': nb_det.get('NotebookInstanceStatus'),
                        'InstanceType': nb_det.get('InstanceType')
                    })
        except Exception:
            pass

    def _fetch_workspaces(self):
        print("Fetching WorkSpaces...")
        subnet_map = self._get_subnet_map()
        try:
            ws_resp = self.workspaces.describe_workspaces()
            for ws in ws_resp.get('Workspaces', []):
                sid = ws.get('SubnetId')
                if sid in subnet_map:
                    subnet_map[sid]['WorkSpaces'].append({
                        'WorkspaceId': ws.get('WorkspaceId'),
                        'State': ws.get('State'),
                        'UserName': ws.get('UserName'),
                        'BundleId': ws.get('BundleId')
                    })
        except Exception:
            pass
