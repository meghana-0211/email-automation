// components/ui/tabs.js

import React from 'react';

export const Tabs = ({ children, defaultValue }) => {
  const [selectedTab, setSelectedTab] = React.useState(defaultValue);

  return (
    <div>
      {React.Children.map(children, (child) =>
        React.cloneElement(child, {
          selectedTab,
          setSelectedTab,
        })
      )}
    </div>
  );
};

export const TabsList = ({ children }) => (
  <div className="flex space-x-4 border-b">{children}</div>
);

export const TabsTrigger = ({ value, children, selectedTab, setSelectedTab }) => (
  <button
    className={`py-2 px-4 ${selectedTab === value ? 'border-b-2 border-blue-500' : ''}`}
    onClick={() => setSelectedTab(value)}
  >
    {children}
  </button>
);

export const TabsContent = ({ value, children, selectedTab }) => (
  <div className={`${selectedTab === value ? 'block' : 'hidden'}`}>{children}</div>
);
