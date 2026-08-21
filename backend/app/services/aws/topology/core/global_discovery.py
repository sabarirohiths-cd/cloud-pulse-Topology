import logging
logger = logging.getLogger(__name__)

import boto3
import json

class GlobalDiscoveryEngine:
    def __init__(self, session: boto3.Session):
        self.session = session
        logger.info("Initializing Global Discovery Engine...")
        self.iam = self.session.client('iam', region_name='us-east-1')
        self.cloudfront = self.session.client('cloudfront', region_name='us-east-1')
        self.route53 = self.session.client('route53', region_name='us-east-1')
        self.s3 = self.session.client('s3', region_name='us-east-1')
        
        self.global_data = {
            'IAMRoles': [],
            'IAMUsers': [],
            'CloudFrontDistributions': [],
            'Route53HostedZones': [],
            'S3Buckets': []
        }

    def run(self):
        logger.info("Running Global Discovery...")
        self._fetch_iam()
        self._fetch_cloudfront()
        self._fetch_route53()
        self._fetch_s3()
        return self.global_data

    def _fetch_iam(self):
        try:
            logger.info("Fetching IAM Roles...")
            roles_resp = self.iam.list_roles()
            for role in roles_resp.get('Roles', []):
                self.global_data['IAMRoles'].append({
                    'RoleName': role.get('RoleName'),
                    'Arn': role.get('Arn'),
                    'CreateDate': role.get('CreateDate').isoformat() if role.get('CreateDate') else None
                })
            
            logger.info("Fetching IAM Users...")
            users_resp = self.iam.list_users()
            for user in users_resp.get('Users', []):
                self.global_data['IAMUsers'].append({
                    'UserName': user.get('UserName'),
                    'Arn': user.get('Arn'),
                    'CreateDate': user.get('CreateDate').isoformat() if user.get('CreateDate') else None
                })
        except Exception as e:
            logger.info(f"Error fetching IAM: {e}")

    def _fetch_cloudfront(self):
        try:
            logger.info("Fetching CloudFront...")
            cf_resp = self.cloudfront.list_distributions()
            for dist in cf_resp.get('DistributionList', {}).get('Items', []):
                self.global_data['CloudFrontDistributions'].append({
                    'Id': dist.get('Id'),
                    'Arn': dist.get('ARN'),
                    'DomainName': dist.get('DomainName'),
                    'Status': dist.get('Status'),
                    'Origins': [o.get('DomainName') for o in dist.get('Origins', {}).get('Items', [])]
                })
        except Exception as e:
            logger.info(f"Error fetching CloudFront: {e}")

    def _fetch_route53(self):
        try:
            logger.info("Fetching Route53 Hosted Zones and Records...")
            r53_resp = self.route53.list_hosted_zones()
            for hz in r53_resp.get('HostedZones', []):
                hz_id = hz.get('Id')
                records = []
                try:
                    rec_resp = self.route53.list_resource_record_sets(HostedZoneId=hz_id)
                    for r in rec_resp.get('ResourceRecordSets', []):
                        targets = []
                        if 'AliasTarget' in r:
                            targets.append(r['AliasTarget'].get('DNSName', ''))
                        for rr in r.get('ResourceRecords', []):
                            targets.append(rr.get('Value', ''))
                        records.append({
                            'Name': r.get('Name'),
                            'Type': r.get('Type'),
                            'Targets': targets
                        })
                except Exception as e:
                    logger.info(f"Error fetching records for {hz_id}: {e}")
                    
                self.global_data['Route53HostedZones'].append({
                    'Id': hz_id,
                    'Name': hz.get('Name'),
                    'CallerReference': hz.get('CallerReference'),
                    'PrivateZone': hz.get('Config', {}).get('PrivateZone'),
                    'Records': records
                })
        except Exception as e:
            logger.info(f"Error fetching Route53: {e}")

    def _fetch_s3(self):
        try:
            logger.info("Fetching S3 Buckets...")
            s3_resp = self.s3.list_buckets()
            for bucket in s3_resp.get('Buckets', []):
                self.global_data['S3Buckets'].append({
                    'Name': bucket.get('Name'),
                    'CreationDate': bucket.get('CreationDate').isoformat() if bucket.get('CreationDate') else None
                })
        except Exception as e:
            logger.info(f"Error fetching S3: {e}")
