// src/components/LoadingSpinner.js
import React from 'react';
import { Loader2 } from 'lucide-react';
import './LoadingSpinner.css';

const LoadingSpinner = ({ 
  size = 'medium', 
  text = null, 
  className = '', 
  color = 'primary' 
}) => {
  const getSizeClass = () => {
    switch (size) {
      case 'small':
        return 'spinner-small';
      case 'large':
        return 'spinner-large';
      case 'xl':
        return 'spinner-xl';
      default:
        return 'spinner-medium';
    }
  };

  const getIconSize = () => {
    switch (size) {
      case 'small':
        return 16;
      case 'large':
        return 32;
      case 'xl':
        return 48;
      default:
        return 24;
    }
  };

  return (
    <div className={`loading-spinner ${getSizeClass()} ${color} ${className}`}>
      <Loader2 
        size={getIconSize()} 
        className="spinner-icon" 
      />
      {text && <span className="spinner-text">{text}</span>}
    </div>
  );
};

// Inline Loading Spinner for smaller contexts
export const InlineSpinner = ({ size = 16, className = '' }) => (
  <Loader2 
    size={size} 
    className={`inline-spinner ${className}`} 
  />
);

// Full Screen Loading Overlay
export const FullScreenLoader = ({ text = 'Loading...' }) => (
  <div className="fullscreen-loader">
    <div className="loader-content">
      <LoadingSpinner size="large" text={text} />
    </div>
  </div>
);

export default LoadingSpinner;