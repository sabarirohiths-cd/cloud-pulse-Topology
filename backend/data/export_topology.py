import asyncio
import json
import os
import sys

# Add backend directory to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock required environment variables so Pydantic Settings doesn't crash
os.environ.setdefault("ENCRYPTION_KEY", "mock-key-for-export-script-only-1234")
os.environ.setdefault("JWT_SECRET", "mock-jwt-for-export-script-only-1234")
# Since we are running from inside the data/ folder, the DB is right here!
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///cloud_pulse.db"

from app.core.database import SessionLocal
from app.models.topology.topology_models import TopologyNode, TopologyEdge
from sqlalchemy import select

# ==========================================
# 🛠️ EDIT THIS TO CHANGE THE ACCOUNT NAME
# ==========================================
TARGET_ACCOUNT = "cd-prod"
OUTPUT_FILE = "exported_topology.json"
# ==========================================
# cd \backend\data> 
# py export_topology.py
# ==========================================

async def export_topology():
    print(f"Exporting topology data for account: '{TARGET_ACCOUNT}'")
    
    async with SessionLocal() as db:
        # Get Nodes
        res = await db.execute(select(TopologyNode).filter(TopologyNode.account_name == TARGET_ACCOUNT))
        nodes = res.scalars().all()
        
        if not nodes:
            print(f"No nodes found for account: '{TARGET_ACCOUNT}'")
            return
            
        node_ids = [n.id for n in nodes]
        
        # Get Edges connected to these nodes
        res = await db.execute(select(TopologyEdge).filter(TopologyEdge.source_id.in_(node_ids) | TopologyEdge.target_id.in_(node_ids)))
        edges = res.scalars().all()
        
        # Format Nodes
        formatted_nodes = []
        for n in nodes:
            formatted_nodes.append({
                "id": n.id,
                "type": n.type,
                "label": n.label,
                "status": n.status,
                "region": n.region,
                "account_name": n.account_name,
                "metadata": n.metadata_json
            })
            
        # Format Edges
        formatted_edges = []
        for e in edges:
            formatted_edges.append({
                "id": e.id,
                "source": e.source_id,
                "target": e.target_id,
                "relation": e.type,
                "metadata": e.metadata_json
            })
            
        # Build JSON Output
        output_data = {
            "account_name": TARGET_ACCOUNT,
            "total_nodes": len(formatted_nodes),
            "total_edges": len(formatted_edges),
            "nodes": formatted_nodes,
            "edges": formatted_edges
        }
        
        # Save to file
        output_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4)
            
        print(f"Successfully exported {len(formatted_nodes)} nodes and {len(formatted_edges)} edges!")
        print(f"Saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(export_topology())
