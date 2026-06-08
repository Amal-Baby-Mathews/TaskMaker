import React, { useMemo } from 'react'
import ReactFlow, { 
  Background, 
  MarkerType,
  Handle,
  Position
} from 'reactflow'
import 'reactflow/dist/style.css'
import { cn } from '@/lib/utils'

interface AgentTopologyMapProps {
  activeNode: string | null
}

// Custom Node component to handle layout pins cleanly
const AgentNode = ({ data }: any) => {
  const isActive = data.isActive
  
  return (
    <div className={cn(
      "px-4 py-3 rounded-xl border text-sm font-semibold tracking-wide transition-all duration-300 font-heading min-w-[140px] text-center relative shadow-md",
      isActive
        ? "bg-[#9D4EDD] text-white border-[#D800C4] shadow-lg shadow-[#D800C4]/30 scale-105 z-10 animate-pulse-slow"
        : "bg-[#181818] text-zinc-400 border-zinc-800/80 hover:border-zinc-700"
    )}>
      {/* Node label */}
      <div className="flex flex-col gap-0.5 select-none">
        <span className="text-[13px] font-bold">{data.label}</span>
        {isActive && (
          <span className="text-[9px] text-[#f7d6ff] font-sans font-extrabold uppercase tracking-wider animate-bounce mt-0.5">
            Active
          </span>
        )}
      </div>

      {/* Explicitly positioned target/source handles to avoid overlapping connections (noodles) */}
      
      {/* Left connections */}
      <Handle 
        type="target" 
        position={Position.Left} 
        id="in-left" 
        style={{ top: '35%', opacity: 0 }} 
      />
      <Handle 
        type="source" 
        position={Position.Left} 
        id="out-left" 
        style={{ top: '65%', opacity: 0 }} 
      />

      {/* Right connections */}
      <Handle 
        type="target" 
        position={Position.Right} 
        id="in-right" 
        style={{ top: '35%', opacity: 0 }} 
      />
      <Handle 
        type="source" 
        position={Position.Right} 
        id="out-right" 
        style={{ top: '65%', opacity: 0 }} 
      />

      {/* Top and Bottom connections */}
      <Handle 
        type="target" 
        position={Position.Top} 
        id="in-top" 
        style={{ left: '35%', opacity: 0 }} 
      />
      <Handle 
        type="source" 
        position={Position.Top} 
        id="out-top" 
        style={{ left: '65%', opacity: 0 }} 
      />
      <Handle 
        type="target" 
        position={Position.Bottom} 
        id="in-bottom" 
        style={{ left: '35%', opacity: 0 }} 
      />
      <Handle 
        type="source" 
        position={Position.Bottom} 
        id="out-bottom" 
        style={{ left: '65%', opacity: 0 }} 
      />
    </div>
  )
}

const nodeTypes = {
  agentNode: AgentNode
}

