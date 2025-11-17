
// Enum for the classification labels of a listing
export enum ListingLabel {
    DEAL = 'deal',
    FAIR = 'fair',
    DUD = 'dud',
}

// Interface for the data returned by the /api/analyze_ai endpoint
export interface ListingAnalysis {
    Address: string;
    Price: string;
    Beds: number;
    Baths: number;
    'Square Footage': string;
    'Estimated Price': string;
    Label: ListingLabel;
    Confidence: number;
    Explanation: string;
    URL: string;
}

// Interface for the payload sent to the /api/save_listing endpoint
export interface SaveListingPayload {
    address: string;
    price: number;
    beds: number;
    baths: number;
    sqft: number;
    estimated_price: number;
    label: ListingLabel;
    confidence: number;
    url: string;
}

// Interface for the listing objects returned by the /api/saved_listings endpoint
export interface SavedListing {
    id: number;
    address: string;
    price: number;
    beds: number;
    baths: number;
    sqft: number;
    estimated_price: number;
    label: ListingLabel;
    confidence: number;
    url: string;
    saved_at: string; // ISO 8601 date string
}
