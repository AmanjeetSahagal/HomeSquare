
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import AnalyzePage from './pages/AnalyzePage';
import SavedListingsPage from './pages/SavedListingsPage';

const App: React.FC = () => {
    // This component sets up the main structure of the app: a persistent header
    // and a main content area where pages are rendered based on the current route.
    return (
        <div className="min-h-screen font-sans text-gray-800 dark:text-gray-200">
            <Header />
            <main className="container mx-auto px-4 py-8">
                <Routes>
                    <Route path="/" element={<AnalyzePage />} />
                    <Route path="/saved" element={<SavedListingsPage />} />
                </Routes>
            </main>
        </div>
    );
};

export default App;
