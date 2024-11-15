// components/ui/textarea.js

import React from 'react';

export const Textarea = ({ value, onChange, placeholder, className }) => (
  <textarea
    value={value}
    onChange={onChange}
    placeholder={placeholder}
    className={`px-4 py-2 border rounded-md w-full ${className}`}
  />
);
