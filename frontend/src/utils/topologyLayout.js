import dagre from '@dagrejs/dagre';

const nodeWidth = 250;
const nodeHeight = 75;

export const transformTopologyToGraph = (topologyJson, viewRegion = 'ALL') => {
  const nodesMap = new Map();
  const edgesMap = new Map();
  
  if (!topologyJson || !topologyJson.Regions) {
    return { nodes: [], edges: [], globalResources: topologyJson?.GlobalResources || null };
  }

  // Helper to extract the correct AWS ID from resources since AWS naming is inconsistent
  const getResourceId = (resource, key) => {
    if (resource.Id) return resource.Id;
    
    // Explicit overrides for AWS naming inconsistencies
    const overrides = {
      'SecurityGroups': resource.GroupId,
      'DhcpOptions': resource.DhcpOptionsId,
      'ElasticIps': resource.AllocationId || resource.PublicIp,
      'GatewayLoadBalancers': resource.LoadBalancerArn,
      'MemoryDBClusters': resource.Name,
      'EMRClusters': resource.Id,
      'DirectoryServices': resource.DirectoryId,
      'AppRunnerVpcConnectors': resource.VpcConnectorArn,
      'GlueConnections': resource.Name,
      'BatchComputeEnvironments': resource.ComputeEnvironmentArn,
      'SecurityAndCompliance': `sec-comp-${Math.random()}`, // usually singleton per region
      'HybridConnectivity': resource.ConnectionId || resource.CoreNetworkId,
      'AutoScalingGroups': resource.AutoScalingGroupName || resource.AutoScalingGroupARN,
      'EKSClusters': resource.Name || resource.Arn,
      'ECSClusters': resource.ClusterName || resource.ClusterArn,
    };

    if (overrides[key]) return overrides[key];

    // Fallback heuristic: Try singularizing the key (e.g. RouteTables -> RouteTableId)
    const singularId = resource[`${key.slice(0, -1)}Id`];
    if (singularId) return singularId;
    
    // Try some common properties
    if (resource.Name) return resource.Name;
    if (resource.Arn) return resource.Arn;

    return `res-${Math.random()}`; // Absolute last resort
  };

  const getLabel = (resource, key) => {
    return resource.Name || resource.GroupName || resource.AutoScalingGroupName || resource.ClusterName || resource.DBInstanceIdentifier || resource.DBClusterIdentifier || resource.FunctionName || resource.CacheClusterId || resource.InstanceId || resource.GroupId || resource.LoadBalancerName || resource.DistributionId || resource.BucketName || 'Resource';
  };

  const addNode = (nodeObj) => {
    if (!nodesMap.has(nodeObj.id)) {
      nodesMap.set(nodeObj.id, nodeObj);
    }
  };

  const addEdge = (source, target) => {
    const edgeId = `e-${source}-${target}`;
    if (!edgesMap.has(edgeId)) {
      edgesMap.set(edgeId, {
        id: edgeId,
        source,
        target,
        type: 'smoothstep',
        style: { stroke: '#94a3b8', strokeWidth: 2 },
        animated: true,
      });
    }
  };

  let targetRegions = [];
  if (viewRegion === 'ALL') {
    targetRegions = Object.values(topologyJson.Regions);
  } else {
    targetRegions = topologyJson.Regions[viewRegion] ? [topologyJson.Regions[viewRegion]] : [];
  }

  targetRegions.forEach(vpcs => {
    vpcs.forEach(vpc => {
    // 1. Create VPC Node
    const vpcId = vpc.Id || vpc.VpcId;
    addNode({
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
      'VpnGateways', 'VpnConnections', 'RegionalQueues', 'InternetGateways',
      'NetworkFirewalls', 'EgressOnlyInternetGateways', 'CarrierGateways',
      'HybridConnectivity'
    ];
    
    const vpcConfigKeys = [
      'RouteTables', 'DhcpOptions', 'FlowLogs', 'SecurityAndCompliance', 
      'SecurityGroups', 'NetworkAcls', 'ElasticIps'
    ];

    const aggregatedConfig = {};
    let hasConfig = false;

    // 1a. Process actual VPC infrastructure resources
    vpcResourceKeys.forEach(key => {
      const vpcResources = vpc[key] || [];
      vpcResources.forEach(res => {
        const resId = getResourceId(res, key);
        
        if (res.IsExternal) {
          const extId = `external-target-${resId}`;
          addNode({
            id: extId,
            type: 'resourceNode',
            data: { label: 'External Region / Account', type: 'External', ...res },
            position: { x: 0, y: 0 },
            sourcePosition: 'right',
            targetPosition: 'left'
          });
          addEdge(vpcId, extId);
        } else {
          addNode({
            id: resId,
            type: 'resourceNode',
            data: { label: getLabel(res, key), type: key.replace(/s$/, ''), ...res },
            position: { x: 0, y: 0 },
            sourcePosition: 'right',
            targetPosition: 'left'
          });
          addEdge(vpcId, resId);
        }
      });
    });

    // 1b. Process and group VPC Configuration resources
    vpcConfigKeys.forEach(key => {
      const configResources = vpc[key] || [];
      if (configResources.length > 0) {
        aggregatedConfig[key] = configResources;
        hasConfig = true;
      }
    });

    if (hasConfig) {
      const configNodeId = `vpc-config-${vpcId}`;
      addNode({
        id: configNodeId,
        type: 'resourceNode',
        data: { 
          label: 'Network Configurations', 
          type: 'ConfigGroup', 
          ...aggregatedConfig 
        },
        position: { x: 0, y: 0 },
        sourcePosition: 'right',
        targetPosition: 'left'
      });
      addEdge(vpcId, configNodeId);
    }

    // 2. Loop Subnets
    const subnets = vpc.Subnets || [];
    subnets.forEach(subnet => {
      const subnetId = subnet.Id || subnet.SubnetId;
      addNode({
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
        'FSxFileSystems', 'OpenSearchDomains', 'NetworkFirewallEndpoints', 'Route53ResolverEndpoints',
        'NeptuneClusters', 'DirectoryServices', 'AppRunnerVpcConnectors', 'EMRClusters',
        'GlueConnections', 'GatewayLoadBalancers', 'GWLBEndpoints', 'MemoryDBClusters',
        'BatchComputeEnvironments', 'FlowLogs'
      ];
      
      subnetResourceKeys.forEach(key => {
        const subnetResources = subnet[key] || [];
        subnetResources.forEach(res => {
          const resId = getResourceId(res, key);
          addNode({
            id: resId,
            type: 'resourceNode',
            data: { label: getLabel(res, key), type: key.replace(/s$/, ''), ...res },
            position: { x: 0, y: 0 },
            sourcePosition: 'right',
            targetPosition: 'left'
          });
          addEdge(subnetId, resId);
        });
      });
    });
    });
  });

  const finalNodes = Array.from(nodesMap.values());
  const finalEdges = Array.from(edgesMap.values());

  const layouted = getLayoutedElements(finalNodes, finalEdges);
  return { ...layouted, globalResources: topologyJson.GlobalResources };
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
