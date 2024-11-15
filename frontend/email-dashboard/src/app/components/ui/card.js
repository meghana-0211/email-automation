// components/ui/card.js

import React from 'react';

export const Card = ({ children }) => (
  <div className="border rounded-lg shadow-lg bg-white overflow-hidden">
    {children}
  </div>
);

export const CardHeader = ({ children }) => (
  <div className="bg-gray-100 p-4 border-b">{children}</div>
);

export const CardTitle = ({ children }) => (
  <h2 className="text-xl font-semibold">{children}</h2>
);

export const CardContent = ({ children }) => (
  <div className="p-4">{children}</div>
);
