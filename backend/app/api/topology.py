from fastapi import APIRouter, HTTPException, Depends
from app.schemas.topology.topology import TopologyScanRequest, TopologyResponse
from app.services.topology_service import TopologyService

router = APIRouter()

def get_topology_service():
    return TopologyService()

@router.post("/scan", response_model=TopologyResponse)
def scan_aws_topology(request: TopologyScanRequest, service: TopologyService = Depends(get_topology_service)):
    try:
        data = service.scan_topology(request)
        return TopologyResponse(
            status="success",
            message=f"Topology successfully scanned for region {request.region}",
            data=data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sample", response_model=TopologyResponse)
def get_sample_topology(service: TopologyService = Depends(get_topology_service)):
    try:
        data = service.get_sample_topology()
        return TopologyResponse(
            status="success",
            message="Sample topology successfully retrieved",
            data=data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{account_id}", response_model=TopologyResponse)
def get_topology_by_account(account_id: str, service: TopologyService = Depends(get_topology_service)):
    # Mocking fetching a saved topology for a specific account. Here we just return sample for now.
    try:
        data = service.get_sample_topology()
        return TopologyResponse(
            status="success",
            message=f"Topology successfully retrieved for account {account_id}",
            data=data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
