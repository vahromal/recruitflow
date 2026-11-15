/// <reference types="vitest" />
import React from 'react';
import ReactDOM from 'react-dom/client';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { BrowserRouter } from 'react-router-dom';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import App from './App';
import { AuthProvider } from './hooks/useAuth';
import { fetchWithRetry, healthUrl } from './api/base';

// On GitHub Pages the app is served from /<repo>/ — React Router needs the same prefix.
const basename = import.meta.env.BASE_URL.replace(/\/$/, '') || '/';

// Wake a sleeping free-tier backend as soon as the app opens.
fetchWithRetry(healthUrl(), undefined, { attempts: 3 }).catch(() => {});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="light">
      <Notifications position="top-right" />
      <BrowserRouter basename={basename}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </MantineProvider>
  </React.StrictMode>
);
