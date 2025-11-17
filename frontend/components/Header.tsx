
import React from 'react';
import { NavLink } from 'react-router-dom';

const Header: React.FC = () => {
    // Helper function to apply conditional classes for active navigation links
    const getNavLinkClass = ({ isActive }: { isActive: boolean }): string => {
        const baseClasses = 'px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200';
        if (isActive) {
            return `${baseClasses} bg-blue-600 text-white`;
        }
        return `${baseClasses} text-gray-300 hover:bg-gray-700 hover:text-white`;
    };

    return (
        <header className="bg-gray-800 dark:bg-gray-900 shadow-lg">
            <nav className="container mx-auto px-4 py-3 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                    <span className="text-3xl">🏡</span>
                    <h1 className="text-xl font-semibold text-white">AI Real Estate Analyzer</h1>
                </div>
                <div className="flex space-x-2">
                    <NavLink to="/" className={getNavLinkClass}>
                        Analyze
                    </NavLink>
                    <NavLink to="/saved" className={getNavLinkClass}>
                        Saved Listings
                    </NavLink>
                </div>
            </nav>
        </header>
    );
};

export default Header;
