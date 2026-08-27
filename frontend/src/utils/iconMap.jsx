import React from 'react';
import { 
  Server, Database, Shield, Lock, Network, Cloud, 
  Box, Zap, Activity, Globe, HardDrive, Key, Layers
} from 'lucide-react';

// Tailwind Themes to preserve explicit class strings for PurgeCSS
const themes = {
  computeGreen: { text: 'text-green-400', border: 'hover:border-green-500/50', borderStatic: 'border-green-500/30' },
  computeEmerald: { text: 'text-emerald-400', border: 'hover:border-emerald-500/50', borderStatic: 'border-emerald-500/30' },
  dbSky: { text: 'text-sky-400', border: 'hover:border-sky-500/50', borderStatic: 'border-sky-500/30' },
  storageYellow: { text: 'text-yellow-400', border: 'hover:border-yellow-500/50', borderStatic: 'border-yellow-500/30' },
  mlOrange: { text: 'text-orange-400', border: 'hover:border-orange-500/50', borderStatic: 'border-orange-500/30' },
  secRed: { text: 'text-red-400', border: 'hover:border-red-500/50', borderStatic: 'border-red-500/30' },
  secLightRed: { text: 'text-red-300', border: 'hover:border-red-400/50', borderStatic: 'border-red-400/30' },
  iamPink: { text: 'text-pink-400', border: 'hover:border-pink-500/50', borderStatic: 'border-pink-500/30' },
  netCyan: { text: 'text-cyan-400', border: 'hover:border-cyan-500/50', borderStatic: 'border-cyan-500/30' },
  netLightCyan: { text: 'text-cyan-300', border: 'hover:border-cyan-400/50', borderStatic: 'border-cyan-400/30' },
  vpcPurple: { text: 'text-purple-400', border: 'hover:border-purple-500/50', borderStatic: 'border-purple-500/30' },
  lbIndigo: { text: 'text-indigo-400', border: 'hover:border-indigo-500/50', borderStatic: 'border-indigo-500/30' },
  miscLightSky: { text: 'text-sky-300', border: 'hover:border-sky-400/50', borderStatic: 'border-sky-400/30' },
  defaultGray: { text: 'text-gray-400', border: 'hover:border-gray-500/50', borderStatic: 'border-gray-500/30' },
  ebsPurple: { text: 'text-purple-400', border: 'hover:border-purple-500/50', borderStatic: 'border-purple-500/30' },
  iamYellow: { text: 'text-yellow-400', border: 'hover:border-yellow-500/50', borderStatic: 'border-yellow-500/30' },
  asgOrange: { text: 'text-orange-400', border: 'hover:border-orange-500/50', borderStatic: 'border-orange-500/30' },
};

