
import React, { useState, useCallback } from 'react';
import { ListingAnalysis, ListingLabel, SaveListingPayload } from '../types';
import Spinner from '../components/Spinner';
const API_BASE = import.meta.env.VITE_API_URL || '';

// Helper component to display a color-coded label
const LabelBadge: React.FC<{ label: ListingLabel }> = ({ label }) => {
    const labelStyles: { [key in ListingLabel]: string } = {
        [ListingLabel.DEAL]: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        [ListingLabel.FAIR]: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
        [ListingLabel.DUD]: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    };
    return (
        <span className={`px-3 py-1 text-sm font-medium rounded-full ${labelStyles[label]}`}>
            {label.charAt(0).toUpperCase() + label.slice(1)}
        </span>
    );
};

// Helper component to display the analysis result in a card
const ListingResultCard: React.FC<{ analysis: ListingAnalysis; onSave: () => void; saveStatus: string }> = ({ analysis, onSave, saveStatus }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden transition-all duration-300 ease-in-out transform hover:scale-[1.02]">
        <div className="p-6">
            <div className="flex justify-between items-start">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{analysis.Address}</h2>
                <LabelBadge label={analysis.Label} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Listing Price</p>
                    <p className="text-2xl font-semibold text-blue-600 dark:text-blue-400">{analysis.Price}</p>
                </div>
                <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">AI Estimated Price</p>
                    <p className="text-2xl font-semibold text-gray-700 dark:text-gray-300">{analysis['Estimated Price']}</p>
                </div>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4 text-center border-t border-b border-gray-200 dark:border-gray-700 py-3">
                <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Beds</p>
                    <p className="font-bold text-lg">{analysis.Beds}</p>
                </div>
                <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Baths</p>
                    <p className="font-bold text-lg">{analysis.Baths}</p>
                </div>
                <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Sq. Ft.</p>
                    <p className="font-bold text-lg">{analysis['Square Footage']}</p>
                </div>
            </div>
            <div className="mt-4">
                <p className="text-sm font-semibold text-gray-600 dark:text-gray-400">AI Explanation (Confidence: {(analysis.Confidence * 100).toFixed(0)}%)</p>
                <p className="text-gray-700 dark:text-gray-300 mt-1">{analysis.Explanation}</p>
            </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700 px-6 py-4 flex justify-between items-center">
            <a href={analysis.URL} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
                View Original Listing
            </a>
            <div>
                {saveStatus && <span className="text-sm mr-4 text-green-600 dark:text-green-400">{saveStatus}</span>}
                 <button onClick={onSave} className="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75 transition-colors">
                    Save Listing
                </button>
            </div>
        </div>
    </div>
);


const AnalyzePage: React.FC = () => {
    // State management for the component
    const [url, setUrl] = useState<string>('');
    const [analysis, setAnalysis] = useState<ListingAnalysis | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [saveStatus, setSaveStatus] = useState<string>('');

    // Utility to parse string values like "$1,000" or "1,500 sqft" into numbers
    const parseNumericString = (s: string): number => {
        return parseInt(s.replace(/[^0-9]/g, ''), 10);
    };

    // Handles the "Analyze Listing" button click
    const handleAnalyze = async () => {
        if (!url) {
            setError('Please enter a valid Zillow or Redfin URL.');
            return;
        }
        setIsLoading(true);
        setError(null);
        setAnalysis(null);
        setSaveStatus('');

        try {
            const response = await fetch(`${API_BASE}/api/analyze_ai`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            if (result.status === 'success') {
                setAnalysis(result.data);
            } else {
                throw new Error(result.message || 'Failed to get analysis.');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };
    
    // Handles saving the current analysis to the backend
    const handleSave = useCallback(async () => {
        if (!analysis) return;
        setSaveStatus('');
        
        // Transform the analysis data to match the backend's expected format
        const payload: SaveListingPayload = {
            address: analysis.Address,
            price: parseNumericString(analysis.Price),
            beds: analysis.Beds,
            baths: analysis.Baths,
            sqft: parseNumericString(analysis['Square Footage']),
            estimated_price: parseNumericString(analysis['Estimated Price']),
            label: analysis.Label,
            confidence: analysis.Confidence,
            url: analysis.URL,
        };

        try {
            const response = await fetch('/api/save_listing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error('Failed to save listing.');
            }
            setSaveStatus('Listing Saved!');
        } catch (err) {
             setSaveStatus(err instanceof Error ? `Error: ${err.message}` : 'Save failed.');
        }
    }, [analysis]);

    return (
        <div className="max-w-4xl mx-auto">
            <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-md">
                <h1 className="text-3xl font-bold text-center mb-2 text-gray-900 dark:text-white">Analyze Real Estate Listings</h1>
                <p className="text-center text-gray-600 dark:text-gray-400 mb-6">Enter a Zillow or Redfin URL to get an AI-powered market analysis.</p>
                <div className="flex flex-col sm:flex-row gap-2">
                    <input
                        type="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="https://www.zillow.com/homedetails/..."
                        className="flex-grow p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                    />
                    <button
                        onClick={handleAnalyze}
                        disabled={isLoading}
                        className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
                    >
                        {isLoading ? 'Analyzing...' : 'Analyze Listing'}
                    </button>
                </div>
            </div>

            <div className="mt-8">
                {isLoading && <div className="flex justify-center"><Spinner /></div>}
                {error && <div className="text-center p-4 bg-red-100 text-red-700 rounded-lg">{error}</div>}
                {analysis && <ListingResultCard analysis={analysis} onSave={handleSave} saveStatus={saveStatus} />}
            </div>
        </div>
    );
};

export default AnalyzePage;
