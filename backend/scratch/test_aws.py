import asyncio
from app.services.topology_service import TopologyService

async def test():
    s = TopologyService()
    sess = await s.get_aws_session('cpi-topology-scanner')
    creds = sess.get_credentials()
    if creds:
        print("Credentials loaded!")
    else:
        print("NO CREDENTIALS LOADED!")
    
    # Try getting instances
    try:
        resources = await s.list_compute_resources('cpi-topology-scanner', 'us-east-1', 'EC2')
        print(f"Resources: {resources}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
