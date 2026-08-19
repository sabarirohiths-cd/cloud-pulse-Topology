from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base

class TopologyResource(Base):
    __tablename__ = "topology_resources"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # --- Core Fields (Aligned with Control/Inventory) ---
    resource_id = Column(String, index=True, nullable=False)
    resource_name = Column(String, nullable=True)
    resource_type = Column(String, index=True, nullable=False) # e.g., 'VPC', 'SUBNET', 'EC2Instances'
    cloud_provider = Column(String, default="aws", index=True)
    account_name = Column(String, index=True, nullable=False)
    region = Column(String, index=True, nullable=False)
    
    # --- Topology Relationship Links ---
    vpc_id = Column(String, index=True, nullable=True)     
    subnet_id = Column(String, index=True, nullable=True)  
    
    # --- Deep Payload ---
    saved_config_json = Column(Text, nullable=False)
    
    last_scanned_at = Column(DateTime, default=datetime.utcnow)
