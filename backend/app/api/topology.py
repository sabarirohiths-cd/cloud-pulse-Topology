from fastapi import APIRouter, HTTPException, Depends
from app.schemas.topology.topology import ComputeFlowRequest, ComputeFlowResponse, ComputeResourceListResponse
from app.services.topology_service import TopologyService

router = APIRouter()

def get_topology_service():
    return TopologyService()

def extract_subgraph(data: dict, start_node_id: str) -> dict:
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    
    if not start_node_id:
        return {"nodes": [], "edges": []}
        
    node_types = {n.get("id"): n.get("type", "") for n in nodes}
    connected_nodes = {start_node_id}
    
    # Do not traverse BACKWARDS from these node types (i.e. if we are at an SNS topic, don't find other alarms that trigger it)
    STOP_BACKWARDS = {"SNS_TOPIC"}
    
    changed = True
    while changed:
        changed = False
        for e in edges:
            src, tgt = e.get("source"), e.get("target")
            
            # Forward traversal: src is in connected_nodes, we found a new tgt
            if src in connected_nodes and tgt not in connected_nodes:
                tgt_type = node_types.get(tgt, "")
                # Prevent lateral movement: if we are at a TG or ALB, do not traverse forward to other EC2s
                if tgt_type == "EC2" and tgt != start_node_id:
                    continue
                connected_nodes.add(tgt)
                changed = True
                
            # Backward traversal: tgt is in connected_nodes, we found a new src
            elif tgt in connected_nodes and src not in connected_nodes:
                tgt_type = node_types.get(tgt, "")
                tgt_str = str(tgt)
                
                # Stop backwards traversal from SNS topics (even if node type is missing) to prevent cross-alarm leakage
                if tgt_type in STOP_BACKWARDS or tgt_str.startswith("arn:aws:sns:"):
                    continue
                    
                src_type = node_types.get(src, "")
                # We WANT to traverse backwards to TARGET_GROUP and ALB (upstream traffic).
                # We only stop traversing backward if we hit ANOTHER EC2 (which shouldn't happen, but just in case).
                if src_type == "EC2" and src != start_node_id:
                    continue
                connected_nodes.add(src)
                changed = True
                
    sub_nodes = [n for n in nodes if n.get("id") in connected_nodes]
    sub_edges = [e for e in edges if e.get("source") in connected_nodes and e.get("target") in connected_nodes]
    
    # Return in the exact format the frontend expects for a trace
    return {
        "compute_id": start_node_id,
        "nodes": sub_nodes,
        "edges": sub_edges
    }

@router.get("/scan/compute-flow/local")
async def get_local_compute_flow(region: str = None, account_name: str = None):
    from app.core.database import SessionLocal
    from sqlalchemy import select
    from app.models.topology.topology_models import TopologyNode, TopologyEdge
    async with SessionLocal() as db:
        query = select(TopologyNode)
        if region:
            query = query.filter(TopologyNode.region == region)
        if account_name:
            query = query.filter(TopologyNode.account_name == account_name)
        nodes_res = await db.execute(query)
        nodes = nodes_res.scalars().all()
        
        edges_res = await db.execute(select(TopologyEdge))
        edges = edges_res.scalars().all()
        
        node_dicts = []
        for n in nodes:
            meta = n.metadata_json or {}
            # Restore health_state and diagnostic back to root for the frontend schema
            health_state = meta.get("health_state", n.status)
            diagnostic = meta.get("diagnostic")
            diagnostic_details = meta.get("diagnostic_details")
            node_dicts.append({
                "id": n.id, "type": n.type, "label": n.label, "status": n.status,
                "metadata": meta, "region": n.region, "account_name": n.account_name,
                "health_state": health_state, "diagnostic": diagnostic,
                "diagnostic_details": diagnostic_details
            })
            
        edge_dicts = []
        for e in edges:
            meta = e.metadata_json or {}
            health_state = meta.get("health_state", "HEALTHY")
            diagnostic = meta.get("diagnostic")
            edge_dicts.append({
                "source": e.source_id, "target": e.target_id, "relation": e.type,
                "metadata": meta, "health_state": health_state, "diagnostic": diagnostic
            })
        
        node_ids = {n["id"] for n in node_dicts}
        edge_dicts = [e for e in edge_dicts if e["source"] in node_ids and e["target"] in node_ids]

        compute_id = next((n["id"] for n in node_dicts if n["type"] == "EC2"), None)
        
        return {
            "compute_id": compute_id,
            "nodes": node_dicts,
            "edges": edge_dicts
        }

