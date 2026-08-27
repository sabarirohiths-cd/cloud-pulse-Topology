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
        
    connected_nodes = {start_node_id}
    changed = True
    while changed:
        changed = False
        for e in edges:
            src, tgt = e.get("source"), e.get("target")
            
            # Check if target is another EC2 instance
            if src in connected_nodes and tgt not in connected_nodes:
                tgt_node = next((n for n in nodes if n.get("id") == tgt), {})
                if tgt_node.get("type") == "EC2" and tgt != start_node_id:
                    continue
                connected_nodes.add(tgt)
                changed = True
                
            # Check if source is another EC2 instance
            elif tgt in connected_nodes and src not in connected_nodes:
                src_node = next((n for n in nodes if n.get("id") == src), {})
                if src_node.get("type") == "EC2" and src != start_node_id:
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
async def get_local_compute_flow(region: str = None):
    import os, json
    filename = "data/last_compute_flow.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
                last_id = data.get("last_compute_id")
                if last_id:
                    start_node = next((n for n in data.get("nodes", []) if n.get("id") == last_id), None)
                    if region and start_node and start_node.get("metadata", {}).get("Region") != region:
                        return {"nodes": [], "edges": []}
                    return extract_subgraph(data, last_id)
            except json.JSONDecodeError:
                pass
    return {"nodes": [], "edges": []}

@router.get("/scan/compute-flow/local/{compute_id}")
async def get_local_trace(compute_id: str):
    import os, json
    filename = "data/last_compute_flow.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
                # Check if the node even exists in our DB
                node_exists = any(n.get("id") == compute_id for n in data.get("nodes", []))
                if node_exists:
                    return extract_subgraph(data, compute_id)
            except json.JSONDecodeError:
                pass
    raise HTTPException(status_code=404, detail="Trace not found locally")

@router.get("/scan/regions/cached")
async def get_cached_regions():
    import os, json
    regions = []
    filename = "data/last_compute_flow.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
                for n in data.get("nodes", []):
                    r = n.get("metadata", {}).get("Region")
                    if r and r != "global":
                        regions.append(r)
            except:
                pass
    return {"regions": list(set(regions))}

@router.post("/scan/compute-flow", response_model=ComputeFlowResponse)
async def scan_compute_flow(request: ComputeFlowRequest, service: TopologyService = Depends(get_topology_service)):
    try:
        data = await service.scan_compute_flow(request)
        return ComputeFlowResponse(
            status="success",
            message=f"Compute flow successfully traced for {request.compute_type} {request.resource_id}",
            compute_id=data.get('compute_id'),
            nodes=data.get('nodes', []),
            edges=data.get('edges', [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scan/compute-resources/local")
async def get_local_compute_resources(region: str = None, compute_type: str = "EC2"):
    import os, json
    filename = "data/last_compute_flow.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
                nodes = data.get("nodes", [])
                
                resources = []
                for n in nodes:
                    if n.get("type") == compute_type:
                        # If region is specified, try to filter, but if Region metadata is missing, just include it (lenient for mock DB)
                        node_region = n.get("metadata", {}).get("Region")
                        if region and node_region and node_region != region:
                            continue
                            
                        resources.append({
                            "id": n.get("id"),
                            "name": n.get("label"),
                            "type": n.get("type"),
                            "state": n.get("status"),
                            "region": node_region or region or "ap-south-1",
                            "managed_by": n.get("metadata", {}).get("managed_by")
                        })
                return {"resources": resources}
            except:
                pass
    return {"resources": []}

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
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-compute-types")
async def get_supported_compute_types():
    import os, json
    
    # Base supported list of compute types we know how to trace
    base_compute_types = {"EC2", "ECS", "LAMBDA", "APPRUNNER"}
    found_types = set()
    
    filename = "data/last_compute_flow.json"
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
                nodes = data.get("nodes", [])
                for n in nodes:
                    t = n.get("type", "").upper()
                    if t in base_compute_types:
                        found_types.add(t)
        except Exception:
            pass
            
    # Always fallback to at least EC2 if nothing found to prevent empty dropdown
    if not found_types:
        found_types.add("EC2")
        
    return {"compute_types": sorted(list(found_types))}
