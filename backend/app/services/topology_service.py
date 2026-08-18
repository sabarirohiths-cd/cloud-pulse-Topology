import boto3
import json
import os
import asyncio
from sqlalchemy import select
from app.services.aws.topology_builder import AWSTopologyBuilder
from app.schemas.topology.topology import TopologyScanRequest
from app.core.database import SessionLocal
from app.models.config.config_cloud_account import ConfigCloudAccount
from app.core.security import decrypt_credentials

class TopologyService:
    def __init__(self):
        pass

    async def _get_account(self, account_id: str = None):
        async with SessionLocal() as session:
            if account_id:
                result = await session.execute(
                    select(ConfigCloudAccount).where(ConfigCloudAccount.account_name == account_id)
                )
            else:
                result = await session.execute(
                    select(ConfigCloudAccount) # Fetch the first available account if none specified
                )
            return result.scalars().first()

    def get_aws_session(self, account_id: str = None, region: str = 'ap-south-1') -> boto3.Session:
        try:
            account = asyncio.run(self._get_account(account_id))
            if not account:
                print(f"No database account configured! Falling back to env variables.")
                return boto3.Session(region_name=region)
                
            creds = decrypt_credentials(account.encrypted_credentials)
            print(f"Successfully retrieved credentials for DB account '{account.account_name}' in {region}.")
            return boto3.Session(
                aws_access_key_id=creds.get('aws_access_key_id'),
                aws_secret_access_key=creds.get('aws_secret_access_key'),
                aws_session_token=creds.get('aws_session_token'), # May be None, which is fine
                region_name=region
            )
        except Exception as e:
            print(f"Failed to fetch DB credentials: {e}. Falling back to env variables.")
            return boto3.Session(region_name=region)

    def scan_topology(self, request: TopologyScanRequest):
        # We still initialize the boto3.Session with a default region,
        # but the builder takes the list of target regions to scan.
        default_region = request.regions[0] if request.regions else 'ap-south-1'
        session = self.get_aws_session(request.account_id, default_region)
        
        builder = AWSTopologyBuilder(session=session, regions=request.regions)
        builder.build()
        
        # Save output for dev/sample viewing
        builder.save_output()
        
        topology_data = builder.get_topology()
        return topology_data

    def get_sample_topology(self):
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'output')
        mock_file = os.path.join(output_dir, 'mock_enterprise_topology.json')
        live_file = os.path.join(output_dir, 'final_complete_topology.json')
        
        merged_regions = {}
        merged_global = {}
        
        # Load mock data
        if os.path.exists(mock_file):
            try:
                with open(mock_file, 'r') as f:
                    mock_data = json.load(f)
                    if isinstance(mock_data, dict) and "Regions" in mock_data:
                        for region, vpcs in mock_data["Regions"].items():
                            merged_regions.setdefault(region, []).extend(vpcs)
                    if isinstance(mock_data, dict) and "GlobalResources" in mock_data:
                        for res_type, resources in mock_data["GlobalResources"].items():
                            merged_global.setdefault(res_type, []).extend(resources)
                    elif isinstance(mock_data, list):
                        merged_regions.setdefault("ap-south-1", []).extend(mock_data)
            except Exception as e:
                print(f"Failed to read mock topology: {e}")

        # Load live scanned data
        if os.path.exists(live_file):
            try:
                with open(live_file, 'r') as f:
                    live_data = json.load(f)
                    if isinstance(live_data, dict) and "Regions" in live_data:
                        for region, vpcs in live_data["Regions"].items():
                            merged_regions.setdefault(region, []).extend(vpcs)
                    if isinstance(live_data, dict) and "GlobalResources" in live_data:
                        for res_type, resources in live_data["GlobalResources"].items():
                            merged_global.setdefault(res_type, []).extend(resources)
                    elif isinstance(live_data, list):
                        merged_regions.setdefault("ap-south-1", []).extend(live_data)
            except Exception as e:
                print(f"Failed to read live topology: {e}")
                
        return {
            "Regions": merged_regions,
            "GlobalResources": merged_global
        }
