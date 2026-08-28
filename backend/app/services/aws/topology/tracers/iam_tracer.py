import logging
from app.services.aws.topology.tracers.base_tracer import BaseTracer

logger = logging.getLogger(__name__)

class IAMTracer(BaseTracer):
    def __init__(self, fetcher):
        super().__init__(fetcher)
        self.iam_client = getattr(self.fetcher, 'iam_client', self.session.client('iam', region_name=self.region))

    def _parse_s3_from_document(self, document, resource_id):
        s3_capabilities = []
        statements = document.get('Statement', [])
        if isinstance(statements, dict):
            statements = [statements]
            
        for stmt in statements:
            if stmt.get('Effect') == 'Allow':
                actions = stmt.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                    
                s3_actions = [a for a in actions if a.startswith('s3:') or a == '*']
                if s3_actions:
                    resources = stmt.get('Resource', [])
                    if isinstance(resources, str):
                        resources = [resources]
                        
                    for res in resources:
                        if isinstance(res, str) and res.startswith('arn:aws:s3:::'):
                            bucket_name = res.split(':::')[1].split('/')[0]
                            if bucket_name != '*' and bucket_name:
                                s3_capabilities.append(f"{bucket_name} ({len(s3_actions)} actions)")
                                self.add_node(bucket_name, 'S3_BUCKET', bucket_name, 'available', {"Type": "S3 Bucket"})
                                self.add_edge(resource_id, bucket_name, 'GRANTS_ACCESS_TO')
                            elif bucket_name == '*':
                                s3_capabilities.append("ALL_BUCKETS")
        return s3_capabilities

    def trace(self, iam_profile_arn, resource_id, tags=None):
        if not tags:
            tags = {}
            
        if iam_profile_arn:
            try:
                profile_name = iam_profile_arn.split('/')[-1]
                profile_resp = self.iam_client.get_instance_profile(InstanceProfileName=profile_name)
                profile = profile_resp.get('InstanceProfile', {})
                
                roles = profile.get('Roles', [])
                if roles:
                    role = roles[0]
                    role_name = role.get('RoleName')
                    role_arn = role.get('Arn')
                    
                    role_resp = self.iam_client.get_role(RoleName=role_name)
                    role_detail = role_resp.get('Role', {})
                    
                    attached_policies = self.iam_client.list_attached_role_policies(RoleName=role_name)
                    attached = attached_policies.get('AttachedPolicies', [])
                    
                    inline_policies = self.iam_client.list_role_policies(RoleName=role_name)
                    inline = inline_policies.get('PolicyNames', [])
                    
                    total_policies = len(attached) + len(inline)
                    s3_caps = []
                    
                    # Parse Managed Policies
                    for p in attached:
                        try:
                            # Pre-check common full access
                            if "AmazonS3FullAccess" in p['PolicyName']:
                                s3_caps.append("ALL_BUCKETS (AmazonS3FullAccess)")
                                continue
                            
                            pol = self.iam_client.get_policy(PolicyArn=p['PolicyArn'])
                            ver = pol['Policy']['DefaultVersionId']
                            pol_ver = self.iam_client.get_policy_version(PolicyArn=p['PolicyArn'], VersionId=ver)
                            doc = pol_ver['PolicyVersion']['Document']
                            s3_caps.extend(self._parse_s3_from_document(doc, resource_id))
                        except Exception as e:
                            logger.debug(f"Could not parse managed policy {p.get('PolicyName')}: {e}")

                    # Parse Inline Policies
                    for p_name in inline:
                        try:
                            pol_resp = self.iam_client.get_role_policy(RoleName=role_name, PolicyName=p_name)
                            doc = pol_resp['PolicyDocument']
                            s3_caps.extend(self._parse_s3_from_document(doc, resource_id))
                        except Exception as e:
                            logger.debug(f"Could not parse inline policy {p_name}: {e}")
                    
                    meta = {
                        "RoleName": role_name,
                        "CreateDate": str(role_detail.get('CreateDate')),
                        "AttachedPoliciesCount": total_policies,
                        "Type": "Instance Profile"
                    }
                    if s3_caps:
                        meta['S3_Access'] = list(set(s3_caps))
                        
                    self.add_node(role_arn, 'IAM_ROLE', role_name, 'available', meta)
                    self.add_edge(role_arn, resource_id, 'GRANTS_ACCESS_TO')
                    
                    # Also update the EC2 node's diagnostic details if it has S3 access
                    if s3_caps:
                        compute_node = next((n for n in self.fetcher.nodes if n['id'] == resource_id), None)
                        if compute_node:
                            if 'diagnostic_details' not in compute_node:
                                compute_node['diagnostic_details'] = {}
                            compute_node['diagnostic_details']['iam_s3_capabilities'] = list(set(s3_caps))
                    return
            except Exception as e:
                logger.warning(f"Failed to fetch IAM role details for {iam_profile_arn}: {e}")
                
            iam_id = iam_profile_arn.split('/')[-1]
            self.add_node(iam_profile_arn, 'IAM_ROLE', iam_id, 'available', {"Type": "Instance Profile"})
            self.add_edge(iam_profile_arn, resource_id, 'GRANTS_ACCESS_TO')
        else:
            app_driven = any(k in tags for k in ['Project', 'App', 'Environment', 'Application'])
            if app_driven:
                compute_node = next((n for n in self.fetcher.nodes if n['id'] == resource_id), None)
                if compute_node:
                    compute_node['health_state'] = "DEGRADED"
                    compute_node['diagnostic'] = "No IAM Instance Profile attached. App may face AccessDenied errors."
