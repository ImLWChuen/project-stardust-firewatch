import React from 'react';

export default function Button({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded text-sm font-medium transition" {...props}>
      {children}
    </button>
  );
}
