import React, { useState, useCallback, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Shield, Share2, Menu, Search, Moon, Sun } from 'lucide-react';

import ScreenshotNode from './components/ScreenshotNode';
import NodeDetailsModal from './components/NodeDetailsModal';
import InspectorPanel from './components/InspectorPanel';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const nodeTypes = {
  screenshotNode: ScreenshotNode,
};

import dagre from 'dagre';

// ... imports

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 250;
const nodeHeight = 450;

const getLayoutedElements = (nodes, edges, direction = 'LR') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction });

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
      targetPosition: isHorizontal ? 'left' : 'top',
      sourcePosition: isHorizontal ? 'right' : 'bottom',
      // We are shifting the dagre node position (anchor=center center) to the top left
      // so it matches the React Flow node anchor point (top left).
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [modalNode, setModalNode] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Check local storage or system preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      return savedTheme === 'dark';
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  // Toggle Dark Mode
  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
  };

  // Apply Dark Mode Class
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDarkMode]);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [adbStatus, setAdbStatus] = useState({ connected: false, device: null });

  // Load data on mount
  useEffect(() => {
    const controller = new AbortController();

    const fetchGraphData = async () => {
      try {
        setIsLoading(true);
        setLoadError(null);

        const response = await fetch(`${API_BASE_URL}/api/graph`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Failed to load graph data (${response.status})`);
        }

        const payload = await response.json();

        const normalizedNodes = (payload.nodes || []).map((node) => ({
          ...node,
          position: node.position || { x: 0, y: 0 },
          data: {
            label: node.data?.label ?? node.label ?? 'Untitled Node',
            description: node.data?.description ?? node.description ?? '',
            screenshot: node.data?.screenshot ?? node.screenshot ?? null,
            annotatedScreenshot: node.data?.annotatedScreenshot ?? null,
            traffic: node.data?.traffic ?? [],
            parser: node.data?.parser ?? node.parser ?? null,
          },
        }));

        const normalizedEdges = (payload.edges || []).map((edge) => ({
          id: edge.id || `${edge.source_node_id}-${edge.target_node_id}`,
          source: edge.source ?? edge.source_node_id,
          target: edge.target ?? edge.target_node_id,
          label: edge.label,
          animated: edge.animated === undefined ? true : Boolean(edge.animated),
        }));

        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
          normalizedNodes,
          normalizedEdges
        );

        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
      } catch (error) {
        if (controller.signal.aborted) return;
        console.error('Failed to load graph data:', error);
        setLoadError(error.message);
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    fetchGraphData();

    return () => controller.abort();
  }, [setNodes, setEdges]);

  // Poll ADB status
  useEffect(() => {
    const fetchAdbStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/adb/status`);
        if (response.ok) {
          const data = await response.json();
          setAdbStatus(data);
        }
      } catch (error) {
        console.error('Failed to fetch ADB status:', error);
        setAdbStatus({ connected: false, device: null });
      }
    };

    // Fetch immediately
    fetchAdbStatus();

    // Poll every 3 seconds
    const interval = setInterval(fetchAdbStatus, 3000);

    return () => clearInterval(interval);
  }, []);
  // ... rest of the component

  const resetVisuals = useCallback(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        style: {
          ...n.style,
          opacity: 1,
          border: '2px solid transparent', // Reset border
        },
      }))
    );
    setEdges((eds) =>
      eds.map((e) => ({
        ...e,
        style: {
          ...e.style,
          stroke: '#b1b1b7',
          strokeWidth: 1,
          opacity: 1,
        },
        animated: true, // Keep default animation or set to false if preferred
      }))
    );
  }, [setNodes, setEdges]);

  // Search Logic
  useEffect(() => {
    if (!searchQuery.trim()) {
      resetVisuals();
      return;
    }

    const query = searchQuery.toLowerCase();
    const matchedNodeIds = new Set();

    setNodes((prevNodes) => {
      prevNodes.forEach(node => {
        const labelMatch = node.data.label.toLowerCase().includes(query);
        const apiMatch = node.data.traffic?.some(req => req.url.toLowerCase().includes(query));
        const parserMatch = node.data.parser?.parsedContentList?.some((item) =>
          (item.content || '').toLowerCase().includes(query)
        );

        if (labelMatch || apiMatch || parserMatch) {
          matchedNodeIds.add(node.id);
        }
      });

      return prevNodes.map((n) => ({
        ...n,
        style: {
          ...n.style,
          opacity: matchedNodeIds.has(n.id) ? 1 : 0.1,
          border: matchedNodeIds.has(n.id) ? '2px solid #2563eb' : '2px solid transparent',
        },
      }));
    });

    setEdges((eds) =>
      eds.map((e) => ({
        ...e,
        style: {
          ...e.style,
          opacity: 0.1,
        },
      }))
    );

  }, [searchQuery, setNodes, setEdges, resetVisuals]); // Re-run when query changes

  const resetLayout = useCallback(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      edges
    );
    setNodes([...layoutedNodes]);
    setEdges([...layoutedEdges]);
  }, [nodes, edges, setNodes, setEdges]);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  const getPathToNode = (targetNodeId, allEdges) => {
    const pathEdges = new Set();
    const pathNodes = new Set([targetNodeId]);
    const queue = [targetNodeId];
    const visited = new Set([targetNodeId]);

    // Build adjacency list for reverse traversal (target -> source)
    const incomingEdges = {};
    allEdges.forEach(edge => {
      if (!incomingEdges[edge.target]) {
        incomingEdges[edge.target] = [];
      }
      incomingEdges[edge.target].push(edge);
    });

    while (queue.length > 0) {
      const currentId = queue.shift();
      const incoming = incomingEdges[currentId] || [];

      incoming.forEach(edge => {
        if (!visited.has(edge.source)) {
          visited.add(edge.source);
          pathNodes.add(edge.source);
          queue.push(edge.source);
        }
        pathEdges.add(edge.id);
      });
    }

    return { pathNodes, pathEdges };
  };

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);

    const { pathNodes, pathEdges } = getPathToNode(node.id, edges);

    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        style: {
          ...n.style,
          opacity: pathNodes.has(n.id) ? 1 : 0.3,
          border: '2px solid transparent', // Reset border on click
        },
      }))
    );

    setEdges((eds) =>
      eds.map((e) => ({
        ...e,
        style: {
          ...e.style,
          stroke: pathEdges.has(e.id) ? '#2563eb' : '#b1b1b7',
          strokeWidth: pathEdges.has(e.id) ? 3 : 1,
          opacity: pathEdges.has(e.id) ? 1 : 0.3,
        },
        animated: pathEdges.has(e.id),
      }))
    );
  }, [edges, setNodes, setEdges]);

  const onNodeDoubleClick = useCallback((event, node) => {
    setModalNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setSearchQuery(''); // Clear search on pane click
    resetVisuals();
  }, [resetVisuals]);

  const closeInspector = useCallback(() => {
    setSelectedNode(null);
    setSearchQuery(''); // Clear search on inspector close
    resetVisuals();
  }, [resetVisuals]);

  const closeModal = useCallback(() => {
    setModalNode(null);
  }, []);

  return (
    <div className="w-full h-screen bg-gray-50 dark:bg-gray-900 flex flex-col transition-colors duration-200">
      {/* Top Navigation Bar */}
      <div className="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6 z-10 shadow-sm transition-colors duration-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white shadow-blue-200 shadow-lg">
            <Shield size={18} />
          </div>
          <div>
            <h1 className="font-bold text-gray-900 dark:text-white leading-tight">Security Explorer</h1>
            <p className="text-[10px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Automated Audit #4291</p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex-1 max-w-md mx-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              placeholder="Search nodes or API endpoints..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-100 dark:bg-gray-700 border-transparent focus:bg-white dark:focus:bg-gray-800 focus:border-blue-500 focus:ring-0 rounded-lg text-sm transition-all text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
            />
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={toggleDarkMode}
            className="p-2 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <div className="flex items-center gap-2 mr-4 border-r border-gray-200 dark:border-gray-700 pr-4">
            <button
              onClick={resetLayout}
              className="px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              title="Reset to auto-layout"
            >
              Reset Layout
            </button>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-700">
            {(() => {
              let color = 'bg-red-500';
              let textColor = 'text-red-700 dark:text-red-400';
              let text = 'ADB not connected';

              if (adbStatus.status === 'connected') {
                color = 'bg-green-500';
                textColor = 'text-green-700 dark:text-green-400';
                text = `Connected: ${adbStatus.device}`;
              } else if (adbStatus.status === 'unauthorized') {
                color = 'bg-yellow-500';
                textColor = 'text-yellow-700 dark:text-yellow-400';
                text = 'Device unauthorized';
              } else if (adbStatus.status === 'adb_missing') {
                color = 'bg-gray-500';
                textColor = 'text-gray-700 dark:text-gray-400';
                text = 'ADB not installed';
              } else if (adbStatus.status === 'offline') {
                color = 'bg-orange-500';
                textColor = 'text-orange-700 dark:text-orange-400';
                text = 'Device offline';
              }

              return (
                <>
                  <div className={`w-2 h-2 rounded-full ${color} animate-pulse`}></div>
                  <span className={`text-xs font-medium ${textColor}`}>
                    {text}
                  </span>
                </>
              );
            })()}
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onNodeDoubleClick={onNodeDoubleClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          className="bg-gray-50 dark:bg-gray-900 transition-colors duration-200"
        >
          <Background color={isDarkMode ? '#374151' : '#e5e7eb'} gap={20} size={1} />
          <Controls className="!bg-white dark:!bg-gray-800 !border-gray-200 dark:!border-gray-700 !shadow-lg !text-gray-600 dark:!text-gray-300 [&>button]:!border-b-gray-200 dark:[&>button]:!border-b-gray-700 [&>button:hover]:!bg-gray-50 dark:[&>button:hover]:!bg-gray-700" />
        </ReactFlow>

        {(isLoading || loadError) && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="px-6 py-4 bg-white/80 dark:bg-gray-900/80 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 text-center">
              {isLoading ? (
                <p className="text-sm font-medium text-gray-700 dark:text-gray-200">Loading graph data…</p>
              ) : (
                <>
                  <p className="text-sm font-semibold text-red-600 dark:text-red-400">Failed to load graph data</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">{loadError}</p>
                </>
              )}
            </div>
          </div>
        )}

        {/* Inspector Panel Overlay */}
        {selectedNode && (
          <InspectorPanel node={selectedNode} onClose={closeInspector} />
        )}

        {/* Node Details Modal */}
        {modalNode && (
          <NodeDetailsModal node={modalNode} onClose={closeModal} />
        )}
      </div>
    </div>
  );
}

export default App;