@router.get("/scan/compute-flow/local/{compute_id}")
async def get_local_trace(compute_id: str):
    from app.core.database import SessionLocal
    from sqlalchemy import select
    from app.models.topology.topology_models import TopologyNode, TopologyEdge
    async with SessionLocal() as db:
        nodes_res = await db.execute(select(TopologyNode))
        all_nodes = nodes_res.scalars().all()
        
        edges_res = await db.execute(select(TopologyEdge))
        all_edges = edges_res.scalars().all()
        
        node_dicts = []
        for n in all_nodes:
            meta = n.metadata_json or {}
            health_state = meta.get("health_state", n.status)
            diagnostic = meta.get("diagnostic")
            diagnostic_details = meta.get("diagnostic_details")
            node_dicts.append({
                "id": n.id, "type": n.type, "label": n.label, "status": n.status,
                "metadata": meta, "region": n.region, "account_name": n.account_name,
                "health_state": health_state, "diagnostic": diagnostic,
                "diagnostic_details": diagnostic_details
            })
            
        edge_dicts = []
        for e in all_edges:
            meta = e.metadata_json or {}
            health_state = meta.get("health_state", "HEALTHY")
            diagnostic = meta.get("diagnostic")
            edge_dicts.append({
                "source": e.source_id, "target": e.target_id, "relation": e.type,
                "metadata": meta, "health_state": health_state, "diagnostic": diagnostic
            })
        
        node_exists = any(n["id"] == compute_id for n in node_dicts)
        if node_exists:
            return extract_subgraph({"nodes": node_dicts, "edges": edge_dicts}, compute_id)
            
    raise HTTPException(status_code=404, detail="Trace not found locally")

@router.get("/scan/regions/cached")
async def get_cached_regions(account_name: str = None):
    from app.core.database import SessionLocal
    from sqlalchemy import select
    from app.models.topology.topology_models import TopologyNode
    async with SessionLocal() as db:
        query = select(TopologyNode.region).distinct()
        if account_name:
            query = query.filter(TopologyNode.account_name == account_name)
        res = await db.execute(query)
        regions = [r for r in res.scalars().all() if r and r != "global"]
        return {"regions": regions}

@router.post("/scan/temp-reset-mock-data")
async def temp_reset_mock_data():
    import os, json
    from app.core.database import SessionLocal
    from sqlalchemy import select, delete
    from app.models.topology.topology_models import TopologyNode, TopologyEdge
    
    async with SessionLocal() as db:
        # Check if mock data exists
        res = await db.execute(select(TopologyNode.id).filter(TopologyNode.account_name == "mock-data"))
        existing_ids = [r for r in res.scalars().all()]
        
        if existing_ids:
            # Delete mock data
            await db.execute(delete(TopologyEdge).where(TopologyEdge.source_id.in_(existing_ids) | TopologyEdge.target_id.in_(existing_ids)))
            await db.execute(delete(TopologyNode).where(TopologyNode.id.in_(existing_ids)))
            await db.commit()
            return {"status": "success", "message": "Mock data deleted", "action": "deleted"}
        
        # Otherwise, Insert mock data
        filename = "data/last_compute_flow.json"
        if not os.path.exists(filename):
            raise HTTPException(status_code=404, detail="Mock data file not found")
            
        with open(filename, "r") as f:
            data = json.load(f)
            
        # Insert nodes
        for n in data.get("nodes", []):
            meta = n.get("metadata", {})
            if "health_state" in n: meta["health_state"] = n["health_state"]
            if "diagnostic" in n: meta["diagnostic"] = n["diagnostic"]
            if "diagnostic_details" in n: meta["diagnostic_details"] = n["diagnostic_details"]
            
            region = meta.get("Region", "eu-west-1")
            account_name = "mock-data"
            
            node = TopologyNode(
                id=f"mock-{n['id']}",
                type=n.get("type", "UNKNOWN"),
                label=n.get("label"),
                region=region,
                account_name=account_name,
                status=n.get("status", "UNKNOWN"),
                metadata_json=meta
            )
            db.add(node)
            
        # Insert edges
        for e in data.get("edges", []):
            meta = {}
            if "health_state" in e: meta["health_state"] = e["health_state"]
            if "diagnostic" in e: meta["diagnostic"] = e["diagnostic"]
            
            mock_source = f"mock-{e['source']}"
            mock_target = f"mock-{e['target']}"
            
            edge = TopologyEdge(
                id=f"{mock_source}::{mock_target}",
                source_id=mock_source,
                target_id=mock_target,
                type=e.get("relation", "LINK"),
                metadata_json=meta
            )
            db.add(edge)
            
        await db.commit()
        
    return {"status": "success", "message": "Database populated with mock data", "action": "inserted"}

