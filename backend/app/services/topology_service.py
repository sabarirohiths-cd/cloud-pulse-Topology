import boto3
import json
import asyncio
from app.services.aws.topology.core.flow_builder import ComputeFlowBuilder
from app.schemas.topology.topology import ComputeFlowRequest
from app.core.database import SessionLocal
from app.models.config.config_cloud_account import ConfigCloudAccount
from app.core.security import decrypt_credentials
from sqlalchemy import select, delete
from app.models.topology.topology_models import TopologyNode, TopologyEdge
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
            resource_id=request.resource_id,
            observability_options=request.observability_options,
            lookback_minutes=request.lookback_minutes
        )
        
        loop = asyncio.get_event_loop()
        flow_data = await loop.run_in_executor(None, builder.build)
        
        async with SessionLocal() as db:
            # Upsert nodes
            for n in flow_data.get('nodes', []):
                result = await db.execute(select(TopologyNode).filter(TopologyNode.id == n['id']))
                existing_node = result.scalars().first()
                
                meta = n.get('metadata', {})
                if "health_state" in n: meta["health_state"] = n["health_state"]
                if "diagnostic" in n: meta["diagnostic"] = n["diagnostic"]
                if "diagnostic_details" in n: meta["diagnostic_details"] = n["diagnostic_details"]
                
                region = meta.get("Region") or meta.get("region") or n.get("region")
                account_name = meta.get("AccountName") or meta.get("account_name") or n.get("account_name") or "cpi-topology-scanner"
                
                if str(n['id']).startswith("arn:aws:"):
                    parts = str(n['id']).split(":")
                    if not region and len(parts) >= 4 and parts[3]: region = parts[3]
                    
                if existing_node:
                    old_meta = existing_node.metadata_json or {}
                    for k, v in old_meta.items():
                        if k not in meta:
                            meta[k] = v
                    existing_node.metadata_json = meta
                    if n.get("status"): existing_node.status = n["status"]
                else:
                    new_node = TopologyNode(
                        id=n['id'],
                        type=n.get('type', 'UNKNOWN'),
                        label=n.get('label'),
                        region=region,
                        account_name=account_name,
                        status=n.get('status', 'UNKNOWN'),
                        metadata_json=meta
                    )
                    db.add(new_node)
                    
            # Upsert edges
            for e in flow_data.get('edges', []):
                source = e.get('source')
                target = e.get('target')
                if not source or not target: continue
                edge_id = f"{source}::{target}"
                
                meta = e.get('metadata', {})
                if "health_state" in e: meta["health_state"] = e["health_state"]
                if "diagnostic" in e: meta["diagnostic"] = e["diagnostic"]
                
                result = await db.execute(select(TopologyEdge).filter(TopologyEdge.id == edge_id))
                existing_edge = result.scalars().first()
                if existing_edge:
                    existing_edge.metadata_json = meta
                else:
                    new_edge = TopologyEdge(
                        id=edge_id,
                        source_id=source,
                        target_id=target,
                        type=e.get("relation", "LINK"),
                        metadata_json=meta
                    )
                    db.add(new_edge)
            
            await db.commit()
            
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
                        tags = {t['Key']: t['Value'] for t in inst.get('Tags', [])}
                        name = tags.get('Name')
                        
                        managed_by = None
                        
                        # Mapping of AWS tags to their human-readable service names
                        MANAGED_TAGS_MAP = {
                            'aws:autoscaling:groupname': 'ASG',
                            'eks:cluster-name': 'EKS',
                            'elasticbeanstalk:environment-name': 'Beanstalk',
                            'aws:batch:compute-environment': 'Batch',
                            'elasticmapreduce:job-flow-id': 'EMR',
                            'aws:cloudformation:stack-name': 'CFN'
                        }
                        
                        managed_by = None
                        for tk, tv in tags.items():
                            tk_lower = tk.lower()
                            if tk_lower in MANAGED_TAGS_MAP:
                                # We prioritize explicit clusters over CFN
                                if MANAGED_TAGS_MAP[tk_lower] != 'CFN' or not managed_by:
                                    managed_by = f"{MANAGED_TAGS_MAP[tk_lower]}: {tv}"
                                if MANAGED_TAGS_MAP[tk_lower] != 'CFN':
                                    break
                            elif 'amazonecsmanaged' in tk_lower:
                                managed_by = "ECS Worker"
                                break
                            
                        state_name = inst.get('State', {}).get('Name', 'unknown')
                        if state_name in ['terminated', 'shutting-down']:
                            continue
                            
                        resources.append({
                            "id": inst['InstanceId'],
                            "name": name,
                            "type": "EC2",
                            "state": state_name,
                            "region": region,
                            "managed_by": managed_by
                        })
        else:
            raise NotImplementedError(f"Listing for {compute_type} is not yet implemented.")
            
        async with SessionLocal() as db:
            # 1. Prune nodes that no longer exist in AWS for this compute type and region
            fetched_resource_ids = {res['id'] for res in resources}
            result = await db.execute(select(TopologyNode.id).filter(TopologyNode.type == compute_type_upper, TopologyNode.region == region))
            existing_ids_for_type_region = {row for row in result.scalars().all()}
            
            keys_to_delete = existing_ids_for_type_region - fetched_resource_ids
            if keys_to_delete:
                await db.execute(delete(TopologyNode).where(TopologyNode.id.in_(keys_to_delete)))
                await db.execute(delete(TopologyEdge).where(TopologyEdge.source_id.in_(keys_to_delete) | TopologyEdge.target_id.in_(keys_to_delete)))
                
            # 2. Add or update fetched resources
            for res in resources:
                metadata = {"Region": res['region']}
                if res.get('managed_by'):
                    metadata['managed_by'] = res['managed_by']
                    
                result = await db.execute(select(TopologyNode).filter(TopologyNode.id == res['id']))
                existing_node = result.scalars().first()
                
                if existing_node:
                    existing_node.status = res['state']
                    meta = existing_node.metadata_json or {}
                    meta['Region'] = res['region']
                    if res.get('managed_by'):
                        meta['managed_by'] = res['managed_by']
                    # Re-assign to trigger SQLAlchemy JSON mutation detection if necessary
                    existing_node.metadata_json = dict(meta)
                else:
                    new_node = TopologyNode(
                        id=res['id'],
                        type=res['type'],
                        label=res['name'] or res['id'],
                        region=res['region'],
                        account_name="cpi-topology-scanner",
                        status=res['state'],
                        metadata_json=metadata
                    )
                    db.add(new_node)
                    
            await db.commit()
            
            # Orphan cleanup: nodes not connected to any EC2 instance
            res_nodes = await db.execute(select(TopologyNode))
            all_nodes = res_nodes.scalars().all()
            res_edges = await db.execute(select(TopologyEdge))
            all_edges = res_edges.scalars().all()
            
            adj = {}
            for e in all_edges:
                adj.setdefault(e.source_id, []).append(e.target_id)
                adj.setdefault(e.target_id, []).append(e.source_id)
                
            roots = [n.id for n in all_nodes if n.type == 'EC2']
            visited = set()
            queue = roots[:]
            while queue:
                curr = queue.pop(0)
                if curr not in visited:
                    visited.add(curr)
                    for neighbor in adj.get(curr, []):
                        if neighbor not in visited:
                            queue.append(neighbor)
                            
            all_node_ids = {n.id for n in all_nodes}
            orphans = all_node_ids - visited
            if orphans:
                await db.execute(delete(TopologyNode).where(TopologyNode.id.in_(orphans)))
                await db.execute(delete(TopologyEdge).where(TopologyEdge.source_id.in_(orphans) | TopologyEdge.target_id.in_(orphans)))
                await db.commit()
            
        return resources

