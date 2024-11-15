import React, { createContext, useContext, useState } from 'react';

const TabsContext = createContext();

export const Tabs = ({ children, defaultValue, className = '' }) => {
  const [selectedTab, setSelectedTab] = useState(defaultValue);

  return (
    <TabsContext.Provider value={{ selectedTab, setSelectedTab }}>
      <div className={className}>
        {children}
      </div>
    </TabsContext.Provider>
  );
};

export const TabsList = ({ children, className = '' }) => (
  <div className={`flex space-x-1 border-b border-gray-200 mb-6 ${className}`}>
    {children}
  </div>
);

export const TabsTrigger = ({ value, children, className = '' }) => {
  const { selectedTab, setSelectedTab } = useContext(TabsContext);
  const isSelected = selectedTab === value;

  return (
    <button
      className={`
        px-4 py-2 rounded-t-lg font-medium text-sm transition-colors duration-200
        ${isSelected 
          ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50' 
          : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
        }
        ${className}
      `}
      onClick={() => setSelectedTab(value)}
    >
      {children}
    </button>
  );
};

export const TabsContent = ({ value, children, className = '' }) => {
  const { selectedTab } = useContext(TabsContext);

  if (selectedTab !== value) return null;

  return (
    <div className={`animate-fadeIn ${className}`}>
      {children}
    </div>
  );
};