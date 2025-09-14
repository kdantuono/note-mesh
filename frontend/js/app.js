// Main application initialization for NoteMesh

// Application state
const AppState = {
    initialized: false,
    currentSection: null,
    isOnline: navigator.onLine
};

// Application initialization
async function initializeApp() {
    try {
        console.log('Initializing NoteMesh...');

        // Initialize UI components
        initializeUI();

        // Initialize authentication
        authManager.initializeAuth();

        // Initialize notes management
        notesManager.initializeNotes();

        // Set up global error handling
        setupErrorHandling();

        // Set up online/offline detection
        setupConnectivityHandlers();

        // Check backend health
        await checkBackendHealth();

        AppState.initialized = true;
        console.log('NoteMesh initialized successfully');

        // Show welcome message for new users
        if (!authManager.isAuthenticated()) {
            setTimeout(() => {
                showToast('Welcome to NoteMesh! Create an account to start managing your notes.', TOAST_TYPES.INFO, 8000);
            }, 1000);
        }

    } catch (error) {
        console.error('Failed to initialize NoteMesh:', error);
        showToast('Failed to initialize application. Please refresh the page.', TOAST_TYPES.ERROR);
    }
}

// Check backend health
async function checkBackendHealth() {
    try {
        await apiClient.healthCheck();
        console.log('Backend health check passed');
    } catch (error) {
        console.warn('Backend health check failed:', error);
        showToast('Warning: Backend service may be unavailable', TOAST_TYPES.WARNING);
    }
}

// Global error handling
function setupErrorHandling() {
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled promise rejection:', event.reason);
        showToast('An unexpected error occurred', TOAST_TYPES.ERROR);
        event.preventDefault();
    });

    // Handle general JavaScript errors
    window.addEventListener('error', (event) => {
        console.error('JavaScript error:', event.error);
        // Don't show toast for every JS error to avoid spam
    });

    // Handle fetch errors globally
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
        try {
            return await originalFetch(...args);
        } catch (error) {
            if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                showToast('Network connection problem', TOAST_TYPES.ERROR);
            }
            throw error;
        }
    };
}

// Online/offline connectivity handling
function setupConnectivityHandlers() {
    window.addEventListener('online', () => {
        AppState.isOnline = true;
        showToast('Connection restored', TOAST_TYPES.SUCCESS);
        console.log('App is online');

        // Retry failed requests if needed
        if (authManager.isAuthenticated()) {
            // Refresh current data
            setTimeout(() => {
                if (notesManager.currentNotes) {
                    notesManager.loadNotes(notesManager.currentPage, notesManager.currentFilters);
                }
            }, 1000);
        }
    });

    window.addEventListener('offline', () => {
        AppState.isOnline = false;
        showToast('You are now offline. Some features may not be available.', TOAST_TYPES.WARNING, 8000);
        console.log('App is offline');
    });
}

// Page visibility handling
function setupPageVisibilityHandlers() {
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && authManager.isAuthenticated()) {
            // Page became visible - refresh data if it's been a while
            const lastRefresh = sessionStorage.getItem('lastDataRefresh');
            const now = Date.now();
            const fiveMinutes = 5 * 60 * 1000;

            if (!lastRefresh || (now - parseInt(lastRefresh)) > fiveMinutes) {
                console.log('Refreshing data after page visibility change');
                notesManager.loadNotes(notesManager.currentPage, notesManager.currentFilters);
                sessionStorage.setItem('lastDataRefresh', now.toString());
            }
        }
    });
}

// Cleanup function for app shutdown
function cleanupApp() {
    console.log('Cleaning up NoteMesh...');

    // Clear any pending timeouts/intervals
    // Remove event listeners if needed

    AppState.initialized = false;
}

// Service worker registration (for future PWA features)
async function registerServiceWorker() {
    if ('serviceWorker' in navigator && window.location.protocol === 'https:') {
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            console.log('Service Worker registered:', registration);
        } catch (error) {
            console.log('Service Worker registration failed:', error);
        }
    }
}

// Performance monitoring
function setupPerformanceMonitoring() {
    // Monitor Core Web Vitals if available
    if ('performance' in window && 'PerformanceObserver' in window) {
        try {
            const observer = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    if (entry.entryType === 'navigation') {
                        console.log('Page load time:', entry.loadEventEnd - entry.loadEventStart, 'ms');
                    }
                }
            });

            observer.observe({ entryTypes: ['navigation'] });
        } catch (error) {
            console.log('Performance monitoring not available');
        }
    }
}

// Data refresh utility
function scheduleDataRefresh() {
    if (!authManager.isAuthenticated()) return;

    // Refresh data every 5 minutes if the page is visible
    setInterval(() => {
        if (document.visibilityState === 'visible' && AppState.isOnline) {
            console.log('Scheduled data refresh');
            notesManager.loadNotes(notesManager.currentPage, notesManager.currentFilters);
        }
    }, 5 * 60 * 1000); // 5 minutes
}

// Debug utilities (development only)
const DebugUtils = {
    // Clear all data
    clearAllData() {
        localStorage.clear();
        sessionStorage.clear();
        console.log('All local data cleared');
        window.location.reload();
    },

    // Show current app state
    showAppState() {
        console.log('App State:', {
            initialized: AppState.initialized,
            isOnline: AppState.isOnline,
            authenticated: authManager.isAuthenticated(),
            currentUser: authManager.getCurrentUser(),
            notesCount: notesManager.currentNotes?.length || 0,
            currentPage: notesManager.currentPage
        });
    },

    // Test API endpoints
    async testAPI() {
        try {
            const health = await apiClient.healthCheck();
            console.log('Health check:', health);

            if (authManager.isAuthenticated()) {
                const profile = await apiClient.getProfile();
                console.log('Profile:', profile);
            }
        } catch (error) {
            console.error('API test failed:', error);
        }
    }
};

// Make debug utils available globally in development
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.DebugUtils = DebugUtils;
    console.log('Debug utilities available via window.DebugUtils');
}

// DOM Content Loaded event handler
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM loaded, initializing app...');

    // Setup additional handlers
    setupPageVisibilityHandlers();
    setupPerformanceMonitoring();

    // Initialize the main application
    await initializeApp();

    // Schedule periodic data refresh
    scheduleDataRefresh();

    // Register service worker for future PWA features
    // await registerServiceWorker();
});

// Window load event handler
window.addEventListener('load', () => {
    console.log('Window loaded completely');

    // Hide any loading indicators
    showSpinner(false);

    // Performance measurement
    const loadTime = performance.now();
    console.log(`App loaded in ${Math.round(loadTime)}ms`);
});

// Before page unload
window.addEventListener('beforeunload', () => {
    cleanupApp();
});

// Export app state for debugging
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AppState, DebugUtils };
}