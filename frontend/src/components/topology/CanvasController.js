import React, { useEffect } from 'react';
import { useReactFlow } from '@xyflow/react';

export default function CanvasController({ focusedNodeId }) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    if (focusedNodeId) {
      setTimeout(() => {
        fitView({
          nodes: [{ id: focusedNodeId }],
          duration: 800,
          maxZoom: 1.2
        });
      }, 50);
    }
  }, [focusedNodeId, fitView]);

  return null; // Invisible component
}
