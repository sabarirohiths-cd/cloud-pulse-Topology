export const getResourceId = (resource, key) => {
  if (!resource) return `res-${Math.random()}`;
  if (resource.Id) return resource.Id;
  const overrides = {
    'RDSInstances': resource.DBInstanceIdentifier || resource.DBClusterIdentifier,
    'ElastiCacheNodes': resource.CacheClusterId,
    'DocumentDBClusters': resource.DBClusterIdentifier,
    'RedshiftClusters': resource.ClusterIdentifier,
    'NeptuneClusters': resource.DBClusterIdentifier,
    'SecurityGroups': resource.GroupId,
    'DhcpOptions': resource.DhcpOptionsId,
    'ElasticIps': resource.AllocationId || resource.PublicIp,
    'LoadBalancers': resource.LoadBalancerName,
    'TargetGroups': resource.TargetGroupName,
    'GatewayLoadBalancers': resource.LoadBalancerArn,
    'MemoryDBClusters': resource.Name,
    'EMRClusters': resource.Id,
    'DirectoryServices': resource.DirectoryId,
    'AppRunnerVpcConnectors': resource.VpcConnectorArn,
    'GlueConnections': resource.Name,
    'BatchComputeEnvironments': resource.ComputeEnvironmentArn,
    'SecurityAndCompliance': `sec-comp-${resource.GuardDutyStatus || 'none'}`,
    'HybridConnectivity': resource.ConnectionId || resource.CoreNetworkId,
    'AutoScalingGroups': resource.AutoScalingGroupName || resource.AutoScalingGroupARN,
    'EKSClusters': resource.Name || resource.Arn,
    'ECSClusters': resource.ClusterName || resource.ClusterArn,
  };
  
  if (overrides[key]) return overrides[key];
  
  const singularId = resource[`${key.slice(0, -1)}Id`];
  if (singularId) return singularId;
  
  if (resource.Name) return resource.Name;
  if (resource.Arn) return resource.Arn;
  
  return `res-${Math.random()}`;
};

export const getResourceLabel = (resource, key) => {
  if (!resource) return 'Unknown Resource';
  return resource.Name || 
         resource.GroupName || 
         resource.AutoScalingGroupName || 
         resource.ClusterName || 
         resource.DBInstanceIdentifier || 
         resource.DBClusterIdentifier || 
         resource.FunctionName || 
         resource.CacheClusterId || 
         resource.InstanceId || 
         resource.GroupId || 
         resource.RouteTableId || 
         resource.LoadBalancerName || 
         resource.DistributionId || 
         resource.BucketName || 
         getResourceId(resource, key) ||
         'Resource';
};

export const RESOURCE_CATEGORIES = {
  vpcConfigKeys: [
    'RouteTables', 'InternetGateways', 'NetworkAcls', 'SecurityGroups',
    'DhcpOptions', 'FlowLogs', 'ElasticIps'
  ],
  vpcResourceKeys: [
    'LoadBalancers', 'PeeringConnections', 'TransitGatewayAttachments',
    'VpnGateways', 'VpnConnections', 'NetworkFirewalls',
    'EgressOnlyInternetGateways', 'CarrierGateways', 'HybridConnectivity'
  ],
  vpcDataKeys: [
    'RDSInstances', 'ElastiCacheNodes', 'RegionalQueues', 'RedshiftClusters', 
    'DocumentDBClusters', 'MemoryDBClusters', 'OpenSearchDomains', 
    'NeptuneClusters', 'AmazonMQBrokers', 'MSKClusters'
  ],
  subnetEdgeKeys: [
    'NatGateways', 'VpcEndpoints', 'NetworkFirewallEndpoints', 'Route53ResolverEndpoints', 'GatewayLoadBalancers', 'GWLBEndpoints'
  ],
  subnetComputeKeys: [
    'Instances', 'EKSClusters', 'ECSClusters', 'LambdaFunctions', 'AutoScalingGroups', 'BatchComputeEnvironments', 'WorkSpaces', 'AppRunnerVpcConnectors', 'EMRClusters'
  ],
  subnetDataKeys: [
    'ElastiCacheNodes', 'DocumentDBClusters', 'RedshiftClusters', 'SageMakerNotebooks', 'FSxFileSystems', 'OpenSearchDomains', 'NeptuneClusters', 'DirectoryServices', 'GlueConnections', 'MemoryDBClusters', 'AmazonMQBrokers', 'MSKClusters'
  ]
};
