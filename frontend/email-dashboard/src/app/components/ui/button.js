// components/ui/button.js

import React from 'react';

export const Button = ({ children, onClick, className, variant = 'solid' }) => {
  const baseStyles = 'px-4 py-2 rounded-md text-white';
  const variantStyles = variant === 'outline' ? 'border border-gray-300 bg-transparent' : 'bg-blue-500';

  return (
    <button onClick={onClick} className={`${baseStyles} ${variantStyles} ${className}`}>
      {children}
    </button>
  );
};