@router.post("/scan/temp-clear-all")
async def temp_clear_all():
    from app.core.database import SessionLocal
    from sqlalchemy import text
    
    async with SessionLocal() as db:
        await db.execute(text("DELETE FROM topology_edges"))
        await db.execute(text("DELETE FROM topology_nodes"))
        await db.commit()
        
    return {"status": "success", "message": "All topology data cleared"}

@router.get("/scan/accounts/cached")
async def get_cached_accounts():
    from app.core.database import SessionLocal
    from sqlalchemy import select
    from app.models.topology.topology_models import TopologyNode
    async with SessionLocal() as db:
        res = await db.execute(select(TopologyNode.account_name).distinct())
        accounts = [r for r in res.scalars().all() if r]
        return {"accounts": accounts}

@router.post("/scan/compute-flow", response_model=ComputeFlowResponse)
async def scan_compute_flow(request: ComputeFlowRequest, service: TopologyService = Depends(get_topology_service)):
    try:
        data = await service.scan_compute_flow(request)
        return ComputeFlowResponse(
            status="success",
            message=f"Compute flow successfully traced for {request.compute_type} {request.resource_id}",
            compute_id=data.get('compute_id'),
            warnings=data.get('warnings', []),
            nodes=data.get('nodes', []),
            edges=data.get('edges', [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scan/compute-resources/local")
async def get_local_compute_resources(region: str = None, compute_type: str = "EC2", account_name: str = None):
    from app.core.database import SessionLocal
    from sqlalchemy import select
    from app.models.topology.topology_models import TopologyNode
    async with SessionLocal() as db:
        query = select(TopologyNode).filter(TopologyNode.type == compute_type)
        if region:
            query = query.filter(TopologyNode.region == region)
        if account_name:
            query = query.filter(TopologyNode.account_name == account_name)
            
        res = await db.execute(query)
        nodes = res.scalars().all()
        
        resources = []
        for n in nodes:
            meta = n.metadata_json or {}
            resources.append({
                "id": n.id,
                "name": n.label,
                "type": n.type,
                "state": n.status,
                "region": n.region or region or "ap-south-1",
                "managed_by": meta.get("managed_by")
            })
        return {"resources": resources}

@router.get("/scan/compute-resources", response_model=ComputeResourceListResponse)
async def get_compute_resources(
    compute_type: str, 
    region: str = "ap-south-1", 
    account_id: str = None, 
    service: TopologyService = Depends(get_topology_service)
):
    try:
        resources = await service.list_compute_resources(account_id, region, compute_type)
        return ComputeResourceListResponse(
            status="success",
            message=f"Successfully fetched {len(resources)} {compute_type} resources.",
            resources=resources
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-compute-types")
async def get_supported_compute_types():
    from app.core.database import SessionLocal
    from sqlalchemy import select
    from app.models.topology.topology_models import TopologyNode
    
    base_compute_types = {"EC2", "ECS", "LAMBDA", "APPRUNNER"}
    found_types = set()
    
    async with SessionLocal() as db:
        res = await db.execute(select(TopologyNode.type).distinct())
        for t in res.scalars().all():
            if t and t.upper() in base_compute_types:
                found_types.add(t.upper())
                
    if not found_types:
        found_types.add("EC2")
        
    return {"compute_types": sorted(list(found_types))}
