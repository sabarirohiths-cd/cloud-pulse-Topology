import dagre from '@dagrejs/dagre';

const nodeWidth = 250;
const nodeHeight = 75;

export const transformTopologyToGraph = (topologyJson) => {
  const nodes = [];
  const edges = [];
  
  if (!topologyJson || !Array.isArray(topologyJson)) return { nodes, edges };

  const addEdge = (source, target) => {
    edges.push({
      id: `e-${source}-${target}`,
      source,
      target,
      type: 'smoothstep',
      style: { stroke: '#94a3b8', strokeWidth: 2 },
      animated: true,
    });
  };

  topologyJson.forEach(vpc => {
    // 1. Create VPC Node
    const vpcId = vpc.Id || vpc.VpcId;
    nodes.push({
      id: vpcId,
      type: 'vpcNode',
      data: { label: `VPC: ${vpcId}`, type: 'VPC', ...vpc },
      position: { x: 0, y: 0 },
      sourcePosition: 'right',
      targetPosition: 'left'
    });

    // Extract VPC-level resources
    const vpcResourceKeys = [
      'LoadBalancers', 'RDSInstances', 'PeeringConnections', 'TransitGatewayAttachments', 
      'VpnGateways', 'VpnConnections', 'RegionalQueues', 'InternetGateways', 'RouteTables',
      'NetworkFirewalls'
    ];
    
    vpcResourceKeys.forEach(key => {
      const vpcResources = vpc[key] || [];
      vpcResources.forEach(res => {
        const resId = res.Id || res.InstanceId || res.DBInstanceIdentifier || res.InternetGatewayId || res.RouteTableId || res.FirewallId || res.Name || `res-${Math.random()}`;
        nodes.push({
          id: resId,
          type: 'resourceNode',
          data: { label: res.Name || res.FirewallName || resId, type: key.replace(/s$/, ''), ...res },
          position: { x: 0, y: 0 },
          sourcePosition: 'right',
          targetPosition: 'left'
        });
        addEdge(vpcId, resId);
      });
    });

    // 2. Loop Subnets
    const subnets = vpc.Subnets || [];
    subnets.forEach(subnet => {
      const subnetId = subnet.Id || subnet.SubnetId;
      nodes.push({
        id: subnetId,
        type: 'subnetNode',
        data: { label: `Subnet: ${subnetId}`, type: 'Subnet', ...subnet },
        position: { x: 0, y: 0 },
        sourcePosition: 'right',
        targetPosition: 'left'
      });
      addEdge(vpcId, subnetId);

      // 3. Extract Subnet-level resources
      const subnetResourceKeys = [
        'Instances', 'NatGateways', 'EKSClusters', 'ECSClusters', 'VpcEndpoints', 
        'LambdaFunctions', 'ElastiCacheNodes', 'EFSMountTargets', 'AutoScalingGroups', 
        'UnclassifiedENIs', 'AmazonMQBrokers', 'MSKClusters',
        'DocumentDBClusters', 'RedshiftClusters', 'SageMakerNotebooks', 'WorkSpaces',
        'FSxFileSystems', 'OpenSearchDomains', 'NetworkFirewallEndpoints', 'Route53ResolverEndpoints'
      ];
      
      subnetResourceKeys.forEach(key => {
        const subnetResources = subnet[key] || [];
        subnetResources.forEach(res => {
          const resId = res.Id || res.InstanceId || res.ClusterName || res.AutoScalingGroupName || res.FunctionName || res.DBClusterIdentifier || res.ClusterIdentifier || res.NotebookInstanceName || res.WorkspaceId || res.FileSystemId || res.DomainName || res.ResolverEndpointId || res.Name || `res-${Math.random()}`;
          nodes.push({
            id: resId,
            type: 'resourceNode',
            data: { label: res.Name || res.ClusterName || res.AutoScalingGroupName || res.DBClusterIdentifier || res.ClusterIdentifier || res.NotebookInstanceName || res.WorkspaceId || res.FileSystemId || res.DomainName || res.FirewallName || resId, type: key.replace(/s$/, ''), ...res },
            position: { x: 0, y: 0 },
            sourcePosition: 'right',
            targetPosition: 'left'
          });
          addEdge(subnetId, resId);
        });
      });
    });
  });

  return getLayoutedElements(nodes, edges);
};

export const getLayoutedElements = (nodes, edges, direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({ 
    rankdir: direction, 
    nodesep: 40,
    ranksep: 180
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    if (nodeWithPosition) {
      node.position = {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      };
    }
    return node;
  });

  return { nodes: layoutedNodes, edges };
};