export const AgentTopologyMap: React.FC<AgentTopologyMapProps> = ({ activeNode }) => {
  // Map active node names from the backend SSE events to local reactflow IDs
  const normalizedActiveNode = useMemo(() => {
    if (!activeNode) return null
    const map: Record<string, string> = {
      'supervisor': 'supervisor',
      'executor': 'executor',
      'critic': 'critic',
      'retriever': 'retriever',
      'responder': 'responder',
      'rule_manager': 'rule_manager',
      'planner': 'planner'
    }
    return map[activeNode.toLowerCase()] || null
  }, [activeNode])

  // Clean, symmetric grid coordinates
  const nodes: any[] = useMemo(() => [
    {
      id: 'supervisor',
      type: 'agentNode',
      data: { label: 'Supervisor', isActive: normalizedActiveNode === 'supervisor' },
      position: { x: 230, y: 150 }
    },
    {
      id: 'planner',
      type: 'agentNode',
      data: { label: 'Planner', isActive: normalizedActiveNode === 'planner' },
      position: { x: 50, y: 30 }
    },
    {
      id: 'critic',
      type: 'agentNode',
      data: { label: 'Critic', isActive: normalizedActiveNode === 'critic' },
      position: { x: 30, y: 150 }
    },
    {
      id: 'executor',
      type: 'agentNode',
      data: { label: 'Executor', isActive: normalizedActiveNode === 'executor' },
      position: { x: 50, y: 270 }
    },
    {
      id: 'retriever',
      type: 'agentNode',
      data: { label: 'Retrieval', isActive: normalizedActiveNode === 'retriever' },
      position: { x: 410, y: 30 }
    },
    {
      id: 'responder',
      type: 'agentNode',
      data: { label: 'Responder', isActive: normalizedActiveNode === 'responder' },
      position: { x: 430, y: 150 }
    },
    {
      id: 'rule_manager',
      type: 'agentNode',
      data: { label: 'Rule Manager', isActive: normalizedActiveNode === 'rule_manager' },
      position: { x: 410, y: 270 }
    }
  ], [normalizedActiveNode])

  // Structured connections using clean 'smoothstep' lines and dedicated handles
  const edges: any[] = useMemo(() => [
    // 1. Supervisor <-> Planner
    {
      id: 'e-sup-plan',
      source: 'supervisor',
      sourceHandle: 'out-top',
      target: 'planner',
      targetHandle: 'in-bottom',
      type: 'smoothstep',
      borderRadius: 12,
      animated: normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'planner',
      style: { 
        stroke: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'planner') ? '#9D4EDD' : '#333333', 
        strokeWidth: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'planner') ? 2.5 : 1.5 
      },
      markerEnd: { 
        type: MarkerType.ArrowClosed, 
        color: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'planner') ? '#9D4EDD' : '#333333' 
      }
    },

    // 2. Planner -> Critic
    {
      id: 'e-plan-crit',
      source: 'planner',
      sourceHandle: 'out-bottom',
      target: 'critic',
      targetHandle: 'in-top',
      type: 'smoothstep',
      borderRadius: 12,
      animated: normalizedActiveNode === 'planner' || normalizedActiveNode === 'critic',
      style: { 
        stroke: (normalizedActiveNode === 'planner' || normalizedActiveNode === 'critic') ? '#9D4EDD' : '#333333', 
        strokeWidth: (normalizedActiveNode === 'planner' || normalizedActiveNode === 'critic') ? 2.5 : 1.5 
      },
      markerEnd: { 
        type: MarkerType.ArrowClosed, 
        color: (normalizedActiveNode === 'planner' || normalizedActiveNode === 'critic') ? '#9D4EDD' : '#333333' 
      }
    },

    // 3. Critic <-> Executor
    {
      id: 'e-crit-exec',
      source: 'critic',
      sourceHandle: 'out-bottom',
      target: 'executor',
      targetHandle: 'in-top',
      type: 'smoothstep',
      borderRadius: 12,
      animated: normalizedActiveNode === 'critic' || normalizedActiveNode === 'executor',
      style: { 
        stroke: (normalizedActiveNode === 'critic' || normalizedActiveNode === 'executor') ? '#9D4EDD' : '#333333', 
        strokeWidth: (normalizedActiveNode === 'critic' || normalizedActiveNode === 'executor') ? 2.5 : 1.5 
      },
      markerEnd: { 
        type: MarkerType.ArrowClosed, 
        color: (normalizedActiveNode === 'critic' || normalizedActiveNode === 'executor') ? '#9D4EDD' : '#333333' 
      }
    },

    // 4. Executor -> Supervisor
    {
      id: 'e-exec-sup',
      source: 'executor',
      sourceHandle: 'out-right',
      target: 'supervisor',
      targetHandle: 'in-bottom',
      type: 'smoothstep',
      borderRadius: 12,
      animated: normalizedActiveNode === 'executor' || normalizedActiveNode === 'supervisor',
      style: { 
        stroke: (normalizedActiveNode === 'executor' || normalizedActiveNode === 'supervisor') ? '#9D4EDD' : '#333333', 
        strokeWidth: (normalizedActiveNode === 'executor' || normalizedActiveNode === 'supervisor') ? 2.5 : 1.5 
      },
      markerEnd: { 
        type: MarkerType.ArrowClosed, 
        color: (normalizedActiveNode === 'executor' || normalizedActiveNode === 'supervisor') ? '#9D4EDD' : '#333333' 
      }
    },

    // 5. Supervisor <-> Retriever
    {
      id: 'e-sup-ret',
      source: 'supervisor',
      sourceHandle: 'out-top',
      target: 'retriever',
      targetHandle: 'in-bottom',
      type: 'smoothstep',
      borderRadius: 12,
      animated: normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'retriever',
      style: { 
        stroke: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'retriever') ? '#9D4EDD' : '#333333', 
        strokeWidth: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'retriever') ? 2.5 : 1.5 
      },
      markerEnd: { 
        type: MarkerType.ArrowClosed, 
        color: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'retriever') ? '#9D4EDD' : '#333333' 
      }
    },

    // 6. Supervisor <-> Responder
    {
      id: 'e-sup-resp',
      source: 'supervisor',
      sourceHandle: 'out-right',
      target: 'responder',
      targetHandle: 'in-left',
      type: 'smoothstep',
      borderRadius: 12,
      animated: normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'responder',
      style: { 
        stroke: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'responder') ? '#9D4EDD' : '#333333', 
        strokeWidth: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'responder') ? 2.5 : 1.5 
      },
      markerEnd: { 
        type: MarkerType.ArrowClosed, 
        color: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'responder') ? '#9D4EDD' : '#333333' 
      }
    },

    // 7. Supervisor <-> Rule Manager
    {
      id: 'e-sup-rule',
      source: 'supervisor',
      sourceHandle: 'out-bottom',
      target: 'rule_manager',
      targetHandle: 'in-top',
      type: 'smoothstep',
      borderRadius: 12,
      animated: normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'rule_manager',
      style: { 
        stroke: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'rule_manager') ? '#9D4EDD' : '#333333', 
        strokeWidth: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'rule_manager') ? 2.5 : 1.5 
      },
      markerEnd: { 
        type: MarkerType.ArrowClosed, 
        color: (normalizedActiveNode === 'supervisor' || normalizedActiveNode === 'rule_manager') ? '#9D4EDD' : '#333333' 
      }
    }
  ], [normalizedActiveNode])

  return (
    <div className="w-full h-[400px] border border-[#2a2a2a] bg-[#141414] rounded-xl overflow-hidden relative shadow-inner">
      <div className="absolute top-3 left-4 z-10 font-heading text-xs font-semibold text-[#9D4EDD] uppercase tracking-wider bg-[#111] px-2.5 py-1.5 rounded-md border border-[#2a2a2a]">
        Agent Topology Map
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        preventScrolling={true}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        panOnDrag={false}
        nodesDraggable={false}
        nodesConnectable={false}
      >
        <Background color="#2a2a2a" gap={16} size={1} />
      </ReactFlow>
    </div>
  )
}
export default AgentTopologyMap
