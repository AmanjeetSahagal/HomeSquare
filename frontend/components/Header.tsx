
import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';

const Header: React.FC = () => {
    const [open, setOpen] = useState(false);
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
                    <h1 className="text-xl font-semibold text-white">HomeSquare</h1>
                </div>
                <div className="hidden sm:flex space-x-2">
                    <NavLink to="/" className={getNavLinkClass}>
                        Analyze
                    </NavLink>
                    <NavLink to="/saved" className={getNavLinkClass}>
                        Saved Listings
                    </NavLink>
                </div>
                <button
                    className="sm:hidden text-white px-3 py-2 border border-gray-600 rounded-md"
                    onClick={() => setOpen((v) => !v)}
                    aria-expanded={open}
                    aria-label="Toggle navigation"
                >
                    Menu
                </button>
            </nav>
            {open && (
                <div className="sm:hidden px-4 pb-3 flex flex-col gap-2">
                    <NavLink to="/" className={getNavLinkClass} onClick={() => setOpen(false)}>
                        Analyze
                    </NavLink>
                    <NavLink to="/saved" className={getNavLinkClass} onClick={() => setOpen(false)}>
                        Saved Listings
                    </NavLink>
                </div>
            )}
        </header>
    );
};

export default Header;
