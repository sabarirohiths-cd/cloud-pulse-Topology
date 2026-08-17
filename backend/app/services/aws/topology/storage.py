from .base import BaseTopologyBuilder

class StorageMixin(BaseTopologyBuilder):
    def _fetch_efs(self):
        print("Fetching EFS...")
        try:
            filesystems = self.efs.describe_file_systems().get('FileSystems', [])
            for fs in filesystems:
                fs_id = fs.get('FileSystemId')
                mts = self.efs.describe_mount_targets(FileSystemId=fs_id).get('MountTargets', [])
                for mt in mts:
                    self.raw_data['EFSMountTargets'].append({
                        'SubnetId': mt.get('SubnetId'),
                        'FileSystemId': fs_id,
                        'MountTargetId': mt.get('MountTargetId'),
                        'IpAddress': mt.get('IpAddress')
                    })
        except Exception:
            pass

    def _fetch_fsx(self):
        print("Fetching FSx...")
        try:
            fsx_resp = self.fsx.describe_file_systems()
            for fs in fsx_resp.get('FileSystems', []):
                self.raw_data['FSxFileSystems'].append({
                    'SubnetIds': fs.get('SubnetIds', []),
                    'FileSystemId': fs.get('FileSystemId'),
                    'FileSystemType': fs.get('FileSystemType'),
                    'StorageCapacity': fs.get('StorageCapacity'),
                    'Lifecycle': fs.get('Lifecycle')
                })
        except Exception:
            pass
