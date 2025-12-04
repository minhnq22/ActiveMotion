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
import { Shield, Share2, Menu, Search, Moon, Sun, Play, Square } from 'lucide-react';

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
  console.log('🚀 App component rendering...');
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
  const [adbStatus, setAdbStatus] = useState({ status: 'disconnected', device: null });

  // Load data function (extracted for reuse)
  const fetchGraphData = useCallback(async () => {
    try {
      setIsLoading(true);
      setLoadError(null);

      const response = await fetch(`${API_BASE_URL}/api/graph`, {
        signal: AbortSignal.timeout(5000), // 5 second timeout
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
      console.error('Failed to load graph data:', error);
      setLoadError(error.message);
      // Initialize with empty graph on error so UI is visible
      setNodes([]);
      setEdges([]);
    } finally {
      setIsLoading(false);
    }
  }, [setNodes, setEdges]);

  // WebSocket connection for live updates
  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;
    let shouldReconnect = true;

    const connectWebSocket = async () => {
      // Build WebSocket URL from API base URL
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      let wsUrl;

      if (apiBaseUrl.startsWith('http://')) {
        wsUrl = apiBaseUrl.replace('http://', 'ws://') + '/ws';
      } else if (apiBaseUrl.startsWith('https://')) {
        wsUrl = apiBaseUrl.replace('https://', 'wss://') + '/ws';
      } else {
        // Assume it's just host:port
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${apiBaseUrl}/ws`;
      }

      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('✅ WebSocket connected');
          // Clear any pending reconnection
          if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
          }
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'graph_updated') {
              console.log('📡 Graph update received:', message.message);
              // Refresh graph data when update is received
              fetchGraphData();
            } else if (message.type === 'adb_status') {
              // Real-time ADB status update with full details
              console.log('📱 ADB status update received (WebSocket):', message);
              setAdbStatus({
                status: message.status,           // connected | disconnected | unauthorized | offline | adb_missing | error
                device: message.device || null,   // Device serial
                message: message.message || 'Unknown status'  // Human-readable message
              });
            } else if (message.type === 'pong') {
              // Handle pong response if needed
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
          console.log('❌ WebSocket disconnected');
          ws = null;

          // Attempt to reconnect after 3 seconds if we should still be connected
          if (shouldReconnect) {
            reconnectTimeout = setTimeout(() => {
              console.log('🔄 Attempting to reconnect WebSocket...');
              connectWebSocket();
            }, 3000);
          }
        };
      } catch (error) {
        console.error('WebSocket connection error:', error);
      }
    };

    connectWebSocket();

    return () => {
      shouldReconnect = false;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (ws) {
        ws.close();
      }
    };
  }, [fetchGraphData]);

  // Load data on mount
  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);
  // ... rest of the component

  const [isRecording, setIsRecording] = useState(false);
  const isCapturingRef = React.useRef(false); // Prevent concurrent captures

  // Single screenshot capture
  useEffect(() => {
    if (isRecording) {
      const captureScreen = async () => {
        // Guard against concurrent requests
        if (isCapturingRef.current) {
          console.log("Capture already in progress, skipping...");
          return;
        }

        isCapturingRef.current = true;
        try {
          const response = await fetch(`${API_BASE_URL}/api/analyze-screen`, {
            method: 'POST',
          });
          if (!response.ok) {
            console.error("Capture failed");
            setIsRecording(false); // Stop on error
          } else {
            console.log("✅ Screen captured successfully");
            // WebSocket will trigger graph update automatically
            setIsRecording(false); // Stop after one capture
          }
        } catch (error) {
          console.error("Capture error:", error);
          setIsRecording(false);
        } finally {
          isCapturingRef.current = false;
        }
      };

      // Capture once
      captureScreen();
    } else {
      // Reset the capturing flag when stopping
      isCapturingRef.current = false;
    }

    return () => {
      isCapturingRef.current = false;
    };
  }, [isRecording, setNodes, setEdges]);

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

  const deleteNode = useCallback(async () => {
    if (!selectedNode) return;

    const nodeIdToDelete = selectedNode.id;

    try {
      // Delete on backend (DB + screenshots)
      const response = await fetch(`${API_BASE_URL}/api/nodes/${encodeURIComponent(nodeIdToDelete)}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        console.error('Failed to delete node on server', response.status);
        return;
      }

      // Optimistically update local graph state
      setNodes((nds) => nds.filter((n) => n.id !== nodeIdToDelete));
      setEdges((eds) => eds.filter((e) => e.source !== nodeIdToDelete && e.target !== nodeIdToDelete));

      // Close the inspector and reset visuals
      setSelectedNode(null);
      resetVisuals();
    } catch (error) {
      console.error('Error deleting node:', error);
    }
  }, [selectedNode, setNodes, setEdges, resetVisuals]);

  console.log('📱 About to render JSX, nodes:', nodes.length, 'edges:', edges.length);

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
              onClick={() => {
                if (!isCapturingRef.current && adbStatus.status === 'connected') {
                  setIsRecording(!isRecording);
                }
              }}
              disabled={isCapturingRef.current || adbStatus.status !== 'connected'}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${isRecording
                ? 'bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50'
                : 'bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50'
                }`}
              title={
                adbStatus.status !== 'connected'
                  ? "Device not connected"
                  : (isRecording ? "Stop Capture" : "Start Capture")
              }
            >
              {isRecording ? <Square size={14} fill="currentColor" /> : <Play size={14} fill="currentColor" />}
              {isRecording ? "Stop" : "Start"}
            </button>
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
      <div className="flex-1 relative bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
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
        >
          <Background color={isDarkMode ? '#374151' : '#e5e7eb'} gap={20} size={1} />
          <Controls className="!bg-white dark:!bg-gray-800 !border-gray-200 dark:!border-gray-700 !shadow-lg !text-gray-600 dark:!text-gray-300 [&>button]:!border-b-gray-200 dark:[&>button]:!border-b-gray-700 [&>button:hover]:!bg-gray-50 dark:[&>button:hover]:!bg-gray-700" />
        </ReactFlow>

        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="px-6 py-4 bg-white/80 dark:bg-gray-900/80 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 text-center">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-200">Loading graph data…</p>
            </div>
          </div>
        )}

        {loadError && (
          <div className="absolute bottom-4 right-4 max-w-md pointer-events-auto">
            <div className="px-4 py-3 bg-red-50 dark:bg-red-900/20 rounded-lg shadow-lg border border-red-200 dark:border-red-800">
              <p className="text-sm font-semibold text-red-600 dark:text-red-400">Connection Error</p>
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">{loadError}</p>
              <p className="text-xs text-red-500 dark:text-red-500 mt-2">Make sure the backend is running at {API_BASE_URL}</p>
              <button
                onClick={() => {
                  setIsLoading(true);
                  setLoadError(null);
                  fetchGraphData();
                }}
                className="mt-2 text-xs px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Inspector Panel Overlay */}
        {selectedNode && (
          <InspectorPanel node={selectedNode} onClose={closeInspector} onDelete={deleteNode} />
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
