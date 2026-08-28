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
            paginator = self.sns_client.get_paginator('list_topics')
            for page in paginator.paginate():
                for topic in page.get('Topics', []):
                    topic_arn = topic['TopicArn']
                    topic_name = topic_arn.split(':')[-1]
                    
                    self.add_node(topic_arn, 'SNS_TOPIC', topic_name, 'available', {
                        "TopicArn": topic_arn,
                        "Type": "SNS Topic"
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch SNS Topics: {e}")
