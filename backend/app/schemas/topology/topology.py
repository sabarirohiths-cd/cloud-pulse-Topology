from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class TopologyScanRequest(BaseModel):
    account_id: Optional[str] = Field(default=None, description="The AWS Account ID to scan")
    region: Optional[str] = Field(default="ap-south-1", description="The AWS Region to scan")
    vpc_id: Optional[str] = Field(default=None, description="Specific VPC to scan (optional)")

class TopologyResponse(BaseModel):
    status: str
    message: str
    data: List[Dict[str, Any]]
