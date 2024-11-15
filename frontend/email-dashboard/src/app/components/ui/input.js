// components/ui/input.js

import React from 'react';

export const Input = ({ type, placeholder, value, onChange, className }) => (
  <input
    type={type}
    placeholder={placeholder}
    value={value}
    onChange={onChange}
    className={`px-4 py-2 border rounded-md w-full ${className}`}
  />
);
