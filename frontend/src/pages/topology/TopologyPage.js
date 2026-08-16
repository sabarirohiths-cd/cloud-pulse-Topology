import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { ReactFlow, MiniMap, Controls, Background, useNodesState, useEdgesState, Panel } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toast } from 'sonner';
import { scanTopology, getSampleTopology } from '../../api/topology';
import { transformTopologyToGraph } from '../../utils/topologyLayout';
import VpcNode from '../../components/topology/nodes/VpcNode';
import SubnetNode from '../../components/topology/nodes/SubnetNode';
import ResourceNode from '../../components/topology/nodes/ResourceNode';
import TopologyDetailModal from '../../components/topology/TopologyDetailModal';

export default function TopologyPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);

  const nodeTypes = useMemo(() => ({
    vpcNode: VpcNode,
    subnetNode: SubnetNode,
    resourceNode: ResourceNode
  }), []);

  const loadData = useCallback(async (isLive = false) => {
    setLoading(true);
    try {
      const response = isLive ? await scanTopology() : await getSampleTopology();
      const topologyData = response.data || [];
      const { nodes: layoutedNodes, edges: layoutedEdges } = transformTopologyToGraph(topologyData);
      
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
      toast.success(isLive ? 'Live scan complete!' : 'Loaded sample topology.');
    } catch (error) {
      toast.error('Failed to load topology: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  return (
    <div className="h-full w-full bg-[#0a0a0f] rounded-lg border border-[#1e232b] overflow-hidden relative flex flex-col">
      <div className="p-4 border-b border-[#1e232b] bg-[#0e1015] flex items-center justify-between z-10">
        <h2 className="text-white font-semibold text-lg">AWS Infrastructure Topology</h2>
        <div className="flex gap-3">
          <button 
            onClick={() => loadData(false)}
            disabled={loading}
            className="px-4 py-2 bg-[#1a1d24] text-gray-300 rounded-md text-sm hover:bg-[#2d333b] hover:text-white transition-colors"
          >
            Load Mock Data
          </button>
          <button 
            onClick={() => loadData(true)}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-500 transition-colors flex items-center gap-2"
          >
            {loading ? 'Scanning...' : 'Live Scan'}
          </button>
        </div>
      </div>
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={(e, node) => setSelectedNode(node)}
          onPaneClick={() => setSelectedNode(null)}
          nodeTypes={nodeTypes}
          fitView
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={true}
          className="bg-transparent"
        >
          <Background color="#1e232b" gap={24} />
          <Controls className="bg-[#1a1d24] border-[#2d333b] fill-white" />
          <MiniMap 
            nodeColor={(node) => {
              if (node.type === 'vpcNode') return '#a855f7';
              if (node.type === 'subnetNode') return '#3b82f6';
              return '#10b981';
            }}
            maskColor="rgba(10, 10, 15, 0.7)"
            className="bg-[#0e1015] border-[#1e232b]"
          />
        </ReactFlow>
        <TopologyDetailModal node={selectedNode} onClose={() => setSelectedNode(null)} />
      </div>
    </div>
  );
}
