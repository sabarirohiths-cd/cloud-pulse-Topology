from .base_tracer import BaseTracer
import logging

logger = logging.getLogger(__name__)

class StorageTracer(BaseTracer):
    def trace(self, block_device_mappings, root_id):
        """
        Traces attached EBS volumes based on block device mappings.
        """
        if not block_device_mappings:
            return

        vol_ids = [mapping.get('Ebs', {}).get('VolumeId') for mapping in block_device_mappings if mapping.get('Ebs', {}).get('VolumeId')]
        if not vol_ids:
            return

        try:
            vols_resp = self.ec2_client.describe_volumes(VolumeIds=vol_ids)
            for vol in vols_resp.get('Volumes', []):
                vol_id = vol['VolumeId']
                vol_state = vol.get('State', 'attached')
                v_health = "HEALTHY"
                v_diag = None
                
                if vol_state == 'error':
                    v_health = "CRITICAL"
                    v_diag = "EBS Volume IOPS degraded or failed."
                    
                self.add_node(vol_id, 'EBS', vol_id, vol_state, {
                    "SizeGB": vol.get('Size'),
                    "VolumeType": vol.get('VolumeType'),
                    "IOPS": vol.get('Iops'),
                    "Encrypted": vol.get('Encrypted'),
                    "Throughput": vol.get('Throughput')
                }, health_state=v_health, diagnostic=v_diag)
                
                self.add_edge(root_id, vol_id, 'MOUNTS')
        except Exception as e:
            logger.warning(f"Failed to describe EBS volumes for {root_id}: {e}")
