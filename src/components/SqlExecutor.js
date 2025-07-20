// src/components/SqlExecutor.js
import React, { useState, useRef, useEffect } from 'react';
import {
  Play,
  Download,
  Copy,
  Check,
  AlertTriangle,
  Database,
  Clock,
  RotateCcw,
  FileText,
  Settings
} from 'lucide-react';

import LoadingSpinner from './LoadingSpinner';
import authService from '../services/authService';
import './SqlExecutor.css';

const SqlExecutor = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [executionTime, setExecutionTime] = useState(null);
  const [history, setHistory] = useState([]);
  const [selectedHistory, setSelectedHistory] = useState('');
  const [copied, setCopied] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  
  const textareaRef = useRef(null);

  useEffect(() => {
    loadQueryHistory();
  }, []);

  const loadQueryHistory = async () => {
    try {
      const response = await authService.apiCall('/admin/sql/history');
      if (response?.ok) {
        const data = await response.json();
        setHistory(data.history || []);
      }
    } catch (error) {
      console.error('Failed to load query history:', error);
    }
  };

  const executeQuery = async () => {
    if (!query.trim()) {
      setError('Please enter a SQL query');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults(null);
    
    const startTime = performance.now();

    try {
      const response = await authService.apiCall('/admin/sql/execute', {
        method: 'POST',
        body: JSON.stringify({
          query: query.trim(),
          page: currentPage,
          per_page: rowsPerPage
        })
      });

      const endTime = performance.now();
      setExecutionTime(endTime - startTime);

      if (response?.ok) {
        const data = await response.json();
        setResults(data);
        setTotalPages(data.pagination?.total_pages || 1);
        
        // Add to history
        const historyItem = {
          query: query.trim(),
          timestamp: new Date().toISOString(),
          success: true,
          row_count: data.row_count
        };
        setHistory(prev => [historyItem, ...prev.slice(0, 19)]); // Keep last 20 queries
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Query execution failed');
      }
    } catch (error) {
      console.error('SQL execution error:', error);
      setError(error.message);
      
      // Add failed query to history
      const historyItem = {
        query: query.trim(),
        timestamp: new Date().toISOString(),
        success: false,
        error: error.message
      };
      setHistory(prev => [historyItem, ...prev.slice(0, 19)]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();
      executeQuery();
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const exportResults = () => {
    if (!results?.data) return;

    const csvContent = [
      results.columns.join(','),
      ...results.data.map(row => 
        results.columns.map(col => 
          typeof row[col] === 'string' && row[col].includes(',') 
            ? `"${row[col]}"` 
            : row[col] || ''
        ).join(',')
      )
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${new Date().toISOString().slice(0, 19)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const loadHistoryQuery = (historyQuery) => {
    setQuery(historyQuery);
    setSelectedHistory(historyQuery);
  };

  const clearResults = () => {
    setResults(null);
    setError(null);
    setExecutionTime(null);
    setCurrentPage(1);
  };

  return (
    <div className="sql-executor">
      <div className="sql-header">
        <h2>
          <Database size={24} />
          SQL Console
        </h2>
        <p className="sql-subtitle">
          Execute SQL queries with real-time results and export capabilities
        </p>
      </div>

      <div className="sql-content">
        {/* Query Input Section */}
        <div className="query-section">
          <div className="query-header">
            <h3>Query Editor</h3>
            <div className="query-actions">
              <button
                onClick={clearResults}
                className="btn btn-secondary"
                disabled={!results && !error}
              >
                <RotateCcw size={16} />
                Clear
              </button>
              <button
                onClick={executeQuery}
                className="btn btn-primary"
                disabled={isLoading || !query.trim()}
              >
                {isLoading ? (
                  <LoadingSpinner size="small" />
                ) : (
                  <Play size={16} />
                )}
                Execute (Ctrl+Enter)
              </button>
            </div>
          </div>

          <div className="query-input-container">
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter your SQL query here..."
              className="query-input"
              rows={8}
            />
            
            {query && (
              <button
                onClick={() => copyToClipboard(query)}
                className="copy-btn"
                title="Copy Query"
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
              </button>
            )}
          </div>

          {/* Query Settings */}
          <div className="query-settings">
            <label>
              Rows per page:
              <select
                value={rowsPerPage}
                onChange={(e) => setRowsPerPage(Number(e.target.value))}
                className="rows-select"
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={500}>500</option>
              </select>
            </label>
          </div>
        </div>

        {/* Query History Sidebar */}
        <div className="history-section">
          <h3>Query History</h3>
          <div className="history-list">
            {history.length > 0 ? (
              history.map((item, index) => (
                <div
                  key={index}
                  className={`history-item ${item.success ? 'success' : 'error'} ${
                    selectedHistory === item.query ? 'selected' : ''
                  }`}
                  onClick={() => loadHistoryQuery(item.query)}
                >
                  <div className="history-query">
                    {item.query.length > 100 
                      ? `${item.query.substring(0, 100)}...`
                      : item.query
                    }
                  </div>
                  <div className="history-meta">
                    <span className="history-time">
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </span>
                    {item.success ? (
                      <span className="history-result">
                        {item.row_count} rows
                      </span>
                    ) : (
                      <span className="history-error">Failed</span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-history">
                <FileText size={32} />
                <p>No query history</p>
              </div>
            )}
          </div>
        </div>

        {/* Results Section */}
        <div className="results-section">
          {/* Execution Info */}
          {(executionTime || error) && (
            <div className="execution-info">
              {executionTime && (
                <div className="execution-time">
                  <Clock size={16} />
                  Executed in {executionTime.toFixed(2)}ms
                </div>
              )}
              {error && (
                <div className="execution-error">
                  <AlertTriangle size={16} />
                  {error}
                </div>
              )}
            </div>
          )}

          {/* Results Display */}
          {results && (
            <div className="results-container">
              <div className="results-header">
                <div className="results-info">
                  <h3>Results</h3>
                  <span className="results-count">
                    {results.row_count} rows
                    {results.pagination && ` (Page ${currentPage} of ${totalPages})`}
                  </span>
                </div>
                <div className="results-actions">
                  <button
                    onClick={exportResults}
                    className="btn btn-secondary"
                  >
                    <Download size={16} />
                    Export CSV
                  </button>
                </div>
              </div>

              {results.data && results.data.length > 0 ? (
                <>
                  <div className="results-table-container">
                    <table className="results-table">
                      <thead>
                        <tr>
                          {results.columns.map((column, index) => (
                            <th key={index}>{column}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {results.data.map((row, index) => (
                          <tr key={index}>
                            {results.columns.map((column, colIndex) => (
                              <td key={colIndex}>
                                {row[column] !== null && row[column] !== undefined
                                  ? String(row[column])
                                  : <span className="null-value">NULL</span>
                                }
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="pagination">
                      <button
                        onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                        disabled={currentPage === 1}
                        className="pagination-btn"
                      >
                        Previous
                      </button>
                      <span className="pagination-info">
                        Page {currentPage} of {totalPages}
                      </span>
                      <button
                        onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                        disabled={currentPage === totalPages}
                        className="pagination-btn"
                      >
                        Next
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-results">
                  <Database size={48} />
                  <p>Query executed successfully but returned no results</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SqlExecutor;