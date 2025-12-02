import React from 'react';
import { X, Globe, Clock, CheckCircle, AlertCircle } from 'lucide-react';

const NodeDetailsModal = ({ node, onClose }) => {
    if (!node) return null;

    const { data } = node;
    const parserItems = data.parser?.parsedContentList || [];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="p-6 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between bg-gray-50 dark:bg-gray-900">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{data.label}</h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Node ID: {node.id}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-gray-500 dark:text-gray-400 transition-colors"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    <div className="space-y-8">
                        {/* Description First */}
                        <div>
                            <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-2">
                                Description
                            </h3>
                            <p className="text-gray-600 dark:text-gray-300 leading-relaxed bg-gray-50 dark:bg-gray-900 p-4 rounded-xl border border-gray-100 dark:border-gray-700">
                                {data.description || 'No description available.'}
                            </p>
                        </div>

                        {/* Two-column layout below description */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            {/* Left Column: Screenshot & Annotated */}
                            <div className="space-y-6">
                                <div className="space-y-4">
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3">
                                            Screenshot
                                        </h3>
                                        <div className="w-full max-w-xs mx-auto bg-gray-100 dark:bg-gray-700 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-600 shadow-sm">
                                            <img src={data.screenshot} alt={data.label} className="w-full h-auto object-contain" />
                                        </div>
                                    </div>

                                    {data.annotatedScreenshot && (
                                        <div>
                                            <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3">
                                                Annotated Screenshot
                                            </h3>
                                            <div className="w-full max-w-xs mx-auto bg-gray-100 dark:bg-gray-700 rounded-xl overflow-hidden border border-blue-200 dark:border-blue-800 shadow-sm">
                                                <img src={data.annotatedScreenshot} alt={`${data.label} annotated`} className="w-full h-auto object-contain" />
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Right Column: Traffic & Parser Details */}
                            <div className="space-y-6">
                            <div>
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">Network Traffic</h3>
                                    <span className="bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-xs font-bold px-2.5 py-0.5 rounded-full">
                                        {data.traffic?.length || 0} Requests
                                    </span>
                                </div>

                                <div className="space-y-3">
                                    {data.traffic && data.traffic.length > 0 ? (
                                        data.traffic.map((req, idx) => (
                                            <div key={idx} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:shadow-md transition-shadow">
                                                <div className="flex items-center justify-between mb-3">
                                                    <span className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wide ${req.method === 'GET' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                                                        req.method === 'POST' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                                            req.method === 'DELETE' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                                                                'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                                                        }`}>
                                                        {req.method}
                                                    </span>
                                                    <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 px-2 py-1 rounded-full">
                                                        <Clock size={14} />
                                                        {req.duration}
                                                    </div>
                                                </div>

                                                <div className="flex items-start gap-3 mb-3">
                                                    <Globe size={16} className="text-gray-400 dark:text-gray-500 mt-0.5 flex-shrink-0" />
                                                    <code className="text-sm text-gray-700 dark:text-gray-300 break-all font-mono bg-gray-50 dark:bg-gray-700 px-1 rounded">{req.url}</code>
                                                </div>

                                                <div className="flex items-center gap-2 pt-3 border-t border-gray-50 dark:border-gray-700">
                                                    {req.status >= 200 && req.status < 300 ? (
                                                        <CheckCircle size={16} className="text-green-500" />
                                                    ) : (
                                                        <AlertCircle size={16} className="text-amber-500" />
                                                    )}
                                                    <span className={`text-sm font-medium ${req.status >= 200 && req.status < 300 ? 'text-green-600' : 'text-amber-600'
                                                        }`}>
                                                        Status {req.status}
                                                    </span>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-center py-12 bg-gray-50 dark:bg-gray-900 rounded-xl border border-dashed border-gray-200 dark:border-gray-700">
                                            <p className="text-gray-400 dark:text-gray-500">No traffic recorded for this step.</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div>
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">Parsed UI Elements</h3>
                                    <span className="bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 text-xs font-bold px-2.5 py-0.5 rounded-full">
                                        {parserItems.length} Elements
                                    </span>
                                </div>
                                <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                                    {parserItems.length > 0 ? (
                                        parserItems.map((item, idx) => (
                                            <div key={idx} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                                        {item.type || 'unknown'}
                                                    </span>
                                                    <span
                                                        className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase ${item.interactivity
                                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                                                            : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                                                            }`}
                                                    >
                                                        {item.interactivity ? 'Interactive' : 'Static'}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-gray-800 dark:text-gray-100">
                                                    {item.content || 'No content'}
                                                </p>
                                                <div className="flex items-center justify-between text-[10px] text-gray-500 dark:text-gray-400 pt-1">
                                                    <span className="truncate max-w-[60%]">
                                                        Source: {item.source || 'unknown'}
                                                    </span>
                                                    {Array.isArray(item.bbox) && item.bbox.length === 4 && (
                                                        <span>
                                                            bbox: {item.bbox.map((v) => v.toFixed ? v.toFixed(2) : v).join(', ')}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-center py-6 bg-gray-50 dark:bg-gray-900 rounded-xl border border-dashed border-gray-200 dark:border-gray-700">
                                            <p className="text-xs text-gray-400 dark:text-gray-500">No parser data available for this node.</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-6 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors shadow-sm"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default NodeDetailsModal;
