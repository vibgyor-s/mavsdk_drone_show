// src/components/ErrorBoundary.js
import React from 'react';
import { reportFrontendError } from '../services/logService';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // Report to backend — fire-and-forget
    try {
      const result = reportFrontendError('ERROR', `React crash: ${error.message}`, {
        stack: error.stack,
        componentStack: errorInfo?.componentStack,
      });
      if (result && typeof result.catch === 'function') {
        result.catch(() => {
          // Backend unreachable — nothing we can do
        });
      }
    } catch {
      // reportFrontendError itself failed — nothing we can do
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-fallback">
          <h2>Something went wrong</h2>
          <p>The application encountered an unexpected error. This has been reported automatically.</p>
          {this.state.error && (
            <pre>{this.state.error.message}</pre>
          )}
          <button
            onClick={this.handleReset}
            style={{
              padding: '8px 16px',
              background: 'var(--color-primary)',
              color: 'var(--color-primary-text)',
              border: 'none',
              borderRadius: 'var(--border-radius-sm)',
              cursor: 'pointer',
            }}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
