from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class TopologyScanRequest(BaseModel):
    account_id: Optional[str] = Field(default=None, description="The AWS Account ID to scan")
    regions: List[str] = Field(default=["ap-south-1"], description="List of AWS Regions to scan")
    vpc_id: Optional[str] = Field(default=None, description="Specific VPC to scan (optional)")

class TopologyResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any]
