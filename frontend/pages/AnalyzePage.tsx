import React, { useState, useCallback, useEffect } from 'react';
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
const ListingResultCard: React.FC<{
    analysis: ListingAnalysis;
    onSave: () => void;
    onCopyShare: () => void;
    saveStatus: string;
    listingUrl: string;
}> = ({ analysis, onSave, onCopyShare, saveStatus, listingUrl }) => (
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
                    {analysis['ML Estimated Price'] != null && (
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            ML median ≈ ${Math.round(analysis['ML Estimated Price']).toLocaleString()}
                            {analysis['ML Interval Low'] != null && analysis['ML Interval High'] != null
                                ? ` ( ${Math.round(analysis['ML Interval Low']).toLocaleString()}–${Math.round(analysis['ML Interval High']).toLocaleString()} )`
                                : ''}
                        </p>
                    )}
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
            <div className="mt-4">
                <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
                    <span>Confidence Meter</span>
                    <span>{Math.round(analysis.Confidence * 100)}%</span>
                </div>
                <div className="h-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-blue-600"
                        style={{ width: `${Math.min(100, Math.max(0, analysis.Confidence * 100))}%` }}
                    />
                </div>
            </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700 px-6 py-4 flex justify-between items-center">
            <a href={analysis.URL || listingUrl} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
                View Original Listing
            </a>
            <div>
                {saveStatus && <span className="text-sm mr-4 text-green-600 dark:text-green-400">{saveStatus}</span>}
                <button onClick={onCopyShare} className="px-4 py-2 mr-2 bg-white text-blue-700 border border-blue-200 font-semibold rounded-lg shadow-sm hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75 transition-colors">
                    Copy Share Link
                </button>
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
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

    useEffect(() => {
        try {
            const hash = window.location.hash || '';
            const queryIndex = hash.indexOf('?');
            if (queryIndex !== -1) {
                const params = new URLSearchParams(hash.slice(queryIndex + 1));
                const sharedUrl = params.get('url');
                if (sharedUrl) {
                    setUrl(sharedUrl);
                    return;
                }
            }
            const raw = localStorage.getItem('homesquare_last_url');
            if (raw) {
                setUrl(raw);
            }
        } catch (e) {
            console.warn('Failed to load persisted URL from localStorage', e);
        }
    }, []);

    // Utility to parse string values like "$1,000" or "1,500 sqft" into numbers
    const parseNumericString = (s: any): number => {
        if (s == null) return 0;
        if (typeof s === 'number') return s;
        if (typeof s === 'string') return parseInt(s.replace(/[^0-9]/g, ''), 10);
        return 0;
    };

    const validateUrl = (value: string) => {
        try {
            const parsed = new URL(value);
            const host = parsed.hostname.replace(/^www\./, '');
            const allowed = ['zillow.com', 'redfin.com'];
            if (!allowed.some((d) => host.endsWith(d))) {
                return 'Please use a Zillow or Redfin URL.';
            }
            return null;
        } catch {
            return 'Please enter a valid URL.';
        }
    };

    // Handles the "Analyze Listing" button click
    const handleAnalyze = async () => {
        const validationError = validateUrl(url);
        if (validationError) {
            setError(validationError);
            return;
        }
        setIsLoading(true);
        setError(null);
        setAnalysis(null);
        setSaveStatus('');
        setToast(null);

        try {
            const response = await fetch(`${API_BASE}/api/analyze_ai`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });

            const result = await response.json();
            if (!response.ok) {
                const msg = result?.error || result?.message || 'Failed to get analysis.';
                throw new Error(msg);
            }
            if (result.status === 'success') {
                setAnalysis(result.data);

                // Persist last successful URL (no auto-restore of results)
                try {
                    localStorage.setItem('homesquare_last_url', url);
                } catch (e) {
                    console.warn('Failed to persist URL to localStorage', e);
                }
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
        if (!analysis) {
            console.warn('handleSave called with no analysis');
            return;
        }

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
            url: analysis.URL || url,
        };

        console.log('HANDLE_SAVE CALLED, payload =', payload, 'API_BASE =', API_BASE);

        try {
            const response = await fetch(`${API_BASE}/api/saved_listings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                let msg = 'Failed to save listing.';
                try {
                    const errJson = await response.json();
                    if (errJson && errJson.error) {
                        msg = errJson.error;
                    }
                } catch {
                    // ignore JSON parsing errors
                }
                throw new Error(msg);
            }

            const saved = await response.json();
            console.log('SAVE RESPONSE =', saved);
            setSaveStatus('Listing Saved!');
            setToast({ message: 'Listing saved', type: 'success' });
        } catch (err) {
            console.error('SAVE ERROR =', err);
            setSaveStatus(err instanceof Error ? `Error: ${err.message}` : 'Save failed.');
            setToast({ message: 'Save failed', type: 'error' });
        }
    }, [analysis, url]);

    const handleCopyShare = async () => {
        const base = `${window.location.origin}${window.location.pathname}`;
        const link = `${base}#/?url=${encodeURIComponent(url)}`;
        try {
            await navigator.clipboard.writeText(link);
            setToast({ message: 'Share link copied', type: 'success' });
        } catch (e) {
            setToast({ message: 'Failed to copy link', type: 'error' });
        }
    };

    const dismissToast = () => setToast(null);

    const comps = analysis?.CompsPreview || [];
    const compsStats = comps.length
        ? (() => {
            const prices = comps.map((c) => c.price).filter((v): v is number => typeof v === 'number' && !Number.isNaN(v));
            const ppsf = comps
                .map((c) => (c.price && c.sqft ? c.price / c.sqft : null))
                .filter((v): v is number => v != null && !Number.isNaN(v));
            const median = (arr: number[]) => {
                const sorted = [...arr].sort((a, b) => a - b);
                const mid = Math.floor(sorted.length / 2);
                return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
            };
            return {
                count: comps.length,
                priceMedian: prices.length ? median(prices) : null,
                ppsfMedian: ppsf.length ? median(ppsf) : null,
            };
        })()
        : null;

    return (
        <div className="max-w-4xl mx-auto">
            <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-md">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Analyze a Listing</h1>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Zillow or Redfin URL</p>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                        Powered by comps + price modeling
                    </div>
                </div>
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
                {error && (
                    <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-sm p-3 bg-red-100 text-red-700 rounded-lg">
                        <span>{error}</span>
                        <button
                            onClick={handleAnalyze}
                            className="px-3 py-1.5 bg-red-600 text-white rounded-md hover:bg-red-700"
                        >
                            Retry
                        </button>
                    </div>
                )}
            </div>

            <div className="mt-8">
                {isLoading && <div className="flex justify-center"><Spinner /></div>}
                {!isLoading && !analysis && !error && (
                    <div className="text-center mt-10 bg-white dark:bg-gray-800 p-10 rounded-lg shadow-md">
                        <div className="mx-auto w-20 h-20 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-3xl mb-4">
                            🏠
                        </div>
                        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">Paste a listing URL to begin</h2>
                        <p className="text-gray-500 dark:text-gray-400 mt-2">
                            We’ll analyze comps, estimate fair value, and show a clear verdict.
                        </p>
                    </div>
                )}
                {analysis && (
                    <>
                        <ListingResultCard
                            analysis={analysis}
                            onSave={handleSave}
                            onCopyShare={handleCopyShare}
                            saveStatus={saveStatus}
                            listingUrl={url}
                        />
                        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-5">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Comps Snapshot</h3>
                                <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                                    <div>Comps used: {analysis.CompsUsed ?? compsStats?.count ?? 0}</div>
                                    <div>Median price: {compsStats?.priceMedian ? `$${Math.round(compsStats.priceMedian).toLocaleString()}` : '—'}</div>
                                    <div>Median $/sqft: {compsStats?.ppsfMedian ? `$${Math.round(compsStats.ppsfMedian).toLocaleString()}` : '—'}</div>
                                </div>
                            </div>
                            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-5">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Listing Delta</h3>
                                <div className="text-sm text-gray-600 dark:text-gray-400">
                                    {analysis['Percent Difference'] != null
                                        ? `List price is ${(analysis['Percent Difference'] * 100).toFixed(1)}% vs estimate.`
                                        : 'Percent difference not available.'}
                                </div>
                            </div>
                        </div>
                        {comps.length > 0 && (
                            <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow-md p-5">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Comparable Homes</h3>
                                <div className="overflow-x-auto">
                                    <table className="min-w-full text-sm">
                                        <thead className="text-gray-600 dark:text-gray-400">
                                            <tr className="text-left border-b border-gray-200 dark:border-gray-700">
                                                <th className="py-2 pr-3">Price</th>
                                                <th className="py-2 pr-3">Beds</th>
                                                <th className="py-2 pr-3">Baths</th>
                                                <th className="py-2 pr-3">Sqft</th>
                                                <th className="py-2">Note</th>
                                            </tr>
                                        </thead>
                                        <tbody className="text-gray-700 dark:text-gray-300">
                                            {comps.slice(0, 6).map((c, idx) => (
                                                <tr key={idx} className="border-b border-gray-100 dark:border-gray-700">
                                                    <td className="py-2 pr-3">{c.price ? `$${c.price.toLocaleString()}` : '—'}</td>
                                                    <td className="py-2 pr-3">{c.beds ?? '—'}</td>
                                                    <td className="py-2 pr-3">{c.baths ?? '—'}</td>
                                                    <td className="py-2 pr-3">{c.sqft ?? '—'}</td>
                                                    <td className="py-2">{c.note || '—'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>

            {toast && (
                <div className="fixed bottom-6 right-6 z-50">
                    <div className={`px-4 py-3 rounded-lg shadow-lg text-sm ${toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
                        <div className="flex items-center gap-3">
                            <span>{toast.message}</span>
                            <button className="opacity-80 hover:opacity-100" onClick={dismissToast}>
                                Dismiss
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AnalyzePage;