// Centralized mapping of all AWS resource types mapped to icons and colors
export const RESOURCE_MAP = {
  // Compute
  'Instance': { icon: Server, ...themes.computeGreen },
  'EC2': { icon: Server, ...themes.computeGreen },
  'EKSCluster': { icon: Box, ...themes.computeEmerald },
  'ECSCluster': { icon: Box, ...themes.computeEmerald },
  'AutoScalingGroup': { icon: Box, ...themes.computeEmerald },
  'ASG': { icon: Layers, ...themes.asgOrange },
  'ElasticBeanstalkEnvironment': { icon: Box, ...themes.computeEmerald },
  'BatchComputeEnvironment': { icon: Box, ...themes.computeEmerald },
  'AppRunnerVpcConnector': { icon: Box, ...themes.computeEmerald },
  'WorkSpace': { icon: Box, ...themes.computeEmerald },

  // Database
  'RDSInstance': { icon: Database, ...themes.dbSky },
  'RDS': { icon: Database, ...themes.dbSky },
  'RedshiftCluster': { icon: Database, ...themes.dbSky },
  'DocumentDBCluster': { icon: Database, ...themes.dbSky },
  'MemoryDBCluster': { icon: Database, ...themes.dbSky },
  'NeptuneCluster': { icon: Database, ...themes.dbSky },
  'ElastiCacheNode': { icon: Database, ...themes.dbSky },
  'DirectoryService': { icon: Database, ...themes.dbSky },

  // Storage
  'S3Bucket': { icon: Box, ...themes.storageYellow },
  'EbsVolume': { icon: Box, ...themes.storageYellow },
  'EBS': { icon: HardDrive, ...themes.ebsPurple },
  'EFSMountTarget': { icon: Box, ...themes.storageYellow },
  'FSxFileSystem': { icon: Box, ...themes.storageYellow },

  // Analytics & ML
  'SageMakerNotebook': { icon: Zap, ...themes.mlOrange },
  'EMRCluster': { icon: Zap, ...themes.mlOrange },
  'GlueConnection': { icon: Zap, ...themes.mlOrange },
  'LambdaFunction': { icon: Zap, ...themes.mlOrange },
  'Lambda': { icon: Zap, ...themes.mlOrange },

  // Messaging
  'RegionalQueue': { icon: HardDrive, ...themes.mlOrange },
  'SQS': { icon: HardDrive, ...themes.mlOrange },
  'AmazonMQBroker': { icon: HardDrive, ...themes.mlOrange },
  'MSKCluster': { icon: HardDrive, ...themes.mlOrange },

  // Security
  'SecurityGroup': { icon: Shield, ...themes.secRed },
  'NetworkFirewall': { icon: Shield, ...themes.secRed },
  'NetworkAcl': { icon: Lock, ...themes.secLightRed },
  'IAMRole': { icon: Shield, ...themes.iamPink },
  'IAM_ROLE': { icon: Key, ...themes.iamYellow },
  'SecurityAndCompliance': { icon: Shield, ...themes.iamPink },

  // Networking Core
  'RouteTable': { icon: Network, ...themes.netCyan },
  'Subnet': { icon: Network, ...themes.netCyan },
  'VpcEndpoint': { icon: Network, ...themes.netCyan },
  'GWLBEndpoint': { icon: Network, ...themes.netCyan },
  'NetworkFirewallEndpoint': { icon: Network, ...themes.netCyan },
  'Route53ResolverEndpoint': { icon: Network, ...themes.netCyan },
  'PeeringConnection': { icon: Network, ...themes.netCyan },
  'VpnConnection': { icon: Network, ...themes.netCyan },
  'HybridConnectivity': { icon: Network, ...themes.netCyan },
  'TransitGatewayRouteTable': { icon: Network, ...themes.netCyan },

  // Networking Gateways & VPC
  'InternetGateway': { icon: Cloud, ...themes.dbSky },
  'EgressOnlyInternetGateway': { icon: Cloud, ...themes.dbSky },
  'NatGateway': { icon: Cloud, ...themes.dbSky },
  'VpnGateway': { icon: Cloud, ...themes.dbSky },
  'TransitGatewayAttachment': { icon: Cloud, ...themes.dbSky },
  'CarrierGateway': { icon: Cloud, ...themes.dbSky },
  'GatewayLoadBalancer': { icon: Cloud, ...themes.dbSky },
  'VPC': { icon: Cloud, ...themes.vpcPurple },
  'VPCs': { icon: Cloud, ...themes.vpcPurple },

  // Load Balancers
  'LoadBalancer': { icon: Network, ...themes.lbIndigo },
  'TargetGroup': { icon: Network, ...themes.lbIndigo },

  // Global & Edge
  'CloudFrontDistribution': { icon: Globe, ...themes.netLightCyan },
  'OpenSearchDomain': { icon: Globe, ...themes.netLightCyan },
  'Route53HostedZone': { icon: Globe, ...themes.netLightCyan },

  // Miscelleneous
  'ElasticIp': { icon: Activity, ...themes.miscLightSky },
  'UnclassifiedENI': { icon: Activity, ...themes.miscLightSky },
  'DhcpOption': { icon: Activity, ...themes.miscLightSky },

  // Fallbacks
  'Default': { icon: Activity, ...themes.defaultGray }
};

export const normalizeType = (type) => {
  return type.endsWith('s') && type !== 'DhcpOptions' && type !== 'ElasticIps' && type !== 'Route53ResolverEndpoints' && type !== 'VPCs'
    ? type.slice(0, -1) 
    : type;
};

export const getIcon = (type, size = 14) => {
  const norm = normalizeType(type);
  const config = RESOURCE_MAP[norm] || RESOURCE_MAP['Default'];
  const IconComponent = config.icon;
  return <IconComponent size={size} className={config.text} />;
};

export const getColorClasses = (type) => {
  const norm = normalizeType(type);
  return RESOURCE_MAP[norm] || RESOURCE_MAP['Default'];
};

export const getGlowColors = (type) => {
  const { text } = getColorClasses(type);
  
  if (text.includes('green') || text.includes('emerald')) return ['rgba(74,222,128,0.6)', 'rgba(34,197,94,0.6)'];
  if (text.includes('sky') || text.includes('cyan')) return ['rgba(56,189,248,0.6)', 'rgba(14,165,233,0.6)'];
  if (text.includes('orange') || text.includes('yellow')) return ['rgba(251,146,60,0.6)', 'rgba(249,115,22,0.6)'];
  if (text.includes('red') || text.includes('pink')) return ['rgba(248,113,113,0.6)', 'rgba(239,68,68,0.6)'];
  
  // Default to violet/indigo
  return ['rgba(167,139,250,0.6)', 'rgba(139,92,246,0.6)'];
};
