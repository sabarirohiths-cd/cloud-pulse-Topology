import logging
from app.services.aws.topology.tracers.base_tracer import BaseTracer

logger = logging.getLogger(__name__)

class IAMTracer(BaseTracer):
    def __init__(self, fetcher):
        super().__init__(fetcher)
        self.iam_client = getattr(self.fetcher, 'iam_client', self.session.client('iam', region_name=self.region))

    def trace(self, iam_profile_arn, resource_id, tags=None):
        if not tags:
            tags = {}
            
        if iam_profile_arn:
            try:
                # The arn is an instance profile arn: arn:aws:iam::123456789012:instance-profile/role-name
                profile_name = iam_profile_arn.split('/')[-1]
                
                profile_resp = self.iam_client.get_instance_profile(InstanceProfileName=profile_name)
                profile = profile_resp.get('InstanceProfile', {})
                
                roles = profile.get('Roles', [])
                if roles:
                    role = roles[0]
                    role_name = role.get('RoleName')
                    role_arn = role.get('Arn')
                    
                    # Fetch detailed role info
                    role_resp = self.iam_client.get_role(RoleName=role_name)
                    role_detail = role_resp.get('Role', {})
                    
                    # Count attached policies
                    attached_policies = self.iam_client.list_attached_role_policies(RoleName=role_name)
                    policy_count = len(attached_policies.get('AttachedPolicies', []))
                    
                    self.add_node(role_arn, 'IAM_ROLE', role_name, 'available', {
                        "RoleName": role_name,
                        "CreateDate": str(role_detail.get('CreateDate')),
                        "AttachedPoliciesCount": policy_count,
                        "Type": "Instance Profile"
                    })
                    self.add_edge(role_arn, resource_id, 'GRANTS_ACCESS_TO')
                    return
            except Exception as e:
                logger.warning(f"Failed to fetch IAM role details for {iam_profile_arn}: {e}")
                
            # Fallback to basic if API fails or lacks permission
            iam_id = iam_profile_arn.split('/')[-1]
            self.add_node(iam_profile_arn, 'IAM_ROLE', iam_id, 'available', {"Type": "Instance Profile"})
            self.add_edge(iam_profile_arn, resource_id, 'GRANTS_ACCESS_TO')
        else:
            app_driven = any(k in tags for k in ['Project', 'App', 'Environment', 'Application'])
            if app_driven:
                # Need to update the compute node's health
                compute_node = next((n for n in self.fetcher.nodes if n['id'] == resource_id), None)
                if compute_node:
                    compute_node['health_state'] = "DEGRADED"
                    compute_node['diagnostic'] = "No IAM Instance Profile attached. App may face AccessDenied errors."
