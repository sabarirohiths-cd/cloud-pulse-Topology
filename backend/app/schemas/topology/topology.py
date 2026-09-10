from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class ComputeFlowRequest(BaseModel):
    account_id: Optional[str] = Field(default=None, description="The AWS Account ID to scan")
    region: str = Field(default="ap-south-1", description="AWS Region to scan")
    compute_type: str = Field(..., description="Type of compute node (EC2, ECS, LAMBDA, APPRUNNER)")
    resource_id: str = Field(..., description="The ID of the compute resource to trace")
    observability_options: Optional[List[str]] = Field(default=None, description="List of observability diagnostics to run (METRICS, LOGS, XRAY)")
    lookback_minutes: Optional[int] = Field(default=15, description="Lookback window in minutes for diagnostics")

class TopologyNodeSchema(BaseModel):
    id: str
    type: str
    label: Optional[str] = None
    region: Optional[str] = None
    account_name: Optional[str] = None
    status: str = "UNKNOWN"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    health_state: Optional[str] = None
    diagnostic: Optional[str] = None
    diagnostic_details: Optional[Dict[str, Any]] = None

class TopologyEdgeSchema(BaseModel):
    id: str
    source: str
    target: str
    type: Optional[str] = None
    relation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    health_state: Optional[str] = None
    diagnostic: Optional[str] = None

class ComputeFlowResponse(BaseModel):
    status: str
    message: str
    compute_id: str
    warnings: List[str] = Field(default_factory=list)
    nodes: List[TopologyNodeSchema]
    edges: List[TopologyEdgeSchema]

class ComputeResource(BaseModel):
    id: str
    name: Optional[str] = None
    type: str
    state: str
    region: str

class ComputeResourceListResponse(BaseModel):
    status: str
    message: str
    resources: List[ComputeResource]
