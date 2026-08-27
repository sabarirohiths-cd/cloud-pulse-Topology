import React, { useMemo, useEffect, useState, useRef, useCallback } from 'react';
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

const CustomNode = ({ data, selected }) => {
  const isRunning = data.status === 'running' || data.status === 'available' || data.status === 'active' || data.status === 'attached';
  const isCritical = data.health_state === 'CRITICAL';
  const isRoot = data.isRoot;
  const isHighlighted = data.isHighlighted;

  const colors = getColorClasses(data.type);

  return (
    <div
      className={`p-4 rounded-xl border transition-all duration-200 shadow-md ${
          isHighlighted ? 'border-cyan-400 ring-1 ring-cyan-400/50 shadow-[0_4px_20px_rgba(34,211,238,0.2)] bg-slate-800 z-10'
        : isCritical ? 'border-rose-500 ring-1 ring-rose-500/50 shadow-[0_4px_20px_rgba(244,63,94,0.2)] bg-rose-950/30 z-10'
        : isRoot ? 'border-amber-500 ring-1 ring-amber-500/50 shadow-[0_4px_20px_rgba(245,158,11,0.2)] bg-amber-950/20 z-10'
        : 'border-slate-700 hover:border-slate-500 hover:shadow-lg bg-slate-800'
        } w-[260px] flex flex-col relative`}>
      <Handle type="target" position={Position.Left} className="!bg-zinc-600 !w-2 !h-4 !rounded-sm !-left-1 !border-none" />

      <div className="flex justify-between items-start mb-3">
        <div
          className={`w-8 h-8 flex items-center justify-center rounded-full border ${isRunning ? 'border-slate-700 bg-slate-900/80 shadow-inner ' + colors.text : 'border-slate-700 bg-slate-900/50 text-slate-500'}`}
        >
          {getIcon(data.type, 16)}
        </div>
        <span className="px-2.5 py-0.5 rounded-full bg-slate-900 border border-slate-700 text-xs font-bold text-slate-300 uppercase tracking-wider shadow-sm">{data.type}</span>
      </div>

      <div className="flex flex-col overflow-hidden gap-1 mb-4">
        <div className="text-zinc-100 font-bold text-lg truncate" title={data.label}>{data.label}</div>
      </div>

      <div className="pt-3 border-t border-zinc-800/50 flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isCritical ? 'bg-red-500' : isRunning ? 'bg-emerald-500' : 'bg-amber-500'}`}></div>
        <span className={`text-[13px] font-bold tracking-wide ${isCritical ? 'text-red-400' : 'text-zinc-400'}`}>
            {isCritical ? 'CRITICAL' : data.status || 'UNKNOWN'}
        </span>
      </div>

      <Handle type="source" position={Position.Right} className="!bg-zinc-600 !w-2 !h-4 !rounded-sm !-right-1 !border-none" />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

const getLayoutedElements = (nodes, edges, direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 280;
  const nodeHeight = 120;

  dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 140 });

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
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

function FlowVisualizerContent({ data, focusNodeId, onNodeClick, isSidebarOpen }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { setCenter, getNode, fitView } = useReactFlow();
  const [lastCenteredNodeId, setLastCenteredNodeId] = useState(null);
  const [hoveredNodeId, setHoveredNodeId] = useState(null);

  // Re-center graph when sidebar toggles
  useEffect(() => {
    // Timeout allows CSS transition (width change) to finish before centering
    const timeout = setTimeout(() => {
      if (nodes.length > 0) {
        fitView({ padding: 0.1, duration: 600, maxZoom: 1.2 });
      }
    }, 350);
    return () => clearTimeout(timeout);
  }, [isSidebarOpen, fitView, nodes.length]);

  useEffect(() => {
    if (focusNodeId && focusNodeId !== lastCenteredNodeId && nodes.length > 0) {
      // Wait for React Flow to fully render and measure node dimensions in the DOM before fitting
      const timeout = setTimeout(() => {
        window.requestAnimationFrame(() => {
          const node = getNode(focusNodeId);
          if (node) {
            const x = node.position.x + (node.measured?.width || 280) / 2;
            const y = node.position.y + (node.measured?.height || 120) / 2;
            setCenter(x, y, { zoom: 1.2, duration: 800 });
          } else {
            fitView({ padding: 0.2, duration: 800, maxZoom: 1.1 });
          }
        });
        setLastCenteredNodeId(focusNodeId);
      }, 400);
      return () => clearTimeout(timeout);
    }
  }, [focusNodeId, nodes, fitView, setCenter, getNode, lastCenteredNodeId]);

  // Also reset the tracker if data completely changes (new trace)
  useEffect(() => {
    setLastCenteredNodeId(null);
  }, [data]);

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
        isRoot: n.id === data.compute_id || n.id === data.last_compute_id,
        isHighlighted: n.id === hoveredNodeId
      },
      position: { x: 0, y: 0 }
    }));

    const rfEdges = (data.edges || []).map((e, idx) => {
      const sourceNode = data.nodes.find(n => n.id === e.source);
      const targetNode = data.nodes.find(n => n.id === e.target);
      const isIncident = e.health_state === 'CRITICAL' || e.health_state === 'BLOCKED' || sourceNode?.health_state === 'CRITICAL' || targetNode?.health_state === 'CRITICAL';

      const isMainEdge = sourceNode?.isRoot || targetNode?.isRoot;

      return {
        id: `e-${e.source}-${e.target}-${idx}`,
        source: e.source,
        target: e.target,
        label: e.relation,
        type: 'default', // 'default' in ReactFlow is usually bezier. Or 'bezier'
        animated: isIncident || true,
        style: isIncident ? { stroke: '#f43f5e', strokeWidth: 2, strokeDasharray: '5,5' } : isMainEdge ? { stroke: '#f59e0b', strokeWidth: 2 } : { stroke: '#64748b', strokeWidth: 2 },
        labelStyle: { fill: isIncident ? '#f43f5e' : isMainEdge ? '#fbbf24' : '#cbd5e1', fontWeight: 700, fontSize: 13 },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.95 },
        labelBgPadding: [6, 4],
        labelBgBorderRadius: 4,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isIncident ? '#f43f5e' : isMainEdge ? '#f59e0b' : '#64748b',
        },
        data: {
          health_state: e.health_state,
          diagnostic: e.diagnostic
        }
      };
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rfNodes, rfEdges, 'LR');

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [data, setNodes, setEdges]);

  // Handle edge highlighting when a node is hovered
  useEffect(() => {
    if (!data || !data.nodes) return;

    setEdges(eds => eds.map(e => {
      const sourceNode = data.nodes.find(n => n.id === e.source);
      const targetNode = data.nodes.find(n => n.id === e.target);
      const isIncident = e.data?.health_state === 'CRITICAL' || e.data?.health_state === 'BLOCKED' || sourceNode?.health_state === 'CRITICAL' || targetNode?.health_state === 'CRITICAL';
      
      const isMainEdge = sourceNode?.isRoot || targetNode?.isRoot;
      
      let strokeColor = isMainEdge ? '#f59e0b' : '#64748b';
      let strokeWidth = 2;
      let labelColor = isMainEdge ? '#fbbf24' : '#94a3b8';
      
      if (isIncident) {
         strokeColor = '#f43f5e';
         labelColor = '#f43f5e';
      } else if (hoveredNodeId && (hoveredNodeId === e.source || hoveredNodeId === e.target)) {
         strokeColor = '#22d3ee'; // cyan-400
         strokeWidth = 3;
         labelColor = '#67e8f9';
      } else if (hoveredNodeId) {
         // Dim non-connected edges if ANY node is hovered
         strokeColor = '#334155';
         strokeWidth = 1;
         labelColor = '#475569';
      }

      return {
        ...e,
        style: { ...e.style, stroke: strokeColor, strokeWidth },
        labelStyle: { ...e.labelStyle, fill: labelColor },
        markerEnd: { ...e.markerEnd, color: strokeColor }
      };
    }));
  }, [hoveredNodeId, data, setEdges]);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 bg-[#0a0a0f] gap-4">
        <CloudOff size={48} className="opacity-20" />
        <p>No trace data available. Select a compute resource.</p>
      </div>
    );
  }

  const handleNodeClick = (_, node) => {
    setHoveredNodeId(null);
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
        onNodeMouseEnter={(_, node) => setHoveredNodeId(node.id)}
        onNodeMouseLeave={() => setHoveredNodeId(null)}
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
        <Background color="#475569" gap={24} size={1.5} />
        <MiniMap 
          nodeColor={(n) => {
            if (n.data?.health_state === 'CRITICAL') return '#f43f5e';
            if (n.data?.isRoot) return '#f59e0b';
            if (n.data?.isHighlighted) return '#22d3ee';
            return '#1e293b';
          }}
          maskColor="rgba(0, 0, 0, 0.6)"
          maskStrokeColor="#94a3b8"
          maskStrokeWidth={1}
          style={{ backgroundColor: '#0f172a', width: 120, height: 80 }}
          className="!bg-slate-900 border border-slate-700 rounded-lg shadow-2xl overflow-hidden"
        />
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
