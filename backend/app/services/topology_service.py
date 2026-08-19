import boto3
import json
import os
import asyncio
from sqlalchemy import select
from app.services.aws.topology_builder import AWSTopologyBuilder
from app.schemas.topology.topology import TopologyScanRequest
from app.core.database import SessionLocal
from app.models.config.config_cloud_account import ConfigCloudAccount
from app.core.security import decrypt_credentials

class TopologyService:
    def __init__(self):
        pass

    async def _get_account(self, account_id: str = None):
        async with SessionLocal() as session:
            if account_id:
                result = await session.execute(
                    select(ConfigCloudAccount).where(ConfigCloudAccount.account_name == account_id)
                )
            else:
                result = await session.execute(
                    select(ConfigCloudAccount) # Fetch the first available account if none specified
                )
            return result.scalars().first()

    async def get_aws_session(self, account_id: str = None, region: str = 'ap-south-1') -> boto3.Session:
        try:
            account = await self._get_account(account_id)
            if not account:
                print(f"No database account configured! Falling back to env variables.")
                return boto3.Session(region_name=region)
                
            creds = decrypt_credentials(account.encrypted_credentials)
            print(f"Successfully retrieved credentials for DB account '{account.account_name}' in {region}.")
            return boto3.Session(
                aws_access_key_id=creds.get('aws_access_key_id'),
                aws_secret_access_key=creds.get('aws_secret_access_key'),
                aws_session_token=creds.get('aws_session_token'), # May be None, which is fine
                region_name=region
            )
        except Exception as e:
            print(f"Failed to fetch DB credentials: {e}. Falling back to env variables.")
            return boto3.Session(region_name=region)

    @staticmethod
    def _get_resource_id(resource, resource_type):
        import uuid
        if not isinstance(resource, dict): return str(resource)
        
        # 1. Exact common primary keys
        known_keys = [
            'Id', 'InstanceId', 'VpcId', 'SubnetId', 'GroupId', 'NetworkAclId',
            'DBInstanceIdentifier', 'DBClusterIdentifier', 'BucketName', 'RoleName', 
            'AllocationId', 'ClusterName', 'AutoScalingGroupName', 'InternetGatewayId',
            'RouteTableId', 'DhcpOptionsId', 'LoadBalancerArn', 'LoadBalancerName', 
            'TransitGatewayId', 'NatGatewayId', 'VpnGatewayId', 'VpnConnectionId', 
            'NetworkInterfaceId', 'FunctionName', 'DomainName', 'FileSystemId', 
            'VolumeId', 'SnapshotId', 'ImageId', 'KeyName', 'QueueUrl', 'TopicArn', 
            'ClusterId', 'EndpointId', 'RepositoryName', 'CacheClusterId', 'WorkspaceId', 'Name'
        ]
        
        for k in known_keys:
            if resource.get(k):
                return str(resource.get(k))
                
        # 2. Dynamic fallback: Look for any key ending in 'Id', 'Arn', or 'ARN'
        for k, v in resource.items():
            if isinstance(k, str) and (k.endswith('Id') or k.endswith('Arn') or k.endswith('ARN')) and v:
                return str(v)
                
        return f"unknown_{resource_type}_{uuid.uuid4().hex}"

    @staticmethod
    def _get_resource_name(resource):
        if not isinstance(resource, dict): return None
        if resource.get('Name'): return resource.get('Name')
        
        # Check Tags for a 'Name' tag
        tags = resource.get('Tags', [])
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, dict) and t.get('Key') == 'Name':
                    return t.get('Value')
                    
        # Check common name fields as a fallback
        name_keys = [
            'ClusterName', 'AutoScalingGroupName', 'FunctionName', 
            'DomainName', 'BucketName', 'RoleName', 'LoadBalancerName',
            'DBInstanceIdentifier', 'DBClusterIdentifier'
        ]
        for k in name_keys:
            if resource.get(k): return str(resource.get(k))
            
        return None

    async def scan_topology(self, request: TopologyScanRequest):
        from app.models.topology_resource import TopologyResource
        from sqlalchemy import text
        
        default_region = request.regions[0] if request.regions else 'ap-south-1'
        
        # 1. Resolve Account Configuration
        account_record = await self._get_account(request.account_id)
        if account_record:
            account_name = account_record.account_name
            cloud_provider = account_record.provider
            print(f"Running scan dynamically for account: {account_name}")
        else:
            account_name = request.account_id or "unknown-account"
            cloud_provider = "aws"
            print(f"Warning: No database account configured. Falling back to env variables for {account_name}.")
            
        session_aws = await self.get_aws_session(request.account_id, default_region)
        
        builder = AWSTopologyBuilder(session=session_aws, regions=request.regions)
        builder.build()
        topology_data = builder.get_topology()
        
        async with SessionLocal() as db_session:
            # Delete old scan data for this account and regions
            await db_session.execute(
                text("DELETE FROM topology_resources WHERE account_name = :acc"),
                {'acc': account_name}
            )
            
            resources_to_insert = []
            
            regions_data = topology_data.get("Regions", {})
            for region, vpcs in regions_data.items():
                for vpc in vpcs:
                    vpc_id = self._get_resource_id(vpc, 'VPC')
                    vpc_name = self._get_resource_name(vpc)
                    
                    vpc_record = TopologyResource(
                        resource_id=vpc_id, resource_name=vpc_name, resource_type='VPC',
                        cloud_provider=cloud_provider, account_name=account_name, region=region,
                        vpc_id=vpc_id, subnet_id=None, saved_config_json=json.dumps(vpc)
                    )
                    resources_to_insert.append(vpc_record)
                    
                    subnets = vpc.get('Subnets', [])
                    for subnet in subnets:
                        subnet_id = self._get_resource_id(subnet, 'Subnet')
                        subnet_name = self._get_resource_name(subnet)
                        
                        subnet_record = TopologyResource(
                            resource_id=subnet_id, resource_name=subnet_name, resource_type='Subnet',
                            cloud_provider=cloud_provider, account_name=account_name, region=region,
                            vpc_id=vpc_id, subnet_id=subnet_id, saved_config_json=json.dumps(subnet)
                        )
                        resources_to_insert.append(subnet_record)
                        
                        for key, val in subnet.items():
                            if isinstance(val, list) and key not in ['Tags']:
                                for res in val:
                                    res_id = self._get_resource_id(res, key)
                                    res_name = self._get_resource_name(res)
                                    res_record = TopologyResource(
                                        resource_id=res_id, resource_name=res_name, resource_type=key,
                                        cloud_provider=cloud_provider, account_name=account_name, region=region,
                                        vpc_id=vpc_id, subnet_id=subnet_id, saved_config_json=json.dumps(res)
                                    )
                                    resources_to_insert.append(res_record)
                                    
                    for key, val in vpc.items():
                        if isinstance(val, list) and key not in ['Tags', 'Subnets']:
                            for res in val:
                                res_id = self._get_resource_id(res, key)
                                res_name = self._get_resource_name(res)
                                res_record = TopologyResource(
                                    resource_id=res_id, resource_name=res_name, resource_type=key,
                                    cloud_provider=cloud_provider, account_name=account_name, region=region,
                                    vpc_id=vpc_id, subnet_id=None, saved_config_json=json.dumps(res)
                                )
                                resources_to_insert.append(res_record)
                                
            global_data = topology_data.get("GlobalResources", {})
            for res_type, resources in global_data.items():
                for res in resources:
                    res_id = self._get_resource_id(res, res_type)
                    res_name = self._get_resource_name(res)
                    res_record = TopologyResource(
                        resource_id=res_id, resource_name=res_name, resource_type=res_type,
                        cloud_provider=cloud_provider, account_name=account_name, region='global',
                        vpc_id=None, subnet_id=None, saved_config_json=json.dumps(res)
                    )
                    resources_to_insert.append(res_record)
                    
            db_session.add_all(resources_to_insert)
            await db_session.commit()
            
        return topology_data

    async def get_saved_topology(self, account_name: str = None):
        from app.models.topology_resource import TopologyResource
        
        # If no account specified, find the first available one dynamically
        if not account_name:
            account_record = await self._get_account()
            if account_record:
                account_name = account_record.account_name
            else:
                account_name = "unknown-account"
                
        async with SessionLocal() as session:
            result = await session.execute(
                select(TopologyResource).where(TopologyResource.account_name == account_name)
            )
            records = result.scalars().all()
            
        merged_regions = {}
        merged_global = {}
        
        vpcs_map = {}
        subnets_map = {}
        
        # Pass 1: Setup VPCs, Subnets, and Globals
        for record in records:
            data = json.loads(record.saved_config_json)
            if record.region == 'global':
                merged_global.setdefault(record.resource_type, []).append(data)
            elif record.resource_type == 'VPC':
                # Strip out existing nested arrays so we don't duplicate them during Pass 2
                for k in list(data.keys()):
                    if isinstance(data[k], list) and k != 'Tags':
                        data[k] = []
                data.setdefault('Subnets', [])
                vpcs_map[record.resource_id] = data
                merged_regions.setdefault(record.region, []).append(data)
            elif record.resource_type == 'Subnet':
                for k in list(data.keys()):
                    if isinstance(data[k], list) and k != 'Tags':
                        data[k] = []
                subnets_map[record.resource_id] = data
                
        # Pass 2: Connect the topology using relational DB columns
        for record in records:
            if record.region == 'global' or record.resource_type == 'VPC':
                continue
                
            data = json.loads(record.saved_config_json)
            
            if record.resource_type == 'Subnet':
                if record.vpc_id in vpcs_map:
                    vpcs_map[record.vpc_id]['Subnets'].append(data)
            else:
                if record.subnet_id and record.subnet_id in subnets_map:
                    subnets_map[record.subnet_id].setdefault(record.resource_type, []).append(data)
                elif record.vpc_id and record.vpc_id in vpcs_map:
                    vpcs_map[record.vpc_id].setdefault(record.resource_type, []).append(data)
                    
        return {
            "Regions": merged_regions,
            "GlobalResources": merged_global
        }


