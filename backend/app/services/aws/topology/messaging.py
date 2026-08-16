from .base import BaseTopologyBuilder

class MessagingMixin(BaseTopologyBuilder):
    def _fetch_messaging_queues(self):
        print("Fetching SQS, MQ, MSK...")
        subnet_map = self._get_subnet_map()
        
        try:
            sqs_resp = self.sqs.list_queues()
            for q in sqs_resp.get('QueueUrls', []):
                for vpc in self.vpcs.values():
                    vpc['RegionalQueues'].append({'QueueUrl': q})
        except Exception:
            pass

        try:
            mq_resp = self.mq.list_brokers()
            for broker in mq_resp.get('BrokerSummaries', []):
                b_id = broker.get('BrokerId')
                b_det = self.mq.describe_broker(BrokerId=b_id)
                info = {
                    'BrokerName': b_det.get('BrokerName'),
                    'BrokerState': b_det.get('BrokerState'),
                    'EngineType': b_det.get('EngineType')
                }
                for sid in b_det.get('SubnetIds', []):
                    if sid in subnet_map:
                        subnet_map[sid]['AmazonMQBrokers'].append(info)
        except Exception:
            pass

        try:
            kafka_resp = self.kafka.list_clusters_v2()
            for cluster in kafka_resp.get('ClusterInfoList', []):
                info = {
                    'ClusterName': cluster.get('ClusterName'),
                    'State': cluster.get('State'),
                    'ClusterType': cluster.get('ClusterType')
                }
                subnets = []
                if 'Provisioned' in cluster:
                    subnets = cluster['Provisioned'].get('BrokerNodeGroupInfo', {}).get('ClientSubnets', [])
                elif 'Serverless' in cluster:
                    for vc in cluster['Serverless'].get('VpcConfigs', []):
                        subnets.extend(vc.get('SubnetIds', []))
                for sid in subnets:
                    if sid in subnet_map:
                        subnet_map[sid]['MSKClusters'].append(info)
        except Exception:
            pass

    def _fetch_opensearch(self):
        print("Fetching OpenSearch...")
        subnet_map = self._get_subnet_map()
        try:
            os_list = self.opensearch.list_domain_names()
            domain_names = [d.get('DomainName') for d in os_list.get('DomainNames', [])]
            if domain_names:
                # We can fetch 5 domains per request, but let's loop to be safe for smaller amounts
                for i in range(0, len(domain_names), 5):
                    chunk = domain_names[i:i+5]
                    os_resp = self.opensearch.describe_domain_names(DomainNames=chunk)
                    for domain in os_resp.get('DomainStatusList', []):
                        vpc_opts = domain.get('VPCOptions')
                        if vpc_opts:
                            info = {
                                'DomainName': domain.get('DomainName'),
                                'EngineVersion': domain.get('EngineVersion'),
                                'Created': domain.get('Created')
                            }
                            for sid in vpc_opts.get('SubnetIds', []):
                                if sid in subnet_map:
                                    subnet_map[sid]['OpenSearchDomains'].append(info)
        except Exception:
            pass
