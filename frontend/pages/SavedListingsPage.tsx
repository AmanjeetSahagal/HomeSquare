// Uses Vite env var for backend base URL, e.g. VITE_API_URL=http://localhost:5050
const API_BASE = import.meta.env.VITE_API_URL;

import React, { useState, useEffect } from 'react';
import { SavedListing, ListingLabel } from '../types';
import Spinner from '../components/Spinner';

// Helper component for the color-coded label badge
const LabelBadge: React.FC<{ label: ListingLabel }> = ({ label }) => {
  const labelStyles: { [key in ListingLabel]: string } = {
    [ListingLabel.DEAL]: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    [ListingLabel.FAIR]: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
    [ListingLabel.DUD]: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  };
  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${labelStyles[label]}`}>
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
};

// Component to display a single saved listing card
const SavedListingCard: React.FC<{ listing: SavedListing; onDelete: () => void; deleting: boolean }> = ({ listing, onDelete, deleting }) => {
  // Format numbers with commas for better readability
  const formatCurrency = (num: number | null | undefined) => {
    if (num == null || isNaN(Number(num))) return '—';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(Number(num));
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'Unknown date';
    const d = new Date(dateString);
    if (Number.isNaN(d.getTime())) return String(dateString);
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden flex flex-col transition-transform duration-300 hover:-translate-y-1">
      <div className="p-5 flex-grow">
        <div className="flex justify-between items-center mb-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Saved on {formatDate((listing as any).saved_at)}
          </p>
          {/* Cast to any in case label typing differs slightly */}
          <LabelBadge label={(listing as any).label} />
        </div>
        <h3 className="font-bold text-lg text-gray-900 dark:text-white truncate">
          {(listing as any).address}
        </h3>
        <div className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-300">Price:</span>
            <span className="font-semibold text-blue-600 dark:text-blue-400">
              {formatCurrency((listing as any).price)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-300">Est. Price:</span>
            <span className="font-semibold">
              {formatCurrency((listing as any).estimated_price)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-300">Confidence:</span>
            <span className="font-semibold">
              {((listing as any).confidence != null
                ? ((listing as any).confidence * 100).toFixed(0) + '%'
                : '—')}
            </span>
          </div>
        </div>
      </div>
      <div className="bg-gray-50 dark:bg-gray-700 px-5 py-3">
        <div className="flex items-center justify-between">
          <a
            href={(listing as any).url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
          >
            View Listing &rarr;
          </a>
          <button
            onClick={onDelete}
            disabled={deleting}
            className="text-sm font-medium text-red-600 hover:text-red-700 disabled:text-red-300"
          >
            {deleting ? 'Removing...' : 'Remove'}
          </button>
        </div>
      </div>
    </div>
  );
};

const SavedListingsPage: React.FC = () => {
  const [listings, setListings] = useState<SavedListing[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [labelFilter, setLabelFilter] = useState<string>('all');
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [dateRange, setDateRange] = useState<string>('all');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const fetchSavedListings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/saved_listings`, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch saved listings.');
      }
      const data: SavedListing[] = await response.json();
      if (!Array.isArray(data)) {
        throw new Error('Unexpected response from server.');
      }
      setListings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSavedListings();
  }, []);

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    setError(null);
    setToast(null);
    const previous = listings;
    setListings((prev) => prev.filter((item) => (item as any).id !== id));
    try {
      const response = await fetch(`${API_BASE}/api/saved_listings/${id}`, {
        method: 'DELETE',
        headers: {
          Accept: 'application/json',
        },
      });
      if (!response.ok) {
        let msg = 'Failed to delete listing.';
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
      setToast({ message: 'Listing removed', type: 'success' });
    } catch (err) {
      setListings(previous);
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
      setToast({ message: 'Remove failed', type: 'error' });
    } finally {
      setDeletingId(null);
    }
  };

  const filteredListings = listings.filter((listing) => {
    const label = String((listing as any).label || '').toLowerCase();
    if (labelFilter !== 'all' && label !== labelFilter) return false;

    const confidence = Number((listing as any).confidence ?? 0) * 100;
    if (confidence < minConfidence) return false;

    if (dateRange !== 'all') {
      const d = new Date((listing as any).saved_at || '');
      if (Number.isNaN(d.getTime())) return false;
      const days = Number(dateRange);
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);
      if (d < cutoff) return false;
    }
    return true;
  });

  if (isLoading) {
    return (
      <div className="flex justify-center mt-16">
        <Spinner size="h-12 w-12" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center mt-16 p-4 bg-red-100 text-red-700 rounded-lg">
        {error}
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Saved Listings</h1>
        <button
          onClick={fetchSavedListings}
          className="px-4 py-2 bg-white text-blue-700 border border-blue-200 rounded-lg shadow-sm hover:bg-blue-50"
        >
          Refresh
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-gray-500 dark:text-gray-400">Label</label>
            <select
              value={labelFilter}
              onChange={(e) => setLabelFilter(e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-md p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="all">All</option>
              <option value="deal">Deal</option>
              <option value="fair">Fair</option>
              <option value="dud">Dud</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 dark:text-gray-400">Min confidence</label>
            <input
              type="range"
              min={0}
              max={100}
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="mt-2 w-full"
            />
            <div className="text-xs text-gray-500 dark:text-gray-400">{minConfidence}%+</div>
          </div>
          <div>
            <label className="text-xs text-gray-500 dark:text-gray-400">Date range</label>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-md p-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="all">All time</option>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
            </select>
          </div>
        </div>
      </div>

      {filteredListings.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredListings.map((listing: SavedListing) => (
            <SavedListingCard
              key={(listing as any).id}
              listing={listing}
              onDelete={() => handleDelete((listing as any).id)}
              deleting={deletingId === (listing as any).id}
            />
          ))}
        </div>
      ) : listings.length === 0 ? (
        <div className="text-center mt-16 bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300">
            No Saved Listings Yet
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mt-2">
            Go to the Analyze page to find and save your first listing!
          </p>
        </div>
      ) : (
        <div className="text-center mt-16 bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300">
            No results match your filters
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mt-2">
            Try lowering the confidence or widening the date range.
          </p>
        </div>
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 z-50">
          <div className={`px-4 py-3 rounded-lg shadow-lg text-sm ${toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
            <div className="flex items-center gap-3">
              <span>{toast.message}</span>
              <button className="opacity-80 hover:opacity-100" onClick={() => setToast(null)}>
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SavedListingsPage;
