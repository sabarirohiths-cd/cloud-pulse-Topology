import { Handle, Position } from '@xyflow/react';
import { Cloud } from 'lucide-react';

export default function VpcNode({ data, sourcePosition, targetPosition }) {
  return (
    <div className="w-[250px] bg-[#11141a] border border-[#1e232b] rounded-md shadow-lg overflow-hidden flex flex-col items-center p-3 relative">
      <Handle type="target" position={targetPosition || Position.Left} className="w-2 h-2 bg-purple-500 border-none" />
      
      <div className="w-10 h-10 bg-purple-500/10 rounded-full flex items-center justify-center mb-2">
        <Cloud className="w-5 h-5 text-purple-400" />
      </div>
      <div className="text-white text-xs font-bold text-center truncate w-full mb-1">{data.label}</div>
      <div className="text-gray-400 text-[10px] text-center w-full uppercase tracking-wider">Virtual Private Cloud</div>
      
      <Handle type="source" position={sourcePosition || Position.Right} className="w-2 h-2 bg-purple-500 border-none" />
    </div>
  );
}
