import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';
import { Toaster } from 'react-hot-toast';

import './App.css';
import Upload from './components/Upload/Upload';
import Search from './components/Search/Search';
import DocumentView from './components/DocumentView/DocumentView';
import Navbar from './components/Navbar/Navbar';
import Sidebar from './components/Sidebar/Sidebar';
import { DocumentProvider } from './context/DocumentContext';

const queryClient = new QueryClient();

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <DocumentProvider>
        <Router>
          <div className="flex flex-col h-screen">
            <Navbar onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
            <div className="flex flex-1 overflow-hidden">
              <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
              <main className="flex-1 overflow-y-auto p-4 bg-gray-50">
                <Routes>
                  <Route path="/" element={<Upload />} />
                  <Route path="/search" element={<Search />} />
                  <Route path="/documents/:id" element={<DocumentView />} />
                </Routes>
              </main>
            </div>
          </div>
        </Router>
        <Toaster position="bottom-right" />
        <ReactQueryDevtools initialIsOpen={false} />
      </DocumentProvider>
    </QueryClientProvider>
  );
}

export default App;