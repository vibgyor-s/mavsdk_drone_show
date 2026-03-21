// src/components/ErrorBoundary.test.js
import React from 'react';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from './ErrorBoundary';

// Mock the logService — must mock before ErrorBoundary loads it
jest.mock('../services/logService', () => ({
  reportFrontendError: jest.fn().mockResolvedValue({ status: 'received' }),
}));

const ThrowError = () => {
  throw new Error('Test crash');
};

describe('ErrorBoundary', () => {
  const originalError = console.error;
  beforeAll(() => { console.error = jest.fn(); });
  afterAll(() => { console.error = originalError; });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Safe content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Safe content')).toBeInTheDocument();
  });

  test('renders fallback UI on error', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Test crash')).toBeInTheDocument();
  });

  test('reports error to backend', () => {
    const { reportFrontendError } = require('../services/logService');
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    expect(reportFrontendError).toHaveBeenCalledWith(
      'ERROR',
      'React crash: Test crash',
      expect.objectContaining({ stack: expect.any(String) }),
    );
  });
});
