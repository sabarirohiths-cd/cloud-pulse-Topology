import React from 'react';
import { 
  Server, Database, Shield, Lock, Network, Cloud, 
  Box, Zap, Activity, Globe, HardDrive
} from 'lucide-react';

export const getIcon = (type, size = 14) => {
  // Normalize type string by removing trailing 's' if plural (rudimentary singularize)
  const normalizedType = type.endsWith('s') && type !== 'RDSInstances' && type !== 'DhcpOptions' && type !== 'ElasticIps' && type !== 'Route53ResolverEndpoints'
    ? type.slice(0, -1) 
    : type;

  switch (normalizedType) {
    case 'Instance':
    case 'EC2':
      return <Server size={size} className="text-green-400" />;
    
    case 'RDSInstance':
    case 'RDS':
    case 'RedshiftCluster':
    case 'DocumentDBCluster':
    case 'MemoryDBCluster':
    case 'NeptuneCluster':
    case 'ElastiCacheNode':
      return <Database size={size} className="text-sky-400" />;
    
    case 'RegionalQueue':
    case 'SQS':
    case 'AmazonMQBroker':
    case 'MSKCluster':
      return <HardDrive size={size} className="text-orange-400" />;

    case 'LambdaFunction':
    case 'Lambda':
      return <Zap size={size} className="text-orange-400" />;
    
    case 'SecurityGroup':
      return <Shield size={size} className="text-red-400" />;
    
    case 'NetworkAcl':
      return <Lock size={size} className="text-red-300" />;
    
    case 'RouteTable':
    case 'Subnet':
      return <Network size={size} className="text-cyan-400" />;
    
    case 'InternetGateway':
    case 'EgressOnlyInternetGateway':
    case 'NatGateway':
    case 'VpnGateway':
    case 'TransitGatewayAttachment':
    case 'CarrierGateway':
    case 'GatewayLoadBalancer':
    case 'VPC':
      return <Cloud size={size} className={type === 'VPC' || type === 'VPCs' ? "text-purple-400" : "text-sky-400"} />;
    
    case 'LoadBalancer':
      return <Network size={size} className="text-indigo-400" />;

    case 'S3Bucket':
      return <Box size={size} className="text-yellow-400" />;
    
    case 'IAMRole':
    case 'SecurityAndCompliance':
      return <Shield size={size} className="text-pink-400" />;
    
    case 'CloudFrontDistribution':
    case 'OpenSearchDomain':
      return <Globe size={size} className="text-cyan-300" />;
      
    case 'EKSCluster':
    case 'ECSCluster':
    case 'AutoScalingGroup':
      return <Box size={size} className="text-emerald-400" />;

    default:
      return <Activity size={size} className="text-gray-400" />;
  }
};

export const getColorClasses = (type) => {
  const normalizedType = type.endsWith('s') && type !== 'RDSInstances' && type !== 'DhcpOptions' && type !== 'ElasticIps' && type !== 'Route53ResolverEndpoints'
    ? type.slice(0, -1) 
    : type;

  switch (normalizedType) {
    case 'Instance':
    case 'EC2':
      return { text: 'text-green-400', border: 'hover:border-green-500/50', borderStatic: 'border-green-500/30' };
    
    case 'RDSInstance':
    case 'RDS':
    case 'RedshiftCluster':
    case 'DocumentDBCluster':
    case 'MemoryDBCluster':
    case 'NeptuneCluster':
    case 'ElastiCacheNode':
      return { text: 'text-sky-400', border: 'hover:border-sky-500/50', borderStatic: 'border-sky-500/30' };
      
    case 'RegionalQueue':
    case 'SQS':
    case 'AmazonMQBroker':
    case 'MSKCluster':
    case 'LambdaFunction':
    case 'Lambda':
      return { text: 'text-orange-400', border: 'hover:border-orange-500/50', borderStatic: 'border-orange-500/30' };
      
    case 'SecurityGroup':
      return { text: 'text-red-400', border: 'hover:border-red-500/50', borderStatic: 'border-red-500/30' };
    
    case 'NetworkAcl':
      return { text: 'text-red-300', border: 'hover:border-red-400/50', borderStatic: 'border-red-400/30' };
      
    case 'RouteTable':
    case 'Subnet':
      return { text: 'text-cyan-400', border: 'hover:border-cyan-500/50', borderStatic: 'border-cyan-500/30' };
      
    case 'VPC':
      return { text: 'text-purple-400', border: 'hover:border-purple-500/50', borderStatic: 'border-purple-500/30' };
      
    case 'InternetGateway':
    case 'EgressOnlyInternetGateway':
    case 'NatGateway':
    case 'VpnGateway':
    case 'TransitGatewayAttachment':
    case 'CarrierGateway':
    case 'GatewayLoadBalancer':
      return { text: 'text-sky-400', border: 'hover:border-sky-500/50', borderStatic: 'border-sky-500/30' };
      
    case 'LoadBalancer':
      return { text: 'text-indigo-400', border: 'hover:border-indigo-500/50', borderStatic: 'border-indigo-500/30' };
      
    case 'S3Bucket':
      return { text: 'text-yellow-400', border: 'hover:border-yellow-500/50', borderStatic: 'border-yellow-500/30' };
      
    case 'IAMRole':
    case 'SecurityAndCompliance':
      return { text: 'text-pink-400', border: 'hover:border-pink-500/50', borderStatic: 'border-pink-500/30' };
      
    case 'CloudFrontDistribution':
    case 'OpenSearchDomain':
      return { text: 'text-cyan-300', border: 'hover:border-cyan-400/50', borderStatic: 'border-cyan-400/30' };
      
    case 'EKSCluster':
    case 'ECSCluster':
    case 'AutoScalingGroup':
      return { text: 'text-emerald-400', border: 'hover:border-emerald-500/50', borderStatic: 'border-emerald-500/30' };
      
    default:
      return { text: 'text-gray-400', border: 'hover:border-gray-500/50', borderStatic: 'border-gray-500/30' };
  }
};
