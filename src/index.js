// src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

// Hide the initial loading spinner when React loads
const hideInitialLoading = () => {
  const initialLoading = document.getElementById('initial-loading');
  if (initialLoading) {
    initialLoading.style.display = 'none';
  }
  document.body.classList.add('app-loaded');
};

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Hide loading spinner after React renders
setTimeout(hideInitialLoading, 100);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();