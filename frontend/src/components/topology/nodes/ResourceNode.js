import { Handle, Position } from '@xyflow/react';
import { Server, Database, Zap, Activity } from 'lucide-react';

export default function ResourceNode({ data, sourcePosition, targetPosition }) {
  const getIcon = () => {
    switch (data.type) {
      case 'EC2': return <Server className="w-5 h-5 text-green-400" />;
      case 'RDS': return <Database className="w-5 h-5 text-blue-400" />;
      case 'Lambda': return <Zap className="w-5 h-5 text-orange-400" />;
      default: return <Activity className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div className="bg-[#1a1d24] border border-[#2d333b] rounded-md p-3 min-w-[200px] flex items-center gap-3 shadow-lg">
      <Handle type="target" position={targetPosition || Position.Left} className="!bg-gray-500 w-2 h-2" />
      <div className="p-2 bg-[#0a0a0f] rounded-md border border-[#2d333b]">
        {getIcon()}
      </div>
      <div className="flex flex-col">
        <span className="text-white text-sm font-medium truncate max-w-[140px]">{data.label}</span>
        <span className="text-gray-400 text-xs">{data.type}</span>
      </div>
      <Handle type="source" position={sourcePosition || Position.Right} className="!bg-gray-500 w-2 h-2" />
    </div>
  );
}
