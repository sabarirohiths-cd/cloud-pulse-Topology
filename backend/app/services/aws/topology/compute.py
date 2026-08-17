from .base import BaseTopologyBuilder

class ComputeMixin(BaseTopologyBuilder):
    def _fetch_ec2(self):
        print("Fetching EC2...")

        try:
            instances_resp = self.ec2.describe_instances()
            for reservation in instances_resp.get('Reservations', []):
                for inst in reservation.get('Instances', []):
                    sg_ids = [isg['GroupId'] for isg in inst.get('SecurityGroups', [])]
                    self.raw_data['Instances'].append({
                        'SubnetId': inst.get('SubnetId'),
                        'InstanceId': inst.get('InstanceId'),
                        'InstanceType': inst.get('InstanceType'),
                        'State': inst.get('State', {}).get('Name'),
                        'PrivateIpAddress': inst.get('PrivateIpAddress'),
                        'PublicIpAddress': inst.get('PublicIpAddress'),
                        'SecurityGroupIds': sg_ids,
                        'Name': self._safe_get_tag(inst.get('Tags', []), 'Name')
                    })
        except Exception:
            pass

    def _fetch_asg_ebs(self):
        print("Fetching ASG and EBS...")
        try:
            asg_resp = self.asg.describe_auto_scaling_groups()
            for asg in asg_resp.get('AutoScalingGroups', []):
                sids = []
                vpc_zone_id = asg.get('VPCZoneIdentifier', '')
                if vpc_zone_id:
                    for sid in vpc_zone_id.split(','):
                        sids.append(sid.strip())
                
                inst_ids = [inst.get('InstanceId') for inst in asg.get('Instances', [])]
                
                self.raw_data['AutoScalingGroups'].append({
                    'SubnetIds': sids,
                    'InstanceIds': inst_ids,
                    'AutoScalingGroupName': asg.get('AutoScalingGroupName'),
                    'MinSize': asg.get('MinSize'),
                    'MaxSize': asg.get('MaxSize'),
                    'DesiredCapacity': asg.get('DesiredCapacity')
                })
        except Exception:
            pass



        try:
            volumes_resp = self.ec2.describe_volumes()
            for vol in volumes_resp.get('Volumes', []):
                for att in vol.get('Attachments', []):
                    self.raw_data['EbsVolumes'].append({
                        'InstanceId': att.get('InstanceId'),
                        'VolumeId': vol.get('VolumeId'),
                        'Size': vol.get('Size'),
                        'State': vol.get('State')
                    })
        except Exception:
            pass

    def _fetch_eks_ecs(self):
        print("Fetching EKS and ECS Clusters...")
        try:
            eks_list = self.eks.list_clusters().get('clusters', [])
            for cluster_name in eks_list:
                c_detail = self.eks.describe_cluster(name=cluster_name).get('cluster', {})
                self.raw_data['EKSClusters'].append({
                    'SubnetIds': c_detail.get('resourcesVpcConfig', {}).get('subnetIds', []),
                    'ClusterName': c_detail.get('name'),
                    'Status': c_detail.get('status'),
                    'Endpoint': c_detail.get('endpoint')
                })
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
                        'ServiceTypes': [],
                        'SubnetIds': []
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
                        ecs_info['SubnetIds'] = list(cluster_subnets)
                    self.raw_data['ECSClusters'].append(ecs_info)
        except Exception:
            pass

    def _fetch_lambda(self):
        print("Fetching Lambda Functions...")
        try:
            lambda_resp = self.lmbda.list_functions()
            for func in lambda_resp.get('Functions', []):
                self.raw_data['LambdaFunctions'].append({
                    'SubnetIds': func.get('VpcConfig', {}).get('SubnetIds', []),
                    'FunctionName': func.get('FunctionName'),
                    'Runtime': func.get('Runtime')
                })
        except Exception:
            pass

    def _fetch_sagemaker(self):
        print("Fetching SageMaker...")
        try:
            sm_resp = self.sagemaker.list_notebook_instances()
            for nb in sm_resp.get('NotebookInstances', []):
                name = nb.get('NotebookInstanceName')
                nb_det = self.sagemaker.describe_notebook_instance(NotebookInstanceName=name)
                self.raw_data['SageMakerNotebooks'].append({
                    'SubnetId': nb_det.get('SubnetId'),
                    'NotebookInstanceName': name,
                    'NotebookInstanceStatus': nb_det.get('NotebookInstanceStatus'),
                    'InstanceType': nb_det.get('InstanceType')
                })
        except Exception:
            pass

    def _fetch_workspaces(self):
        print("Fetching WorkSpaces...")
        try:
            ws_resp = self.workspaces.describe_workspaces()
            for ws in ws_resp.get('Workspaces', []):
                self.raw_data['WorkSpaces'].append({
                    'SubnetId': ws.get('SubnetId'),
                    'WorkspaceId': ws.get('WorkspaceId'),
                    'State': ws.get('State'),
                    'UserName': ws.get('UserName'),
                    'BundleId': ws.get('BundleId')
                })
        except Exception:
            pass

    def _fetch_app_runner_vpc_connectors(self):
        print("Fetching App Runner VPC Connectors...")
        try:
            ar_resp = self.apprunner.list_vpc_connectors()
            for vpc_conn in ar_resp.get('VpcConnectors', []):
                arn = vpc_conn.get('VpcConnectorArn')
                conn_det = self.apprunner.describe_vpc_connector(VpcConnectorArn=arn).get('VpcConnector', {})
                self.raw_data['AppRunnerVpcConnectors'].append({
                    'SubnetIds': conn_det.get('Subnets', []),
                    'VpcConnectorName': conn_det.get('VpcConnectorName'),
                    'VpcConnectorArn': conn_det.get('VpcConnectorArn'),
                    'Status': conn_det.get('Status')
                })
        except Exception:
            pass

    def _fetch_emr(self):
        print("Fetching EMR Clusters...")
        try:
            emr_resp = self.emr.list_clusters(ClusterStates=['STARTING', 'BOOTSTRAPPING', 'RUNNING', 'WAITING', 'TERMINATING'])
            for cluster in emr_resp.get('Clusters', []):
                c_id = cluster.get('Id')
                c_det = self.emr.describe_cluster(ClusterId=c_id).get('Cluster', {})
                ec2_attr = c_det.get('Ec2InstanceAttributes', {})
                sids = []
                sid = ec2_attr.get('Ec2SubnetId')
                if sid:
                    sids.append(sid)
                for rsid in ec2_attr.get('RequestedEc2SubnetIds', []):
                    if rsid not in sids:
                        sids.append(rsid)
                self.raw_data['EMRClusters'].append({
                    'SubnetIds': sids,
                    'Id': c_id,
                    'Name': c_det.get('Name'),
                    'State': c_det.get('Status', {}).get('State')
                })
        except Exception:
            pass

    def _fetch_glue_connections(self):
        print("Fetching Glue Connections...")
        try:
            glue_resp = self.glue.get_connections()
            for conn in glue_resp.get('ConnectionList', []):
                reqs = conn.get('PhysicalConnectionRequirements', {})
                sid = reqs.get('SubnetId')
                if sid:
                    self.raw_data['GlueConnections'].append({
                        'SubnetId': sid,
                        'Name': conn.get('Name'),
                        'ConnectionType': conn.get('ConnectionType'),
                        'SecurityGroupIdList': reqs.get('SecurityGroupIdList', [])
                    })
        except Exception:
            pass

    def _fetch_batch(self):
        print("Fetching AWS Batch...")
        try:
            batch_resp = self.batch.describe_compute_environments()
            for env in batch_resp.get('computeEnvironments', []):
                resources = env.get('computeResources', {})
                subnets = resources.get('subnets', [])
                if subnets:
                    self.raw_data['BatchComputeEnvironments'].append({
                        'SubnetIds': subnets,
                        'ComputeEnvironmentName': env.get('computeEnvironmentName'),
                        'State': env.get('state'),
                        'Status': env.get('status'),
                        'Type': resources.get('type')
                    })
        except Exception:
            pass
