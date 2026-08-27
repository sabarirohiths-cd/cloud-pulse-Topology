from .base_tracer import BaseTracer
import logging

logger = logging.getLogger(__name__)

class TrafficTracer(BaseTracer):
    def trace(self, vpc_id, target_ids, root_id):
        """
        Traces upstream traffic: Target Groups -> ALBs -> Route53
        target_ids: list of strings (can be instance IDs or IP addresses)
        root_id: the ID of the node to connect the target group to (usually the instance/service)
        """
        if not vpc_id or not target_ids:
            return

        target_groups = self.elbv2_client.describe_target_groups().get('TargetGroups', [])
        
        associated_tgs = []
        for tg in target_groups:
            if tg.get('VpcId') != vpc_id: continue
            
            tg_arn = tg['TargetGroupArn']
            try:
                health_response = self.elbv2_client.describe_target_health(TargetGroupArn=tg_arn)
                has_unhealthy = False
                match_found = False
                
                for target_health in health_response.get('TargetHealthDescriptions', []):
                    if target_health.get('TargetHealth', {}).get('State') == 'unhealthy':
                        has_unhealthy = True
                    target_id = target_health.get('Target', {}).get('Id')
                    
                    if target_id in target_ids:
                        match_found = True
                        
                if match_found:
                    associated_tgs.append(tg)
                    tg_name = tg.get('TargetGroupName')
                    
                    unhealthy_count = sum(1 for h in health_response.get('TargetHealthDescriptions', []) if h.get('TargetHealth', {}).get('State') == 'unhealthy')
                    tg_health = "CRITICAL" if has_unhealthy else "HEALTHY"
                    tg_diag = f"Health check failed ({unhealthy_count} unhealthy). Web process may be down." if has_unhealthy else None
                    
                    self.add_node(tg_arn, 'TARGET_GROUP', tg_name, 'active', {
                        "Protocol": tg.get('Protocol'),
                        "Port": tg.get('Port'),
                        "TargetType": tg.get('TargetType'),
                        "HealthCheckPath": tg.get('HealthCheckPath'),
                        "UnhealthyHostCount": unhealthy_count
                    }, health_state=tg_health, diagnostic=tg_diag)
                    self.add_edge(tg_arn, root_id, 'TARGETS')
                    
            except Exception as e:
                logger.warning(f"Failed to fetch health for TG {tg_arn}: {e}")
                
        # Trace ALBs
        lb_dns_names = []
        alb_arns = []
        for tg in associated_tgs:
            for lb_arn in tg.get('LoadBalancerArns', []):
                if lb_arn in alb_arns: continue
                alb_arns.append(lb_arn)
                
                lbs = self.elbv2_client.describe_load_balancers(LoadBalancerArns=[lb_arn]).get('LoadBalancers', [])
                if lbs:
                    lb = lbs[0]
                    lb_name = lb.get('LoadBalancerName')
                    dns_name = lb.get('DNSName')
                    lb_dns_names.append(dns_name.lower())
                    
                    self.add_node(lb_arn, 'ALB', lb_name, lb.get('State', {}).get('Code', 'active'), {
                        "DNSName": dns_name,
                        "Scheme": lb.get('Scheme'),
                        "Type": lb.get('Type'),
                        "VpcId": lb.get('VpcId')
                    })
                    self.add_edge(lb_arn, tg['TargetGroupArn'], 'FORWARDS_TO')
                    
                    # Add ALB Security Groups
                    for sg_id in lb.get('SecurityGroups', []):
                        self.add_node(sg_id, 'SECURITY_GROUP', sg_id, 'available', {
                            "Type": "Security Group",
                            "GroupId": sg_id
                        })
                        self.add_edge(sg_id, lb_arn, 'PROTECTS')
                    
        # Trace Route53
        if lb_dns_names:
            zones = self.route53_client.list_hosted_zones().get('HostedZones', [])
            for zone in zones:
                zone_id = zone['Id']
                records = self.route53_client.list_resource_record_sets(HostedZoneId=zone_id).get('ResourceRecordSets', [])
                for record in records:
                    if record['Type'] in ['A', 'CNAME']:
                        match_found = False
                        
                        for val in record.get('ResourceRecords', []):
                            if any(lb_dns in val['Value'].lower() for lb_dns in lb_dns_names):
                                match_found = True
                                break
                                
                        if not match_found and 'AliasTarget' in record:
                            dns_name = record['AliasTarget'].get('DNSName', '').lower()
                            if any(lb_dns in dns_name for lb_dns in lb_dns_names):
                                match_found = True
                                
                        if match_found:
                            rec_name = record['Name'].strip('.')
                            self.add_node(rec_name, 'ROUTE53', rec_name, 'active', {
                                "RecordType": record.get('Type'),
                                "TTL": record.get('TTL')
                            })
                            for arn in alb_arns:
                                self.add_edge(rec_name, arn, 'ROUTES_TO')
