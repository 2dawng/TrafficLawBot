import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MessageContent({ content }) {
    return (
        <div className="markdown-content leading-[1.3] text-sm">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    // Customize heading styles
                    h1: ({ node, ...props }) => (
                        <h1 className="text-2xl font-bold leading-tight" {...props} />
                    ),
                    h2: ({ node, ...props }) => (
                        <h2 className="text-xl font-bold leading-tight" {...props} />
                    ),
                    h3: ({ node, ...props }) => (
                        <h3 className="text-lg font-semibold leading-tight" {...props} />
                    ),
                    // Customize paragraph
                    p: ({ node, ...props }) => (
                        <p className="mb-0" {...props} />
                    ),
                    // Customize lists
                    ul: ({ node, ...props }) => (
                        <ul className="list-disc list-inside ml-4 my-0" {...props} />
                    ),
                    ol: ({ node, ...props }) => (
                        <ol className="list-decimal list-inside ml-2 my-0" {...props} />
                    ),
                    li: ({ node, ...props }) => (
                        <li className="mb-0" {...props} />
                    ),
                    // Customize code blocks
                    code: ({ node, inline, ...props }) => {
                        return inline ? (
                            <code
                                className="bg-gray-200 text-gray-800 px-1.5 py-0.5 rounded text-xs font-mono"
                                {...props}
                            />
                        ) : (
                            <code
                                className="block bg-gray-100 text-gray-800 p-2 rounded-lg text-xs font-mono overflow-x-auto my-1"
                                {...props}
                            />
                        );
                    },
                    // Customize blockquotes
                    blockquote: ({ node, ...props }) => (
                        <blockquote
                            className="border-l-4 border-gray-300 pl-3 italic text-gray-700 my-1"
                            {...props}
                        />
                    ),
                    // Customize links
                    a: ({ node, ...props }) => (
                        <a
                            className="text-blue-600 hover:text-blue-800 underline"
                            target="_blank"
                            rel="noopener noreferrer"
                            {...props}
                        />
                    ),
                    // Customize tables
                    table: ({ node, ...props }) => (
                        <div className="overflow-x-auto my-1">
                            <table className="min-w-full border-collapse border border-gray-300" {...props} />
                        </div>
                    ),
                    thead: ({ node, ...props }) => (
                        <thead className="bg-gray-100" {...props} />
                    ),
                    th: ({ node, ...props }) => (
                        <th className="border border-gray-300 px-3 py-2 text-left font-semibold" {...props} />
                    ),
                    td: ({ node, ...props }) => (
                        <td className="border border-gray-300 px-3 py-2" {...props} />
                    ),
                    // Customize strong/bold
                    strong: ({ node, ...props }) => (
                        <strong className="font-bold" {...props} />
                    ),
                    // Customize emphasis/italic
                    em: ({ node, ...props }) => (
                        <em className="italic" {...props} />
                    ),
                    // Horizontal rule
                    hr: ({ node, ...props }) => (
                        <hr className="my-2 border-gray-300" {...props} />
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
