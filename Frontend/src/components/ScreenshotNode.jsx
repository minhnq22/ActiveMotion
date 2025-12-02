import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';

const ScreenshotNode = ({ data, selected }) => {
    return (
        <div
            className={`relative w-[200px] bg-white dark:bg-gray-800 rounded-xl shadow-md border-2 transition-all duration-200 ${selected ? 'border-blue-500 shadow-lg ring-2 ring-blue-200 dark:ring-blue-900' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
        >
            {/* Phone Notch/Header Mockup */}
            <div className="h-6 bg-gray-100 dark:bg-gray-700 rounded-t-lg border-b border-gray-100 dark:border-gray-700 flex items-center justify-center">
                <div className="w-12 h-1 bg-gray-300 dark:bg-gray-500 rounded-full"></div>
            </div>

            {/* Screen Content */}
            <div className="p-2">
                <div className="w-full bg-gray-50 dark:bg-gray-900 rounded overflow-hidden relative group">
                    {data.screenshot ? (
                        <img
                            src={data.screenshot}
                            alt={data.label}
                            className="w-full h-auto object-contain"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400 dark:text-gray-500 text-xs">
                            No Image
                        </div>
                    )}

                    {/* Label Overlay */}
                    <div className="absolute bottom-0 left-0 right-0 bg-black/60 backdrop-blur-sm p-2 text-white">
                        <p className="text-xs font-medium truncate">{data.label}</p>
                    </div>
                </div>
            </div>

            {/* Handles */}
            {/* Handles */}
            <Handle
                type="target"
                position={Position.Left}
                className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white dark:!border-gray-800"
            />
            <Handle
                type="source"
                position={Position.Right}
                className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white dark:!border-gray-800"
            />
        </div>
    );
};

export default memo(ScreenshotNode);
