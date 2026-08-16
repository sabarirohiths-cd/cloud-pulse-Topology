from .base import BaseTopologyBuilder

class StorageMixin(BaseTopologyBuilder):
    def _fetch_efs(self):
        print("Fetching EFS...")
        subnet_map = self._get_subnet_map()
        try:
            filesystems = self.efs.describe_file_systems().get('FileSystems', [])
            for fs in filesystems:
                fs_id = fs.get('FileSystemId')
                mts = self.efs.describe_mount_targets(FileSystemId=fs_id).get('MountTargets', [])
                for mt in mts:
                    sid = mt.get('SubnetId')
                    if sid in subnet_map:
                        subnet_map[sid]['EFSMountTargets'].append({
                            'FileSystemId': fs_id,
                            'MountTargetId': mt.get('MountTargetId'),
                            'IpAddress': mt.get('IpAddress')
                        })
        except Exception:
            pass

    def _fetch_fsx(self):
        print("Fetching FSx...")
        subnet_map = self._get_subnet_map()
        try:
            fsx_resp = self.fsx.describe_file_systems()
            for fs in fsx_resp.get('FileSystems', []):
                fs_info = {
                    'FileSystemId': fs.get('FileSystemId'),
                    'FileSystemType': fs.get('FileSystemType'),
                    'StorageCapacity': fs.get('StorageCapacity'),
                    'Lifecycle': fs.get('Lifecycle')
                }
                for sid in fs.get('SubnetIds', []):
                    if sid in subnet_map:
                        subnet_map[sid]['FSxFileSystems'].append(fs_info)
        except Exception:
            pass
