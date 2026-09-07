from sqlalchemy import Column, String, JSON
from app.core.database import Base

class TopologyNode(Base):
    __tablename__ = "topology_nodes"
    
    id = Column(String, primary_key=True, index=True)
    type = Column(String, index=True, nullable=False)
    label = Column(String, nullable=True)
    region = Column(String, index=True, nullable=True)
    account_name = Column(String, index=True, nullable=True)
    status = Column(String, default="UNKNOWN")
    metadata_json = Column(JSON, nullable=True)

class TopologyEdge(Base):
    __tablename__ = "topology_edges"
    
    id = Column(String, primary_key=True, index=True) # Usually a compound like source_id-target_id
    source_id = Column(String, index=True, nullable=False)
    target_id = Column(String, index=True, nullable=False)
    type = Column(String, index=True, nullable=True) # e.g. CONTAINS, ROUTES_TO
    metadata_json = Column(JSON, nullable=True)
