// components/ui/card.js

export const Card = ({ children, className = '' }) => (
    <div className={`bg-white rounded-xl shadow-md overflow-hidden border border-gray-100 ${className}`}>
      {children}
    </div>
  );
  
  export const CardHeader = ({ children, className = '' }) => (
    <div className={`px-6 py-4 border-b border-gray-100 bg-gray-50 ${className}`}>
      {children}
    </div>
  );
  
  export const CardTitle = ({ children, className = '' }) => (
    <h2 className={`text-xl font-semibold text-gray-800 ${className}`}>
      {children}
    </h2>
  );
  
  export const CardContent = ({ children, className = '' }) => (
    <div className={`p-6 ${className}`}>
      {children}
    </div>
  );
  