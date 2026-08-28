import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .base_layer import DiagnosticLayer

logger = logging.getLogger(__name__)

class ApplicationLayer(DiagnosticLayer):
    @property
    def layer_name(self) -> str:
        return "application"

    def _extract_alb_and_target_group(self, instance_id: str, fetcher: Any):
        tg_arn = None
        alb_arn = None
        
        for e in fetcher.edges:
            if e['target'] == instance_id and e['relation'] == 'TARGETS':
                tg_arn = e['source']
                break
                
        if tg_arn:
            for e in fetcher.edges:
                if e['target'] == tg_arn and e['relation'] == 'FORWARDS_TO':
                    alb_arn = e['source']
                    break
                    
        return alb_arn, tg_arn

    def analyze(self, instance_id: str, fetcher: Any, options: List[str], lookback_minutes: int) -> Dict[str, Any]:
        logger.info(f"Running Application Layer analysis for {instance_id}")
        
        node = next((n for n in fetcher.nodes if n['id'] == instance_id), None)
        if not node:
            return {"status": "UNKNOWN", "summary": "Node not found"}
            
        status = "HEALTHY"
        issues = []
        details = {
            "metrics": {},
            "logs": {},
            "xray": {}
        }
        
        # 1. Metrics
        if 'METRICS' in options:
            metrics_res = self._check_metrics(instance_id, fetcher, lookback_minutes)
            details["metrics"] = metrics_res
            if metrics_res.get("issues"):
                issues.extend(metrics_res["issues"])
                status = "CRITICAL" if metrics_res.get("status") == "CRITICAL" else ("DEGRADED" if status != "CRITICAL" else status)
                
        # 2. Logs
        if 'LOGS' in options:
            logs_res = self._check_logs(instance_id, fetcher, lookback_minutes)
            details["logs"] = logs_res
            if logs_res.get("issues"):
                issues.extend(logs_res["issues"])
                status = "CRITICAL"
                
        # 3. X-Ray
        if 'XRAY' in options:
            xray_res = self._check_xray(instance_id, fetcher, lookback_minutes)
            details["xray"] = xray_res
            if xray_res.get("issues"):
                issues.extend(xray_res["issues"])
                status = "DEGRADED" if status != "CRITICAL" else status
                
        summary = "Application telemetry looks healthy."
        if issues:
            summary = f"Detected {len(issues)} application issues: {'; '.join(issues[:2])}" + ("..." if len(issues) > 2 else "")
            
        return {
            "status": status,
            "summary": summary,
            "details": details
        }
        
    def _check_metrics(self, instance_id, fetcher, lookback_minutes):
        cloudwatch = fetcher.session.client('cloudwatch', region_name=fetcher.region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)
        
        alb_arn, tg_arn = self._extract_alb_and_target_group(instance_id, fetcher)
        
        # New: extract RDS and EBS IDs from topology edges
        rds_ids = [e['target'] for e in fetcher.edges if e['source'] == instance_id and e['relation'] == 'QUERIES']
        ebs_ids = [e['target'] for e in fetcher.edges if e['source'] == instance_id and e['relation'] == 'MOUNTS']
        
        node = next((n for n in fetcher.nodes if n['id'] == instance_id), None)
        node_type = node.get('type', 'EC2') if node else 'EC2'
        
        # Determine root compute metric parameters
        metric_namespace = 'AWS/EC2'
        dim_name = 'InstanceId'
        metric_name = 'CPUUtilization'
        
        if node_type == 'ECS':
            metric_namespace = 'AWS/ECS'
            dim_name = 'ServiceName'
        elif node_type == 'LAMBDA':
            metric_namespace = 'AWS/Lambda'
            dim_name = 'FunctionName'
            metric_name = 'Errors' # Lambda doesn't have CPUUtilization
            
        queries = []
        # Root Compute Metric
        queries.append({
            'Id': 'cpu',
            'MetricStat': {
                'Metric': {
                    'Namespace': metric_namespace,
                    'MetricName': metric_name,
                    'Dimensions': [{'Name': dim_name, 'Value': instance_id}]
                },
                'Period': 300,
                'Stat': 'Maximum',
            },
            'ReturnData': True
        })
        
        # ALB Metrics
        if alb_arn and tg_arn:
            try:
                alb_dim = "/".join(alb_arn.split(':')[-1].split('/')[1:])
                tg_dim = "/".join(tg_arn.split(':')[-1].split('/')[1:])
                
                queries.append({
                    'Id': 'errors5xx',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/ApplicationELB',
                            'MetricName': 'HTTPCode_Target_5XX_Count',
                            'Dimensions': [
                                {'Name': 'TargetGroup', 'Value': tg_dim},
                                {'Name': 'LoadBalancer', 'Value': alb_dim}
                            ]
                        },
                        'Period': 300,
                        'Stat': 'Sum',
                    },
                    'ReturnData': True
                })
                
                queries.append({
                    'Id': 'alblatency',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/ApplicationELB',
                            'MetricName': 'TargetResponseTime',
                            'Dimensions': [
                                {'Name': 'TargetGroup', 'Value': tg_dim},
                                {'Name': 'LoadBalancer', 'Value': alb_dim}
                            ]
                        },
                        'Period': 300,
                        'Stat': 'Average',
                    },
                    'ReturnData': True
                })
            except Exception as e:
                logger.warning(f"Failed to parse ALB/TG dimensions: {e}")
                
        # RDS Metrics
        for i, db_id in enumerate(rds_ids):
            # AWS metric DBInstanceIdentifier expects the plain string name for RDS, usually the node ID is just the name.
            # E.g. db-xyz... Wait, if node_id in topology is db-xyz, or topology-test-db, we'll use that.
            clean_db_id = db_id.split(':')[-1] if 'arn:' in db_id else db_id
            
            queries.append({
                'Id': f'rdscpu_{i}',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': 'CPUUtilization',
                        'Dimensions': [{'Name': 'DBInstanceIdentifier', 'Value': clean_db_id}]
                    },
                    'Period': 300,
                    'Stat': 'Maximum',
                },
                'ReturnData': True
            })
            queries.append({
                'Id': f'rdsconn_{i}',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': 'DatabaseConnections',
                        'Dimensions': [{'Name': 'DBInstanceIdentifier', 'Value': clean_db_id}]
                    },
                    'Period': 300,
                    'Stat': 'Maximum',
                },
                'ReturnData': True
            })

        # EBS Metrics
        for i, vol_id in enumerate(ebs_ids):
            queries.append({
                'Id': f'ebsqueue_{i}',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/EBS',
                        'MetricName': 'VolumeQueueLength',
                        'Dimensions': [{'Name': 'VolumeId', 'Value': vol_id}]
                    },
                    'Period': 300,
                    'Stat': 'Maximum',
                },
                'ReturnData': True
            })
                
        issues = []
        status = "HEALTHY"
        cpu_val = 0
        err_val = 0
        
        multi_tier_metrics = {}
        
        try:
            resp = cloudwatch.get_metric_data(
                MetricDataQueries=queries,
                StartTime=start_time,
                EndTime=end_time
            )
            
            for res in resp.get('MetricDataResults', []):
                val = res['Values'][0] if res['Values'] else None
                if val is None:
                    continue
                    
                multi_tier_metrics[res['Id']] = val
                
                if res['Id'] == 'cpu':
                    cpu_val = val
                    if cpu_val > 90:
                        issues.append(f"High EC2 CPU Utilization ({cpu_val:.1f}%)")
                        status = "DEGRADED"
                elif res['Id'] == 'errors5xx':
                    err_val = val
                    if err_val > 0:
                        issues.append(f"{int(err_val)} HTTP 5XX server errors detected via ALB")
                        status = "CRITICAL"
                elif res['Id'] == 'alblatency':
                    if val > 2.0: # seconds
                        issues.append(f"High ALB Target Latency ({val:.2f}s)")
                        status = "DEGRADED"
                elif res['Id'].startswith('rdscpu_'):
                    if val > 80:
                        issues.append(f"High RDS CPU Utilization ({val:.1f}%)")
                        status = "DEGRADED"
                elif res['Id'].startswith('rdsconn_'):
                    if val > 1000:
                        issues.append(f"High RDS Connections ({int(val)})")
                        status = "DEGRADED"
                elif res['Id'].startswith('ebsqueue_'):
                    if val > 10:
                        issues.append(f"High EBS Volume Queue Length ({val:.1f})")
                        status = "DEGRADED"
                        
        except Exception as e:
            logger.warning(f"Failed to fetch CloudWatch metrics: {e}")
            
        return {
            "status": status,
            "issues": issues,
            "cpu_max": cpu_val,
            "errors_5xx": err_val,
            "multi_tier": multi_tier_metrics
        }

    def _check_logs(self, instance_id, fetcher, lookback_minutes):
        logs = fetcher.session.client('logs', region_name=fetcher.region)
        issues = []
        traces = []
        
        # 1. Dynamic Log Group Discovery & 2. Stream Matching
        discovered_log_groups = []
        
        node = next((n for n in fetcher.nodes if n['id'] == instance_id), None)
        node_type = node.get('type', 'EC2') if node else 'EC2'
        log_prefix = f'/aws/{node_type.lower()}/'
        
        try:
            paginator = logs.get_paginator('describe_log_groups')
            # Filter by prefix to narrow down search space for efficiency
            for page in paginator.paginate(logGroupNamePrefix=log_prefix):
                for lg in page.get('logGroups', []):
                    lg_name = lg['logGroupName']
                    # Check if stream matching instance_id exists in this log group
                    try:
                        stream_resp = logs.describe_log_streams(
                            logGroupName=lg_name,
                            logStreamNamePrefix=instance_id,
                            limit=1
                        )
                        if stream_resp.get('logStreams'):
                            discovered_log_groups.append(lg_name)
                    except Exception as e:
                        logger.debug(f"Skipping streams for {lg_name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to describe log groups dynamically: {e}")

        # 3. Graceful Fallback
        if not discovered_log_groups:
            issues.append(f"No log groups dynamically discovered containing streams for {instance_id}.")
            return {
                "issues": issues,
                "traces": [],
                "log_group": "None"
            }
            
        if len(discovered_log_groups) > 1:
            issues.append(f"Multiple log groups found for {instance_id}. Using the first one: {discovered_log_groups[0]}")
            
        log_group_name = discovered_log_groups[0]
        
        end_time = int(time.time())
        start_time = end_time - (lookback_minutes * 60)
        
        query = "fields @timestamp, @message | filter @message like /(?i)(error|exception|fatal|timeout|NullReferenceException|OOM)/ | sort @timestamp desc | limit 5"
        
        try:
            start_resp = logs.start_query(
                logGroupName=log_group_name,
                startTime=start_time,
                endTime=end_time,
                queryString=query
            )
            
            query_id = start_resp['queryId']
            results = []
            
            for _ in range(5):
                time.sleep(1)
                res = logs.get_query_results(queryId=query_id)
                if res['status'] == 'Complete':
                    results = res.get('results', [])
                    break
                    
            if not results and lookback_minutes < 1440:
                # smart fallback
                start_time = end_time - (1440 * 60)
                start_resp = logs.start_query(
                    logGroupName=log_group_name,
                    startTime=start_time,
                    endTime=end_time,
                    queryString=query
                )
                query_id = start_resp['queryId']
                for _ in range(5):
                    time.sleep(1)
                    res = logs.get_query_results(queryId=query_id)
                    if res['status'] == 'Complete':
                        results = res.get('results', [])
                        break
                        
            if results:
                issues.append(f"Found {len(results)} error logs in {log_group_name}")
                for row in results:
                    msg = next((f['value'] for f in row if f['field'] == '@message'), '')
                    if msg:
                        traces.append(msg)
                        
        except Exception as e:
            logger.warning(f"Failed to query CloudWatch Logs Insights: {e}")
            issues.append(f"Failed to query CloudWatch Logs Insights: {str(e)}")
            
        return {
            "issues": issues,
            "traces": traces,
            "log_group": log_group_name
        }

    def _check_xray(self, instance_id, fetcher, lookback_minutes):
        xray = fetcher.session.client('xray', region_name=fetcher.region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)
        
        issues = []
        faulty_traces = 0
        
        try:
            resp = xray.get_trace_summaries(
                StartTime=start_time,
                EndTime=end_time
            )
            
            all_summaries = resp.get('TraceSummaries', [])
            summaries = [s for s in all_summaries if s.get('HasFault', False) or s.get('Duration', 0) > 3]
            
            if summaries:
                faulty_traces = len(summaries)
                issues.append(f"Found {faulty_traces} faulty/slow X-Ray traces")
                
        except Exception as e:
            logger.warning(f"Failed to fetch X-Ray traces: {e}")
            
        return {
            "issues": issues,
            "faulty_trace_count": faulty_traces
        }
