import React, { useState } from 'react';
import { X, Smartphone, Activity, Globe, Clock, CheckCircle, AlertCircle, Trash2 } from 'lucide-react';

const InspectorPanel = ({ node, onClose, onDelete }) => {
    const [activeTab, setActiveTab] = useState('context');

    if (!node) return null;

    const { data } = node;
    // Handle both old array format and new Vision-First object format
    const mergedContent = data.parser?.mergedContent || [];
    const parserItems = Array.isArray(mergedContent)
        ? mergedContent  // Old format: direct array
        : (mergedContent.elements || []);  // New Vision-First format: { screen_state, elements }

    const screenState = Array.isArray(mergedContent)
        ? null
        : (mergedContent.screen_state || null);

    // Count interactive elements (support both old and new field names)
    const interactiveCount = parserItems.filter((item) =>
        item.status?.clickable || item.adb_attributes?.clickable
    ).length;

    return (
        <div className="absolute top-4 right-4 w-96 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden h-[calc(100vh-2rem)] z-50 animate-in slide-in-from-right-10 duration-200">
            {/* Header */}
            <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between bg-gray-50/50 dark:bg-gray-900/50">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400">
                        <Smartphone size={18} />
                    </div>
                    <div>
                        <h2 className="font-semibold text-gray-900 dark:text-white">{data.label}</h2>
                        <p className="text-xs text-gray-500 dark:text-gray-400">ID: {node.id}</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={onDelete}
                        className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-md text-red-500 dark:text-red-400 transition-colors"
                        title="Delete Node"
                    >
                        <Trash2 size={18} />
                    </button>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md text-gray-500 dark:text-gray-400 transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-100 dark:border-gray-700">
                <button
                    onClick={() => setActiveTab('context')}
                    className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'context'
                        ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-50/30 dark:bg-blue-900/20'
                        : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'
                        } `}
                >
                    Context
                </button>
                <button
                    onClick={() => setActiveTab('traffic')}
                    className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'traffic'
                        ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-50/30 dark:bg-blue-900/20'
                        : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'
                        } `}
                >
                    Traffic ({data.traffic?.length || 0})
                </button>
                <button
                    onClick={() => setActiveTab('parser')}
                    className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'parser'
                        ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-50/30 dark:bg-blue-900/20'
                        : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'
                        } `}
                >
                    Parser ({parserItems.length || 0})
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
                {activeTab === 'context' && (
                    <div className="space-y-6">
                        <div className="space-y-4">
                            <div>
                                <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">Screen Preview</h3>
                                <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600">
                                    <img src={data.screenshot} alt={data.label} className="w-full h-auto object-contain" />
                                </div>
                            </div>

                            {data.annotatedScreenshot && (
                                <div>
                                    <h3 className="text-xs font-semibold text-blue-500 dark:text-blue-400 uppercase tracking-wider mb-3">Annotated View</h3>
                                    <div className="w-full bg-blue-50/50 dark:bg-blue-900/20 rounded-lg overflow-hidden border border-blue-200 dark:border-blue-800">
                                        <img src={data.annotatedScreenshot} alt={`${data.label} annotated`} className="w-full h-auto object-contain" />
                                    </div>
                                </div>
                            )}
                        </div>

                        <div>
                            <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Description</h3>
                            <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed bg-gray-50 dark:bg-gray-900 p-3 rounded-lg border border-gray-100 dark:border-gray-700">
                                {data.description || 'No description available.'}
                            </p>
                        </div>
                    </div>
                )}
                {activeTab === 'traffic' && (
                    <div className="space-y-3">
                        {data.traffic && data.traffic.length > 0 ? (
                            data.traffic.map((req, idx) => (
                                <div key={idx} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 hover:shadow-sm transition-shadow">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${req.method === 'GET' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                                            req.method === 'POST' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                                req.method === 'DELETE' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                                                    'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                                            } `}>
                                            {req.method}
                                        </span>
                                        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                                            <Clock size={12} />
                                            {req.duration}
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-2 mb-2">
                                        <Globe size={14} className="text-gray-400 dark:text-gray-500 mt-0.5 flex-shrink-0" />
                                        <code className="text-xs text-gray-700 dark:text-gray-300 break-all font-mono">{req.url}</code>
                                    </div>
                                    <div className="flex items-center gap-1.5 pt-2 border-t border-gray-50 dark:border-gray-700">
                                        {req.status >= 200 && req.status < 300 ? (
                                            <CheckCircle size={12} className="text-green-500" />
                                        ) : (
                                            <AlertCircle size={12} className="text-amber-500" />
                                        )}
                                        <span className={`text-xs font-medium ${req.status >= 200 && req.status < 300 ? 'text-green-600' : 'text-amber-600'
                                            } `}>
                                            Status {req.status}
                                        </span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="text-center py-8 text-gray-400">
                                <Activity size={32} className="mx-auto mb-2 opacity-50" />
                                <p className="text-sm">No traffic recorded</p>
                            </div>
                        )}
                    </div>
                )}
                {activeTab === 'parser' && (
                    <div className="space-y-4">
                        {/* Screen State Info (Vision-First only) */}
                        {screenState && (
                            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-blue-700 dark:text-blue-300 mb-2">Screen State</h4>
                                <div className="flex items-center gap-2 text-xs">
                                    {screenState.can_scroll_vertical ? (
                                        <>
                                            <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-semibold">
                                                SCROLLABLE
                                            </span>
                                            <span className="text-gray-600 dark:text-gray-400">
                                                {screenState.scrollable_areas?.length || 0} area(s)
                                            </span>
                                        </>
                                    ) : (
                                        <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 font-semibold">
                                            STATIC
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {parserItems.length > 0 ? (
                            <>
                                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                                    <span>{parserItems.length} elements parsed</span>
                                    <span className="px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 font-medium">
                                        {interactiveCount} interactive
                                    </span>
                                </div>
                                <div className="space-y-2">
                                    {parserItems.map((item, idx) => {
                                        // Support both old and new field names
                                        const displayType = item.type || item.role || 'Unknown';
                                        const displayContent = item.content || item.text_content || '';
                                        const displayDesc = item.adb_attributes?.content_desc || item.description || '';
                                        const source = item.source || 'unknown';

                                        return (
                                            <div
                                                key={item.uid || idx}
                                                className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-2"
                                            >
                                                {/* Header: Type + Source Badge */}
                                                <div className="flex items-center justify-between">
                                                    <span className="text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-300">
                                                        {displayType}
                                                    </span>
                                                    <span
                                                        className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase ${source === 'merged' || source === 'vision_enriched'
                                                                ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
                                                                : source === 'adb'
                                                                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                                                                    : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                                                            }`}
                                                    >
                                                        {source === 'vision_enriched' ? 'V+ADB' : source}
                                                    </span>
                                                </div>

                                                {/* Content */}
                                                {displayContent && (
                                                    <p className="text-xs text-gray-900 dark:text-gray-100 font-medium bg-gray-50 dark:bg-gray-900 p-2 rounded">
                                                        {displayContent}
                                                    </p>
                                                )}

                                                {/* Description */}
                                                {displayDesc && (
                                                    <p className="text-xs text-gray-600 dark:text-gray-400 italic">
                                                        {displayDesc}
                                                    </p>
                                                )}

                                                {/* Bounds */}
                                                {Array.isArray(item.bounds) && item.bounds.length === 4 && (
                                                    <div className="text-[9px] text-gray-500 dark:text-gray-500 font-mono">
                                                        [{item.bounds.join(', ')}]
                                                    </div>
                                                )}

                                                {/* Status Badges - Support both old (status) and new (adb_attributes) */}
                                                {(item.status || item.adb_attributes) && (
                                                    <div className="flex flex-wrap gap-1">
                                                        {(item.status?.clickable || item.adb_attributes?.clickable) && (
                                                            <span className="text-[8px] px-1 py-0.5 rounded bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 font-semibold">
                                                                CLICK
                                                            </span>
                                                        )}
                                                        {(item.status?.scrollable || item.adb_attributes?.scrollable) && (
                                                            <span className="text-[8px] px-1 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 font-semibold">
                                                                SCROLL
                                                            </span>
                                                        )}
                                                        {(item.status?.editable || item.adb_attributes?.editable) && (
                                                            <span className="text-[8px] px-1 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 font-semibold">
                                                                EDIT
                                                            </span>
                                                        )}
                                                        {(item.status?.checked || item.adb_attributes?.checked) && (
                                                            <span className="text-[8px] px-1 py-0.5 rounded bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400 font-semibold">
                                                                ✓
                                                            </span>
                                                        )}
                                                        {(item.status?.selected || item.adb_attributes?.selected) && (
                                                            <span className="text-[8px] px-1 py-0.5 rounded bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400 font-semibold">
                                                                SEL
                                                            </span>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </>
                        ) : (
                            <div className="text-center py-8 text-gray-400">
                                <Activity size={32} className="mx-auto mb-2 opacity-50" />
                                <p className="text-sm">No parser data for this screen</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default InspectorPanel;
