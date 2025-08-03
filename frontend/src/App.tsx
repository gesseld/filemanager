import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Settings from './components/Settings/Settings';
import UserProfileForm from './components/Settings/UserProfileForm';
import NotificationPreferences from './components/Settings/NotificationPreferences';
import ThemeSelector from './components/Settings/ThemeSelector';
import SecuritySettings from './components/Settings/SecuritySettings';
import TagManagement from './components/TagManagement/TagManagement';
import TagList from './components/TagManagement/TagList';
import TagEditor from './components/TagManagement/TagEditor';
import TagAssigner from './components/TagManagement/TagAssigner';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from 'react-hot-toast';
import ErrorBoundary from './components/ErrorBoundary';

import './App.css';
import Upload from './components/Upload/Upload';
import { SearchBar as Search } from './components/Search';
import { DocumentViewer } from './components/DocumentViewer';
import Dashboard from './components/Dashboard/Dashboard';
import { DocumentProvider } from './context/DocumentContext';
import { NavigationProvider } from './context/NavigationContext';
import MainNavbar from './components/Navigation/MainNavbar';
import CollapsibleSidebar from './components/Navigation/CollapsibleSidebar';
import RecentFiles from './components/Navigation/RecentFiles';

const queryClient = new QueryClient();

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <DocumentProvider>
          <NavigationProvider>
            <Router>
            <div className="flex flex-col h-screen">
              <MainNavbar />
              <div className="flex flex-1 overflow-hidden">
                <CollapsibleSidebar
                  isOpen={sidebarOpen}
                  onClose={() => setSidebarOpen(false)}
                />
                <main className="flex-1 overflow-y-auto p-4 bg-gray-50">
                  <Routes>
                    <Route path="/" element={<Upload />} />
                    <Route path="/search" element={<Search />} />
                    <Route path="/documents/:id" element={<DocumentViewer />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/settings" element={<Settings />}>
                      <Route index element={<Navigate to="profile" replace />} />
                      <Route path="profile" element={<UserProfileForm />} />
                      <Route path="notifications" element={<NotificationPreferences />} />
                      <Route path="theme" element={<ThemeSelector />} />
                      <Route path="security" element={<SecuritySettings />} />
                    </Route>
                    <Route path="/tags" element={<TagManagement />}>
                      <Route index element={<Navigate to="list" replace />} />
                      <Route path="list" element={<TagList />} />
                      <Route path="create" element={<TagEditor />} />
                      <Route path="assign" element={<TagAssigner />} />
                    </Route>
                  </Routes>
                  <RecentFiles />
                </main>
              </div>
            </div>
            </Router>
            <Toaster position="bottom-right" />
            <ReactQueryDevtools initialIsOpen={false} />
          </NavigationProvider>
        </DocumentProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;