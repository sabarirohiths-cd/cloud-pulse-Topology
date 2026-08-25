import React, { useMemo, useEffect, useState } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from '@dagrejs/dagre';
import { getIcon, getColorClasses, getGlowColors } from '../../../utils/iconMap';
import { CloudOff } from 'lucide-react';

const CustomNode = ({ data }) => {
  const isRunning = data.status === 'running' || data.status === 'available' || data.status === 'active' || data.status === 'attached';
  const isCritical = data.health_state === 'CRITICAL';
  const isRoot = data.isRoot;

  const colors = getColorClasses(data.type);

  return (
    <div
      className={`p-4 rounded-xl border-2 bg-[#161b22]/90 backdrop-blur ${isCritical ? 'border-red-500 ring-2 ring-red-500 animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.5)]'
        : isRoot ? 'border-sky-500 shadow-[0_0_20px_rgba(14,165,233,0.3)] ring-1 ring-sky-500'
        : 'border-zinc-700 shadow-xl'
        } w-[260px] flex flex-col relative transition-transform hover:scale-105`}>
      <Handle type="target" position={Position.Top} className="!bg-zinc-500 !w-3 !h-3 !-top-1.5" />

      <div className="flex items-center gap-3 mb-2">
        <div
          className={`p-2 rounded-lg ${isRunning ? colors.text : 'bg-zinc-800 text-zinc-400'}`}
          style={isRunning ? { backgroundColor: 'rgba(255,255,255,0.05)' } : {}}
        >
          {getIcon(data.type, 18)}
        </div>
        <div className="flex flex-col overflow-hidden gap-1">
          <span className="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-[9px] font-bold text-sky-400 uppercase tracking-wider w-fit shadow-sm">{data.type}</span>
          <div className="text-white font-bold text-sm break-words leading-tight" title={data.label}>{data.label}</div>
        </div>
      </div>

      <div className="mt-2 pt-2 border-t border-zinc-800 flex justify-between items-center">
        <div className={`flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider ${isCritical ? 'text-red-400' : isRunning ? 'text-emerald-400' : 'text-amber-400'}`}>
          <div className={`w-2 h-2 rounded-full ${isCritical ? 'bg-red-500' : isRunning ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></div>
          {isCritical ? 'CRITICAL' : data.status || 'UNKNOWN'}
        </div>

        {data.metadata?.PrivateIpAddress && (
          <div className="text-xs text-zinc-500 font-mono">
            {data.metadata.PrivateIpAddress}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-zinc-500 !w-3 !h-3 !-bottom-1.5" />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 280;
  const nodeHeight = 120;

  dagreGraph.setGraph({ rankdir: direction, nodesep: 50, ranksep: 100 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

function FlowVisualizerContent({ data, focusNodeId, onNodeClick }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { setCenter, getNode } = useReactFlow();

  useEffect(() => {
    if (focusNodeId && nodes.length > 0) {
      const node = getNode(focusNodeId);
      if (node && node.position) {
        setCenter(node.position.x + 140, node.position.y + 60, { zoom: 1.15, duration: 800 });
      }
    }
  }, [focusNodeId, nodes, getNode, setCenter]);

  useEffect(() => {
    if (!data || !data.nodes) return;

    const rfNodes = data.nodes.map(n => ({
      id: n.id,
      type: 'custom',
      data: {
        label: n.label,
        type: n.type,
        status: n.status,
        metadata: n.metadata,
        health_state: n.health_state,
        diagnostic: n.diagnostic,
        isRoot: n.id === data.compute_id || n.id === data.last_compute_id
      },
      position: { x: 0, y: 0 }
    }));

    const rfEdges = (data.edges || []).map((e, idx) => {
      const sourceNode = data.nodes.find(n => n.id === e.source);
      const targetNode = data.nodes.find(n => n.id === e.target);
      const isIncident = e.health_state === 'CRITICAL' || e.health_state === 'BLOCKED' || sourceNode?.health_state === 'CRITICAL' || targetNode?.health_state === 'CRITICAL';

      return {
        id: `e-${e.source}-${e.target}-${idx}`,
        source: e.source,
        target: e.target,
        label: e.relation,
        type: 'smoothstep',
        animated: isIncident || true,
        style: isIncident ? { stroke: '#ef4444', strokeWidth: 3, strokeDasharray: '5,5' } : { stroke: '#22c55e', strokeWidth: 2 },
        labelStyle: { fill: isIncident ? '#ef4444' : '#22c55e', fontWeight: 700, fontSize: 10 },
        labelBgStyle: { fill: '#161b22', fillOpacity: 0.9 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isIncident ? '#ef4444' : '#22c55e',
        },
        data: {
          health_state: e.health_state,
          diagnostic: e.diagnostic
        }
      };
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rfNodes, rfEdges, 'TB');

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [data, setNodes, setEdges]);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-zinc-500 bg-[#0a0a0f] gap-4">
        <CloudOff size={48} className="opacity-20" />
        <p>No trace data available. Select a compute resource.</p>
      </div>
    );
  }

  const handleNodeClick = (_, node) => {
    if (onNodeClick) {
      onNodeClick(node);
    }
  };

  return (
    <div className="w-full h-full bg-[#0a0a0f]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.1, maxZoom: 1.2 }}
        minZoom={0.1}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        panOnScroll={false}
        className="bg-transparent [&>.react-flow__renderer>.react-flow__viewport]:transition-transform [&>.react-flow__renderer>.react-flow__viewport]:duration-150 [&>.react-flow__renderer>.react-flow__viewport]:ease-out"
      >
        <Background color="#1e232b" gap={24} size={2} />
        <Controls
          className="bg-[#161b22] border-zinc-800 shadow-xl"
          showInteractive={false}
        />
      </ReactFlow>
    </div>
  );
}

export default function ApplicationFlowVisualizer(props) {
  return (
    <ReactFlowProvider>
      <FlowVisualizerContent {...props} />
    </ReactFlowProvider>
  );
}
