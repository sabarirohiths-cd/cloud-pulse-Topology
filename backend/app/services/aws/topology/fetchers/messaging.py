import logging
logger = logging.getLogger(__name__)

from ..core.base import BaseTopologyBuilder

class MessagingMixin(BaseTopologyBuilder):
    def _fetch_messaging_queues(self):
        logger.debug("Fetching SQS, MQ, MSK...")
        try:
            sqs_resp = self.sqs.list_queues()
            for q in sqs_resp.get('QueueUrls', []):
                self.raw_data['RegionalQueues'].append({'QueueUrl': q})
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            mq_resp = self.mq.list_brokers()
            for broker in mq_resp.get('BrokerSummaries', []):
                b_id = broker.get('BrokerId')
                b_det = self.mq.describe_broker(BrokerId=b_id)
                self.raw_data['AmazonMQBrokers'].append({
                    'SubnetIds': b_det.get('SubnetIds', []),
                    'BrokerName': b_det.get('BrokerName'),
                    'BrokerState': b_det.get('BrokerState'),
                    'EngineType': b_det.get('EngineType')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

        try:
            kafka_resp = self.kafka.list_clusters_v2()
            for cluster in kafka_resp.get('ClusterInfoList', []):
                subnets = []
                if 'Provisioned' in cluster:
                    subnets = cluster['Provisioned'].get('BrokerNodeGroupInfo', {}).get('ClientSubnets', [])
                elif 'Serverless' in cluster:
                    for vc in cluster['Serverless'].get('VpcConfigs', []):
                        subnets.extend(vc.get('SubnetIds', []))
                
                self.raw_data['MSKClusters'].append({
                    'SubnetIds': subnets,
                    'ClusterName': cluster.get('ClusterName'),
                    'State': cluster.get('State'),
                    'ClusterType': cluster.get('ClusterType')
                })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")

    def _fetch_opensearch(self):
        logger.debug("Fetching OpenSearch...")
        try:
            os_list = self.opensearch.list_domain_names()
            domain_names = [d.get('DomainName') for d in os_list.get('DomainNames', [])]
            if domain_names:
                for i in range(0, len(domain_names), 5):
                    chunk = domain_names[i:i+5]
                    os_resp = self.opensearch.describe_domain_names(DomainNames=chunk)
                    for domain in os_resp.get('DomainStatusList', []):
                        vpc_opts = domain.get('VPCOptions')
                        if vpc_opts:
                            self.raw_data['OpenSearchDomains'].append({
                                'SubnetIds': vpc_opts.get('SubnetIds', []),
                                'DomainName': domain.get('DomainName'),
                                'EngineVersion': domain.get('EngineVersion'),
                                'Created': domain.get('Created')
                            })
        except Exception as e:
            logger.warning(f"Error during AWS discovery: {e}")
