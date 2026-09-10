import logging
from app.services.aws.topology.tracers.network_tracer import NetworkTracer
from app.services.aws.topology.tracers.traffic_tracer import TrafficTracer
from app.services.aws.topology.tracers.storage_tracer import StorageTracer
from app.services.aws.topology.tracers.database_tracer import DatabaseTracer
from app.services.aws.topology.tracers.iam_tracer import IAMTracer
from app.services.aws.topology.tracers.security_tracer import SecurityTracer
from app.services.aws.topology.tracers.xray_tracer import XRayTracer
from app.services.aws.topology.tracers.messaging_tracer import MessagingTracer
from app.services.aws.topology.tracers.observability_tracer import ObservabilityTracer
from app.services.aws.topology.tracers.cluster_tracer import ClusterTracer
from app.services.aws.topology.observability.diagnostic_tracer import DiagnosticTracer
import concurrent.futures

logger = logging.getLogger(__name__)

class EC2FlowFetcher:
    def __init__(self, session, region: str, resource_id: str, observability_options: list[str] = None, lookback_minutes: int = 15):
        self.session = session
        self.region = region
        self.resource_id = resource_id
        self.observability_options = observability_options or []
        self.lookback_minutes = lookback_minutes
        
        self.ec2_client = self.session.client('ec2', region_name=self.region)
        self.elbv2_client = self.session.client('elbv2', region_name=self.region)
        self.route53_client = self.session.client('route53', region_name=self.region)
        self.rds_client = self.session.client('rds', region_name=self.region)
        self.autoscaling_client = self.session.client('autoscaling', region_name=self.region)
        self.elasticache_client = self.session.client('elasticache', region_name=self.region)
        
        self.nodes = []
        self.edges = []
        self.warnings = []
        
    def _add_node(self, node_id, node_type, label, status, metadata=None, health_state="HEALTHY", diagnostic=None):
        if metadata is None:
            metadata = {}
        if 'Region' not in metadata:
            metadata['Region'] = self.region if node_type != 'IAM_ROLE' else 'global'
            
        existing_node = next((n for n in self.nodes if n['id'] == node_id), None)
        if existing_node:
            existing_node['metadata'].update(metadata)
            if health_state != "HEALTHY":
                existing_node['health_state'] = health_state
            if diagnostic:
                existing_node['diagnostic'] = diagnostic
            if existing_node['label'] == node_id and label != node_id:
                existing_node['label'] = label
        else:
            self.nodes.append({
                "id": node_id,
                "type": node_type,
                "label": label,
                "status": status,
                "metadata": metadata,
                "health_state": health_state,
                "diagnostic": diagnostic
            })
            
    def _add_edge(self, source, target, relation, health_state="HEALTHY", diagnostic=None):
        if not any(e['source'] == source and e['target'] == target and e['relation'] == relation for e in self.edges):
            self.edges.append({
                "source": source,
                "target": target,
                "relation": relation,
                "health_state": health_state,
                "diagnostic": diagnostic
            })

    def fetch(self):
        logger.info(f"Tracing EC2 Flow for instance {self.resource_id} using modular tracers")
        
        # 1. Fetch EC2 Instance
        response = self.ec2_client.describe_instances(InstanceIds=[self.resource_id])
        if not response['Reservations'] or not response['Reservations'][0]['Instances']:
            raise ValueError(f"EC2 Instance {self.resource_id} not found.")
            
        instance = response['Reservations'][0]['Instances'][0]
        state = instance.get('State', {}).get('Name', 'unknown')
        private_ip = instance.get('PrivateIpAddress')
        vpc_id = instance.get('VpcId')
        subnet_id = instance.get('SubnetId')
        
        # Extract Name tag for proper labeling
        ec2_tags = {t['Key']: t['Value'] for t in instance.get('Tags', [])}
        node_label = ec2_tags.get('Name') or self.resource_id
        
        sg_ids = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]
        
        ec2_health = "HEALTHY"
        ec2_diag = None
        status_checks = None

        if state != 'running':
            ec2_health = "STOPPED" if state in ['stopped', 'terminated'] else "OFFLINE"
            ec2_diag = f"Instance is {state}."
        else:
            try:
                paginator = self.ec2_client.get_paginator('describe_instance_status')
                status_resp = None
                for page in paginator.paginate(InstanceIds=[self.resource_id], IncludeAllInstances=True):
                    if page.get('InstanceStatuses'):
                        status_resp = page
                        break
                
                if status_resp and status_resp.get('InstanceStatuses'):
                    st = status_resp['InstanceStatuses'][0]
                    sys_st = st.get('SystemStatus', {}).get('Status')
                    inst_st = st.get('InstanceStatus', {}).get('Status')
                    ebs_st = st.get('AttachedEbsStatus', {}).get('Status', 'ok') # default to ok if not present
                    
                    status_checks = {
                        "system_status": sys_st,
                        "instance_status": inst_st,
                        "ebs_status": ebs_st,
                        "summary": ""
                    }
                    
                    failed_checks = 0
                    if sys_st != 'ok': failed_checks += 1
                    if inst_st != 'ok': failed_checks += 1
                    if ebs_st != 'ok' and ebs_st != 'not-applicable': failed_checks += 1
                    
                    passed = 3 - failed_checks
                    status_checks["summary"] = f"{passed}/3 checks passed"

                    if sys_st != 'ok':
                        ec2_health = "CRITICAL"
                        ec2_diag = f"System status check failed ({sys_st}) - AWS hardware degradation."
                    elif inst_st != 'ok':
                        ec2_health = "UNHEALTHY"
                        ec2_diag = f"Instance status check failed ({inst_st}) - OS/Kernel configuration issue."
                    else:
                        ec2_health = "HEALTHY"
            except Exception as e:
                logger.warning(f"Failed to fetch EC2 status: {e}")
            
        # Network Interfaces (ENI) & Elastic IPs
        enis = []
        for eni in instance.get('NetworkInterfaces', []):
            eni_info = {"NetworkInterfaceId": eni.get('NetworkInterfaceId')}
            if eni.get('Association', {}).get('PublicIp'):
                eni_info['ElasticIp'] = eni['Association']['PublicIp']
            enis.append(eni_info)
            
        node_metadata = {
            "InstanceType": instance.get('InstanceType'),
            "PrivateIpAddress": private_ip,
            "PublicIpAddress": instance.get('PublicIpAddress'),
            "VpcId": vpc_id,
            "SubnetId": subnet_id,
            "NetworkInterfaces": enis
        }
        if status_checks:
            node_metadata["status_checks"] = status_checks

        self._add_node(self.resource_id, 'EC2', node_label, state, node_metadata, health_state=ec2_health, diagnostic=ec2_diag)
        
        # IAM Role
        iam_profile_arn = instance.get('IamInstanceProfile', {}).get('Arn')
        IAMTracer(self).trace(iam_profile_arn, self.resource_id, tags=ec2_tags)

        asg_name = ec2_tags.get('aws:autoscaling:groupName')
        if asg_name:
            try:
                paginator = self.autoscaling_client.get_paginator('describe_auto_scaling_groups')
                for page in paginator.paginate(AutoScalingGroupNames=[asg_name]):
                    for asg in page.get('AutoScalingGroups', []):
                        asg_health = "HEALTHY"
                        asg_diag = None
                        for asg_inst in asg.get('Instances', []):
                            if asg_inst['InstanceId'] == self.resource_id:
                                if 'Terminating:Wait' in asg_inst['LifecycleState'] or asg_inst['HealthStatus'] == 'Unhealthy':
                                    ec2_node = next((n for n in self.nodes if n['id'] == self.resource_id), None)
                                    if ec2_node:
                                        ec2_node['health_state'] = "CRITICAL"
                                        ec2_node['diagnostic'] = "Instance is being terminated by ASG health checks."
                                    asg_health = "CRITICAL"
                                    asg_diag = f"Instance {self.resource_id} is unhealthy/terminating."
                                break
                    self._add_node(asg_name, 'ASG', asg_name, 'active', {
                        "DesiredCapacity": asg.get('DesiredCapacity'),
                        "MinSize": asg.get('MinSize'),
                        "MaxSize": asg.get('MaxSize')
                    }, health_state=asg_health, diagnostic=asg_diag)
                    self._add_edge(asg_name, self.resource_id, 'MANAGES')
            except Exception as e:
                logger.warning(f"Failed to describe ASG {asg_name}: {e}")
                
        for sg_id in sg_ids:
            # We don't have SG names right now without calling describe_sgs, so just use ID
            self._add_node(sg_id, 'SECURITY_GROUP', sg_id, 'available', {"Type": "Security Group", "GroupId": sg_id})
            self._add_edge(sg_id, self.resource_id, 'PROTECTS')

        # === 2. Trigger Modular Tracers (Concurrently) ===
        # Instantiate tracers in the main thread to avoid boto3 session locking during client creation
        network_tracer = NetworkTracer(self)
        traffic_tracer = TrafficTracer(self)
        storage_tracer = StorageTracer(self)
        database_tracer = DatabaseTracer(self)
        xray_tracer = XRayTracer(self)
        observability_tracer = ObservabilityTracer(self)
        messaging_tracer = MessagingTracer(self)
        cluster_tracer = ClusterTracer(self)

        def trace_network():
            network_tracer.trace(vpc_id, [subnet_id] if subnet_id else [], self.resource_id)
            
        def trace_traffic():
            traffic_tracer.trace(vpc_id, [self.resource_id, private_ip], self.resource_id)
            
        def trace_storage():
            storage_tracer.trace(instance.get('BlockDeviceMappings', []), self.resource_id)
            
        def trace_database():
            database_tracer.trace(vpc_id, sg_ids, self.resource_id, root_tags=ec2_tags, root_name=node_label)
            
        def trace_xray():
            xray_tracer.trace(self.lookback_minutes)
            
        def trace_observability():
            observability_tracer.trace()
            
        def trace_messaging():
            messaging_tracer.trace()
            
        def trace_clusters():
            cluster_tracer.trace(ec2_tags, self.resource_id)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(trace_network),
                executor.submit(trace_traffic),
                executor.submit(trace_storage),
                executor.submit(trace_database),
                executor.submit(trace_xray),
                executor.submit(trace_observability),
                executor.submit(trace_messaging),
                executor.submit(trace_clusters)
            ]
            concurrent.futures.wait(futures)
            
        # Check for exceptions in futures
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error in concurrent tracer: {e}")
        
        # === 3. Deep Tracing for all Discovered Security Groups ===
        # (Must run after Database/Traffic tracers because they discover SGs)
        all_sgs = [n['id'] for n in self.nodes if n['type'] == 'SECURITY_GROUP']
        if all_sgs:
            SecurityTracer(self).trace(all_sgs)
            
        # === 6. Observability Diagnostics (On-Demand) ===
        if self.observability_options:
            DiagnosticTracer(self).trace(self.resource_id, self.observability_options, self.lookback_minutes)
        
        return {
            "compute_id": self.resource_id,
            "nodes": self.nodes,
            "edges": self.edges,
            "warnings": self.warnings
        }
