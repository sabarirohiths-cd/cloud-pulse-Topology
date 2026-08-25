import boto3
import json
import asyncio
from app.services.aws.topology.core.flow_builder import ComputeFlowBuilder
from app.schemas.topology.topology import ComputeFlowRequest
from app.core.database import SessionLocal
from app.models.config.config_cloud_account import ConfigCloudAccount
from app.core.security import decrypt_credentials
from sqlalchemy import select

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
                    select(ConfigCloudAccount)
                )
            return result.scalars().first()

    async def get_aws_session(self, account_id: str = None, region: str = 'ap-south-1') -> boto3.Session:
        try:
            account = await self._get_account(account_id)
            if not account:
                print(f"No database account configured! Falling back to env variables.")
                return boto3.Session(region_name=region)
                
            creds = decrypt_credentials(account.encrypted_credentials)
            return boto3.Session(
                aws_access_key_id=creds.get('aws_access_key_id'),
                aws_secret_access_key=creds.get('aws_secret_access_key'),
                aws_session_token=creds.get('aws_session_token'),
                region_name=region
            )
        except Exception as e:
            print(f"Failed to fetch DB credentials: {e}. Falling back to env variables.")
            return boto3.Session(region_name=region)

    async def scan_compute_flow(self, request: ComputeFlowRequest):
        print(f"\n[DEEP FETCH] 🔍 Deep Tracing {request.compute_type} {request.resource_id} in {request.region}...\n")
        
        session_aws = await self.get_aws_session(request.account_id, request.region)
        
        builder = ComputeFlowBuilder(
            session=session_aws,
            region=request.region,
            compute_type=request.compute_type,
            resource_id=request.resource_id
        )
        
        loop = asyncio.get_event_loop()
        flow_data = await loop.run_in_executor(None, builder.build)
        
        # Save to JSON file for easy debugging/inspection
        import os
        os.makedirs("data", exist_ok=True)
        filename = "data/last_compute_flow.json"
        
        try:
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    try:
                        existing_data = json.load(f)
                    except:
                        existing_data = {}
                
                # Merge nodes and edges (avoid duplicates by ID)
                existing_nodes = {n['id']: n for n in existing_data.get('nodes', []) if 'id' in n}
                for n in flow_data.get('nodes', []):
                    if n['id'] in existing_nodes:
                        old_meta = existing_nodes[n['id']].get('metadata', {})
                        new_meta = n.get('metadata', {})
                        # Preserve keys that are in old_meta but not in new_meta
                        for k, v in old_meta.items():
                            if k not in new_meta:
                                new_meta[k] = v
                        n['metadata'] = new_meta
                    existing_nodes[n['id']] = n
                    
                existing_edges = {(e.get('source'), e.get('target')): e for e in existing_data.get('edges', [])}
                for e in flow_data.get('edges', []):
                    existing_edges[(e.get('source'), e.get('target'))] = e
                    
                existing_data['nodes'] = list(existing_nodes.values())
                existing_data['edges'] = list(existing_edges.values())
                existing_data['last_compute_id'] = flow_data.get('compute_id')
                
                # Remove old duplicated data if it exists
                existing_data.pop('last_trace', None)
                existing_data.pop('traces', None)
                existing_data.pop('compute_id', None)
            else:
                existing_data = {
                    "last_compute_id": flow_data.get('compute_id'),
                    "nodes": flow_data.get('nodes', []),
                    "edges": flow_data.get('edges', [])
                }
            
            with open(filename, "w") as f:
                json.dump(existing_data, f, indent=4)
        except Exception as e:
            print(f"Warning: Failed to save flow to JSON: {e}")
            
        return flow_data

    async def list_compute_resources(self, account_id: str, region: str, compute_type: str):
        print(f"\n[GLOBAL FETCH] 🚀 Scanning {compute_type} resources in {region} for account {account_id}...\n")
        session_aws = await self.get_aws_session(account_id, region)
        compute_type_upper = compute_type.upper()
        
        resources = []
        
        if compute_type_upper == 'EC2':
            client = session_aws.client('ec2', region_name=region)
            paginator = client.get_paginator('describe_instances')
            for page in paginator.paginate():
                for res in page.get('Reservations', []):
                    for inst in res.get('Instances', []):
                        name = next((t['Value'] for t in inst.get('Tags', []) if t['Key'] == 'Name'), None)
                        resources.append({
                            "id": inst['InstanceId'],
                            "name": name,
                            "type": "EC2",
                            "state": inst.get('State', {}).get('Name', 'unknown'),
                            "region": region
                        })
        else:
            raise NotImplementedError(f"Listing for {compute_type} is not yet implemented.")
            
        # Update JSON file with the fetched resources as nodes
        import os
        os.makedirs("data", exist_ok=True)
        filename = "data/last_compute_flow.json"
        
        try:
            existing_data = {"nodes": [], "edges": []}
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        pass
            
            existing_nodes = {n.get('id'): n for n in existing_data.get('nodes', []) if 'id' in n}
            for res in resources:
                if res['id'] not in existing_nodes:
                    existing_nodes[res['id']] = {
                        "id": res['id'],
                        "type": res['type'],
                        "label": res['name'] or res['id'],
                        "status": res['state'],
                        "metadata": {
                            "Region": res['region']
                        }
                    }
                else:
                    # Update existing node state/region
                    existing_nodes[res['id']]['status'] = res['state']
                    if 'metadata' not in existing_nodes[res['id']]:
                        existing_nodes[res['id']]['metadata'] = {}
                    existing_nodes[res['id']]['metadata']['Region'] = res['region']
                    
            existing_data['nodes'] = list(existing_nodes.values())
            
            with open(filename, "w") as f:
                json.dump(existing_data, f, indent=4)
        except Exception as e:
            print(f"Warning: Failed to save resources to JSON: {e}")
            
        return resources

