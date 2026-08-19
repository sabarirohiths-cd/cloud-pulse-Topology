from fastapi import APIRouter, HTTPException, Depends
from app.schemas.topology.topology import TopologyScanRequest, TopologyResponse
from app.services.topology_service import TopologyService

router = APIRouter()

def get_topology_service():
    return TopologyService()

@router.post("/scan", response_model=TopologyResponse)
async def scan_aws_topology(request: TopologyScanRequest, service: TopologyService = Depends(get_topology_service)):
    try:
        data = await service.scan_topology(request)
        return TopologyResponse(
            status="success",
            message=f"Topology successfully scanned for regions {', '.join(request.regions)}",
            data=data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}", response_model=TopologyResponse)
async def get_topology_by_account(account_id: str, service: TopologyService = Depends(get_topology_service)):
    try:
        data = await service.get_saved_topology(account_name=account_id)
        return TopologyResponse(
            status="success",
            message=f"Topology successfully retrieved for account {account_id} from Database",
            data=data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
