import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ApolloProvider } from '@apollo/client';
import { client } from './lib/apollo';
import { isAuthenticated } from './lib/api';
import LoginPage from './pages/Login';
import DashboardPage from './pages/Dashboard';
import ResetPasswordPage from './pages/ResetPassword';

// Evaluated on mount so token expiry is caught when the user navigates back
// to a protected route, not just at the start of the session.
function PrivateRoute({ children }) {
  const [authed, setAuthed] = useState(null);

  useEffect(() => {
    setAuthed(isAuthenticated());
  }, []);

  if (authed === null) return null; // avoid flash before check completes
  return authed ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <ApolloProvider client={client}>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <DashboardPage />
              </PrivateRoute>
            }
          />
          {/* Redirect any unknown route — prevents unguarded pages from rendering */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </ApolloProvider>
  );
}
