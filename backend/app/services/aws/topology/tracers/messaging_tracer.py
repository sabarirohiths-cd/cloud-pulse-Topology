import logging
from app.services.aws.topology.tracers.base_tracer import BaseTracer

logger = logging.getLogger(__name__)

class MessagingTracer(BaseTracer):
    def __init__(self, fetcher):
        super().__init__(fetcher)
        self.sns_client = getattr(self.fetcher, 'sns_client', self.session.client('sns', region_name=self.region))

    def trace(self):
        """
        Discovers global/regional messaging resources like SNS Topics.
        This provides nodes for other tracers (like CloudWatch Alarms) to link to.
        """
        logger.info("Tracing Messaging Resources (SNS)")
        try:
            # Only add nodes for SNS topics that have been explicitly triggered/referenced by other resources (e.g. Alarms)
            referenced_sns_arns = set()
            for e in self.fetcher.edges:
                if e['target'].startswith('arn:aws:sns:'):
                    referenced_sns_arns.add(e['target'])
                    
            for topic_arn in referenced_sns_arns:
                topic_name = topic_arn.split(':')[-1]
                
                self.add_node(topic_arn, 'SNS_TOPIC', topic_name, 'available', {
                    "TopicArn": topic_arn,
                    "Type": "SNS Topic"
                })
        except Exception as e:
            logger.warning(f"Failed to fetch SNS Topics: {e}")
