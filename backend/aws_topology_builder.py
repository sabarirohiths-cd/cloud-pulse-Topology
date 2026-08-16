import boto3
import json
import os
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

class AWSTopologyBuilder:
    def __init__(self, region='ap-south-1'):
        self.region = region
        self.vpcs = {}
        
        print(f"Initializing AWS Clients for region {self.region}...")
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.elbv2 = boto3.client('elbv2', region_name=self.region)
        self.rds = boto3.client('rds', region_name=self.region)
        self.eks = boto3.client('eks', region_name=self.region)
        self.ecs = boto3.client('ecs', region_name=self.region)
        self.lmbda = boto3.client('lambda', region_name=self.region)
        self.elasticache = boto3.client('elasticache', region_name=self.region)
        self.efs = boto3.client('efs', region_name=self.region)
        self.asg = boto3.client('autoscaling', region_name=self.region)
        self.mq = boto3.client('mq', region_name=self.region)
        self.kafka = boto3.client('kafka', region_name=self.region)
        self.sqs = boto3.client('sqs', region_name=self.region)
        self.docdb = boto3.client('docdb', region_name=self.region)
        self.redshift = boto3.client('redshift', region_name=self.region)
        self.sagemaker = boto3.client('sagemaker', region_name=self.region)
        self.workspaces = boto3.client('workspaces', region_name=self.region)

    def _safe_get_tag(self, tags, key):
        if tags:
            for tag in tags:
                if tag.get('Key') == key:
                    return tag.get('Value')
        return None

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
                    'RegionalQueues': []
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
                        'WorkSpaces': []
                    })
        except Exception as e:
            print(f"Error fetching Subnets: {e}")

    def _get_subnet_map(self):
        subnet_map = {}
        for vpc in self.vpcs.values():
            for sub in vpc.get('Subnets', []):
                subnet_map[sub['SubnetId']] = sub
        return subnet_map

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
        except Exception as e:
            print(f"Warning: Failed to fetch Security Groups: {e}")

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
        except Exception as e:
            print(f"Warning: Failed to fetch EC2 instances: {e}")

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
        except Exception as e:
            print(f"Warning: Failed to fetch Route Tables: {e}")

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
        except Exception as e:
            print(f"Warning: Failed to fetch NAT Gateways: {e}")

    def _fetch_elb_rds(self):
        print("Fetching Load Balancers and RDS...")
        subnet_map = self._get_subnet_map()
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
        except Exception as e:
            print(f"Warning: Failed to fetch Load Balancers: {e}")

        try:
            rds_resp = self.rds.describe_db_instances()
            for db in rds_resp.get('DBInstances', []):
                sub_group = db.get('DBSubnetGroup', {})
                vpc_id = sub_group.get('VpcId')
                if vpc_id in self.vpcs:
                    self.vpcs[vpc_id]['RDSInstances'].append({
                        'DBInstanceIdentifier': db.get('DBInstanceIdentifier'),
                        'Engine': db.get('Engine'),
                        'DBInstanceStatus': db.get('DBInstanceStatus'),
                        'Endpoint': db.get('Endpoint', {}).get('Address')
                    })
        except Exception as e:
            print(f"Warning: Failed to fetch RDS: {e}")

    def _fetch_eks_ecs(self):
        print("Fetching EKS and ECS Clusters...")
        subnet_map = self._get_subnet_map()
        try:
            eks_list = self.eks.list_clusters().get('clusters', [])
            for cluster_name in eks_list:
                c_detail = self.eks.describe_cluster(name=cluster_name).get('cluster', {})
                subnets = c_detail.get('resourcesVpcConfig', {}).get('subnetIds', [])
                vpc_id = c_detail.get('resourcesVpcConfig', {}).get('vpcId')
                eks_info = {
                    'ClusterName': c_detail.get('name'),
                    'Status': c_detail.get('status'),
                    'Endpoint': c_detail.get('endpoint')
                }
                for sid in subnets:
                    if sid in subnet_map:
                        subnet_map[sid]['EKSClusters'].append(eks_info)
        except Exception as e:
            print(f"Warning: Failed to fetch EKS: {e}")

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
                            ecs_info['ServiceTypes'].append(s.get('serviceName'))
                            vpc_conf = s.get('networkConfiguration', {}).get('awsvpcConfiguration', {})
                            cluster_subnets.update(vpc_conf.get('subnets', []))
                            
                        for sid in cluster_subnets:
                            if sid in subnet_map:
                                subnet_map[sid]['ECSClusters'].append(ecs_info)
        except Exception as e:
            print(f"Warning: Failed to fetch ECS: {e}")

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
        except Exception as e:
            print(f"Warning: Failed to fetch VPC Endpoints: {e}")

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
        except Exception as e:
            print(f"Warning: Failed to fetch VPC Peering: {e}")

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
        except Exception as e:
            print(f"Warning: Failed to fetch NACLs: {e}")

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
        except Exception as e:
            print(f"Warning: Failed to fetch TGW Attachments: {e}")

    def _fetch_serverless_storage(self):
        print("Fetching Lambda, ElastiCache, EFS...")
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
        except Exception as e:
            print(f"Warning: Failed to fetch Lambda: {e}")

        try:
            cache_clusters = self.elasticache.describe_cache_clusters().get('CacheClusters', [])
            for cluster in cache_clusters:
                subnet_group = cluster.get('CacheSubnetGroupName')
                if subnet_group:
                    try:
                        g_info = self.elasticache.describe_cache_subnet_groups(CacheSubnetGroupName=subnet_group)
                        subnets = g_info.get('CacheSubnetGroups', [{}])[0].get('Subnets', [])
                        c_info = {
                            'CacheClusterId': cluster.get('CacheClusterId'),
                            'Engine': cluster.get('Engine'),
                            'CacheNodeType': cluster.get('CacheNodeType')
                        }
                        for sn in subnets:
                            sid = sn.get('SubnetIdentifier')
                            if sid in subnet_map:
                                subnet_map[sid]['ElastiCacheNodes'].append(c_info)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Warning: Failed to fetch ElastiCache: {e}")

        try:
            filesystems = self.efs.describe_file_systems().get('FileSystems', [])
            for fs in filesystems:
                fs_id = fs.get('FileSystemId')
                mts = self.efs.describe_mount_targets(FileSystemId=fs_id).get('MountTargets', [])
                for mt in mts:
                    sid = mt.get('SubnetId')
                    if sid in subnet_map:
                        subnet_map[sid]['EFSMountTargets'].append({
                            'FileSystemId': fs_id,
                            'MountTargetId': mt.get('MountTargetId'),
                            'IpAddress': mt.get('IpAddress')
                        })
        except Exception as e:
            print(f"Warning: Failed to fetch EFS: {e}")

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
        except Exception as e:
            print(f"Warning: Failed to fetch ASGs: {e}")

        try:
            addresses_resp = self.ec2.describe_addresses()
            for addr in addresses_resp.get('Addresses', []):
                inst_id = addr.get('InstanceId')
                if inst_id and inst_id in instance_map:
                    instance_map[inst_id]['ElasticIps'].append({
                        'PublicIp': addr.get('PublicIp')
                    })
        except Exception as e:
            print(f"Warning: Failed to fetch EIPs: {e}")

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
        except Exception as e:
            print(f"Warning: Failed to fetch EBS: {e}")

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
        except Exception as e:
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
        except Exception as e:
            pass

        try:
            eni_resp = self.ec2.describe_network_interfaces()
            for eni in eni_resp.get('NetworkInterfaces', []):
                sid = eni.get('SubnetId')
                if sid not in subnet_map:
                    continue
                
                type_ = eni.get('InterfaceType')
                desc = eni.get('Description', '').lower()
                
                if eni.get('Attachment', {}).get('InstanceId') or type_ in ['nat_gateway', 'vpc_endpoint', 'transit_gateway']:
                    continue
                if any(k in desc for k in ['elb', 'rds', 'lambda', 'efs', 'eks', 'ecs', 'autoscaling']):
                    continue
                    
                subnet_map[sid]['UnclassifiedENIs'].append({
                    'NetworkInterfaceId': eni.get('NetworkInterfaceId'),
                    'PrivateIpAddress': eni.get('PrivateIpAddress'),
                    'InterfaceType': type_,
                    'Description': eni.get('Description')
                })
        except Exception as e:
            pass

    def _fetch_messaging_queues(self):
        print("Fetching SQS, MQ, MSK...")
        subnet_map = self._get_subnet_map()
        
        try:
            sqs_resp = self.sqs.list_queues()
            for q in sqs_resp.get('QueueUrls', []):
                for vpc in self.vpcs.values():
                    vpc['RegionalQueues'].append({'QueueUrl': q})
        except Exception:
            pass

        try:
            mq_resp = self.mq.list_brokers()
            for broker in mq_resp.get('BrokerSummaries', []):
                b_id = broker.get('BrokerId')
                b_det = self.mq.describe_broker(BrokerId=b_id)
                info = {
                    'BrokerName': b_det.get('BrokerName'),
                    'BrokerState': b_det.get('BrokerState'),
                    'EngineType': b_det.get('EngineType')
                }
                for sid in b_det.get('SubnetIds', []):
                    if sid in subnet_map:
                        subnet_map[sid]['AmazonMQBrokers'].append(info)
        except Exception:
            pass

        try:
            kafka_resp = self.kafka.list_clusters_v2()
            for cluster in kafka_resp.get('ClusterInfoList', []):
                info = {
                    'ClusterName': cluster.get('ClusterName'),
                    'State': cluster.get('State'),
                    'ClusterType': cluster.get('ClusterType')
                }
                subnets = []
                if 'Provisioned' in cluster:
                    subnets = cluster['Provisioned'].get('BrokerNodeGroupInfo', {}).get('ClientSubnets', [])
                elif 'Serverless' in cluster:
                    for vc in cluster['Serverless'].get('VpcConfigs', []):
                        subnets.extend(vc.get('SubnetIds', []))
                for sid in subnets:
                    if sid in subnet_map:
                        subnet_map[sid]['MSKClusters'].append(info)
        except Exception:
            pass

    def _fetch_documentdb(self):
        print("Fetching DocumentDB...")
        subnet_map = self._get_subnet_map()
        try:
            docdb_resp = self.docdb.describe_db_clusters()
            for cluster in docdb_resp.get('DBClusters', []):
                subnet_group = cluster.get('DBSubnetGroup')
                info = {
                    'DBClusterIdentifier': cluster.get('DBClusterIdentifier'),
                    'Engine': cluster.get('Engine'),
                    'Status': cluster.get('Status')
                }
                if subnet_group:
                    try:
                        g_info = self.docdb.describe_db_subnet_groups(DBSubnetGroupName=subnet_group)
                        subnets = g_info.get('DBSubnetGroups', [{}])[0].get('Subnets', [])
                        for sn in subnets:
                            sid = sn.get('SubnetIdentifier')
                            if sid in subnet_map:
                                subnet_map[sid]['DocumentDBClusters'].append(info)
                    except Exception:
                        pass
        except Exception:
            pass

    def _fetch_redshift(self):
        print("Fetching Redshift...")
        subnet_map = self._get_subnet_map()
        try:
            rs_resp = self.redshift.describe_clusters()
            for cluster in rs_resp.get('Clusters', []):
                subnet_group_name = cluster.get('ClusterSubnetGroupName')
                info = {
                    'ClusterIdentifier': cluster.get('ClusterIdentifier'),
                    'NodeType': cluster.get('NodeType'),
                    'ClusterStatus': cluster.get('ClusterStatus')
                }
                if subnet_group_name:
                    try:
                        g_info = self.redshift.describe_cluster_subnet_groups(ClusterSubnetGroupName=subnet_group_name)
                        subnets = g_info.get('ClusterSubnetGroups', [{}])[0].get('Subnets', [])
                        for sn in subnets:
                            sid = sn.get('SubnetIdentifier')
                            if sid in subnet_map:
                                subnet_map[sid]['RedshiftClusters'].append(info)
                    except Exception:
                        pass
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

    def build(self):
        print("Starting AWSTopologyBuilder Process...")
        
        # 1. Fetch synchronous skeleton
        self._fetch_vpcs_and_subnets()
        
        if not self.vpcs:
            print("No VPCs found. Exiting.")
            return

        # 2. Run workers in parallel
        worker_methods = [
            self._fetch_ec2_and_sg,
            self._fetch_routes_nat,
            self._fetch_elb_rds,
            self._fetch_eks_ecs,
            self._fetch_endpoints_peering,
            self._fetch_tgw_nacl,
            self._fetch_serverless_storage,
            self._fetch_asg_eip_ebs,
            self._fetch_vgw_vpn_eni,
            self._fetch_messaging_queues,
            self._fetch_documentdb,
            self._fetch_redshift,
            self._fetch_sagemaker,
            self._fetch_workspaces
        ]
        
        print("Spawning worker threads for concurrent fetching...")
        with ThreadPoolExecutor(max_workers=len(worker_methods)) as executor:
            for method in worker_methods:
                executor.submit(method)

        print("Topology fully assembled!")

    def save_output(self, output_dir='output', filename='final_complete_topology.json'):
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, filename)
        with open(path, 'w') as f:
            json.dump(list(self.vpcs.values()), f, indent=4)
        print(f"Topology JSON exported to {path}")

    def print_summary(self):
        print("\n=== AWS Topology Summary ===")
        total_vpcs = len(self.vpcs)
        total_subnets = 0
        total_ec2 = 0
        total_rds = 0
        total_lambdas = 0
        total_docdb = 0
        total_redshift = 0
        total_sagemaker = 0
        total_workspaces = 0
        
        for vpc in self.vpcs.values():
            total_subnets += len(vpc.get('Subnets', []))
            total_rds += len(vpc.get('RDSInstances', []))
            for sub in vpc.get('Subnets', []):
                total_ec2 += len(sub.get('Instances', []))
                total_lambdas += len(sub.get('LambdaFunctions', []))
                total_docdb += len(sub.get('DocumentDBClusters', []))
                total_redshift += len(sub.get('RedshiftClusters', []))
                total_sagemaker += len(sub.get('SageMakerNotebooks', []))
                total_workspaces += len(sub.get('WorkSpaces', []))
                
        print(f"VPCs Found: {total_vpcs}")
        print(f"Subnets Found: {total_subnets}")
        print(f"EC2 Instances Found: {total_ec2}")
        print(f"RDS Instances Found: {total_rds}")
        print(f"Lambda Functions Found: {total_lambdas}")
        print(f"DocumentDB Clusters Found: {total_docdb}")
        print(f"Redshift Clusters Found: {total_redshift}")
        print(f"SageMaker Notebooks Found: {total_sagemaker}")
        print(f"WorkSpaces Found: {total_workspaces}")
        print("============================\n")

if __name__ == "__main__":
    builder = AWSTopologyBuilder()
    builder.build()
    builder.print_summary()
    builder.save_output()
