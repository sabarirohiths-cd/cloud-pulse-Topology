import logging
from app.services.aws.topology.tracers.base_tracer import BaseTracer

logger = logging.getLogger(__name__)

class ObservabilityTracer(BaseTracer):
    def __init__(self, fetcher):
        super().__init__(fetcher)
        self.cw_client = getattr(self.fetcher, 'cloudwatch_client', self.session.client('cloudwatch', region_name=self.region))

    def trace(self):
        """
        Discovers regional observability primitives like CloudWatch Alarms.
        """
        logger.info("Tracing Observability Resources (CloudWatch Alarms)")
        try:
            paginator = self.cw_client.get_paginator('describe_alarms')
            for page in paginator.paginate():
                for alarm in page.get('MetricAlarms', []):
                    alarm_arn = alarm['AlarmArn']
                    alarm_name = alarm['AlarmName']
                    state = alarm['StateValue'] # OK, ALARM, INSUFFICIENT_DATA
                    
                    health_state = "HEALTHY"
                    diagnostic = None
                    if state == 'ALARM':
                        health_state = "CRITICAL"
                        diagnostic = f"Alarm {alarm_name} is in ALARM state: {alarm.get('StateReason', '')}"
                    elif state == 'INSUFFICIENT_DATA':
                        health_state = "UNKNOWN"
                        
                    self.add_node(alarm_arn, 'CLOUDWATCH_ALARM', alarm_name, state.lower(), {
                        "MetricName": alarm.get('MetricName'),
                        "Namespace": alarm.get('Namespace'),
                        "Statistic": alarm.get('Statistic'),
                        "Threshold": alarm.get('Threshold'),
                        "Type": "CloudWatch Alarm"
                    }, health_state=health_state, diagnostic=diagnostic)
                    
                    # Connect to SNS topics if triggered
                    for action in alarm.get('AlarmActions', []):
                        if action.startswith('arn:aws:sns:'):
                            self.add_edge(alarm_arn, action, 'TRIGGERS')
                            
                    # Link Alarm to the actual infrastructure it monitors
                    for dim in alarm.get('Dimensions', []):
                        val = dim['Value']
                        # If the dimension value matches our root EC2 instance or any other discovered node (like RDS/ALB)
                        if val == self.fetcher.resource_id or any(n['id'] == val for n in self.fetcher.nodes):
                            self.add_edge(alarm_arn, val, 'MONITORS')
                            
        except Exception as e:
            logger.warning(f"Failed to fetch CloudWatch Alarms: {e}")
