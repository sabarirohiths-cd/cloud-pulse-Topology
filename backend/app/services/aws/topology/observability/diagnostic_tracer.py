import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DiagnosticTracer:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.session = fetcher.session
        self.region = fetcher.region
        self.nodes = fetcher.nodes
        self.edges = fetcher.edges
        
        self.cloudwatch = self.session.client('cloudwatch', region_name=self.region)
        self.logs = self.session.client('logs', region_name=self.region)
        self.xray = self.session.client('xray', region_name=self.region)
        
    def _extract_alb_and_target_group(self, instance_id: str):
        tg_arn = None
        alb_arn = None
        
        for e in self.edges:
            if e['target'] == instance_id and e['relation'] == 'TARGETS':
                tg_arn = e['source']
                break
                
        if tg_arn:
            for e in self.edges:
                if e['target'] == tg_arn and e['relation'] == 'FORWARDS_TO':
                    alb_arn = e['source']
                    break
                    
        return alb_arn, tg_arn
        
    def trace(self, instance_id: str, options: list[str], lookback_minutes: int = 15):
        logger.info(f"Running on-demand observability diagnostics for {instance_id}: {options} (lookback: {lookback_minutes}m)")
        options = [opt.upper() for opt in options]
        
        alb_arn, tg_arn = self._extract_alb_and_target_group(instance_id)
        
        if 'METRICS' in options:
            self._handle_metrics(instance_id, alb_arn, tg_arn, lookback_minutes)
            
        if 'LOGS' in options:
            self._handle_logs(instance_id, lookback_minutes)
            
        if 'XRAY' in options:
            self._handle_xray(instance_id, lookback_minutes)
            
    def _handle_metrics(self, instance_id, alb_arn, tg_arn, lookback_minutes):
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)
        
        queries = []
        
        # 1. EC2 CPU
        queries.append({
            'Id': 'cpu',
            'MetricStat': {
                'Metric': {
                    'Namespace': 'AWS/EC2',
                    'MetricName': 'CPUUtilization',
                    'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}]
                },
                'Period': 300,
                'Stat': 'Maximum',
            },
            'ReturnData': True
        })
        
        # 2. ALB 5XX Errors
        if alb_arn and tg_arn:
            try:
                # ALB ARN: arn:aws:elasticloadbalancing:region:account:loadbalancer/app/name/id
                # Dimension: app/name/id
                alb_dim = "/".join(alb_arn.split(':')[-1].split('/')[1:])
                # TargetGroup ARN: arn:aws:elasticloadbalancing:region:account:targetgroup/name/id
                # Dimension: targetgroup/name/id
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
            except Exception as e:
                logger.warning(f"Failed to parse ALB/TG dimensions for metrics: {e}")
                
        try:
            resp = self.cloudwatch.get_metric_data(
                MetricDataQueries=queries,
                StartTime=start_time,
                EndTime=end_time
            )
            
            for res in resp.get('MetricDataResults', []):
                if res['Id'] == 'cpu' and res['Values']:
                    cpu = res['Values'][0]
                    if cpu > 90:
                        node = next((n for n in self.nodes if n['id'] == instance_id), None)
                        if node:
                            node['health_state'] = 'DEGRADED'
                            node['diagnostic'] = f'High CPU Utilization ({cpu:.1f}%)'
                            
                elif res['Id'] == 'errors5xx' and res['Values']:
                    errors = res['Values'][0]
                    if errors > 0:
                        node = next((n for n in self.nodes if n['id'] == tg_arn), None)
                        if node:
                            node['health_state'] = 'CRITICAL'
                            node['diagnostic'] = f'{int(errors)} HTTP 5XX server errors detected (last {lookback_minutes}m)'
                            
        except Exception as e:
            logger.warning(f"Failed to fetch CloudWatch metrics: {e}")

    def _run_logs_query(self, log_group_name: str, start_time: int, end_time: int):
        query = "fields @timestamp, @message | filter @message like /(?i)(error|exception|fatal|timeout)/ | sort @timestamp desc | limit 5"
        
        start_resp = self.logs.start_query(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            queryString=query
        )
        
        query_id = start_resp['queryId']
        
        # Poll for results (max 5 seconds)
        for _ in range(5):
            time.sleep(1)
            res = self.logs.get_query_results(queryId=query_id)
            if res['status'] == 'Complete':
                return res.get('results', [])
        return []

    def _handle_logs(self, instance_id, lookback_minutes):
        node = next((n for n in self.nodes if n['id'] == instance_id), None)
        if not node:
            return
            
        log_group_name = node.get('metadata', {}).get('CloudWatchLogGroup', f'/aws/ec2/{instance_id}')
        
        try:
            end_time = int(time.time())
            start_time = end_time - (lookback_minutes * 60)
            
            results = self._run_logs_query(log_group_name, start_time, end_time)
            
            # Smart Fallback: If 0 logs found and lookback < 24h, check last 24h
            is_fallback = False
            if not results and lookback_minutes < 1440:
                logger.info(f"0 error logs found in last {lookback_minutes}m. Triggering smart fallback to 24h (1440m).")
                start_time = end_time - (1440 * 60)
                results = self._run_logs_query(log_group_name, start_time, end_time)
                is_fallback = True
                
            if results:
                node['health_state'] = 'CRITICAL'
                fallback_str = " (24h fallback)" if is_fallback else ""
                node['diagnostic'] = f'Found {len(results)} error logs in {log_group_name}{fallback_str}'
                
                traces = []
                for row in results:
                    msg = next((f['value'] for f in row if f['field'] == '@message'), '')
                    if msg:
                        traces.append(msg)
                        
                if 'metadata' not in node:
                    node['metadata'] = {}
                node['metadata']['recent_stack_traces'] = traces
                
        except Exception as e:
            logger.warning(f"Failed to query CloudWatch Logs Insights for {log_group_name}: {e}")

    def _handle_xray(self, instance_id, lookback_minutes):
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=lookback_minutes)
            
            resp = self.xray.get_trace_summaries(
                StartTime=start_time,
                EndTime=end_time
            )
            
            all_summaries = resp.get('TraceSummaries', [])
            summaries = [s for s in all_summaries if s.get('HasFault', False) or s.get('Duration', 0) > 3]
            
            if summaries:
                node = next((n for n in self.nodes if n['id'] == instance_id), None)
                if node:
                    if node.get('health_state', 'HEALTHY') != 'CRITICAL':
                        node['health_state'] = 'DEGRADED'
                        node['diagnostic'] = f'Found {len(summaries)} faulty/slow X-Ray traces (last {lookback_minutes}m)'
        except Exception as e:
            logger.warning(f"Failed to fetch X-Ray traces: {e}")
