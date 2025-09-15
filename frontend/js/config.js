// Configuration for NoteMesh frontend
const CONFIG = {
    // Use relative URL for API calls when served through nginx proxy
    API_BASE_URL: window.location.origin + '/api',
    FALLBACK_API_URL: 'http://localhost:8000/api', // Fallback for direct access
    TOKEN_KEY: 'notemesh_token',
    REFRESH_TOKEN_KEY: 'notemesh_refresh_token',
    USER_KEY: 'notemesh_user',
    ITEMS_PER_PAGE: 9,
    MAX_CONTENT_PREVIEW: 150,
    TOAST_DURATION: 3000 // Reduced toast duration
};

// API Endpoints
const ENDPOINTS = {
    // Auth
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
    PROFILE: '/auth/me',

    // Notes
    NOTES: '/notes/',
    NOTE_BY_ID: (id) => `/notes/${id}`,
    NOTE_TAGS: '/notes/tags/',
    VALIDATE_LINKS: '/notes/validate-links',

    // Sharing
    SHARES: '/sharing/',
    SHARE_NOTE: '/sharing/',
    REVOKE_SHARE: (shareId) => `/sharing/${shareId}`,
    SHARED_NOTE: (noteId) => `/sharing/notes/${noteId}`,
    NOTE_ACCESS: (noteId) => `/sharing/notes/${noteId}/access`,
    SHARING_STATS: '/sharing/stats',

    // Search
    SEARCH: '/search/notes',
    SEARCH_TAGS: '/search/tags/suggest',
    SEARCH_STATS: '/search/stats',

    // Health
    HEALTH: '/health/'
};

// Note types for visual distinction
const NOTE_TYPES = {
    OWNED: 'owned',
    SHARED_WITH_ME: 'shared-with-me',
    SHARED_BY_ME: 'shared-by-me'
};

// Toast types
const TOAST_TYPES = {
    SUCCESS: 'success',
    ERROR: 'error',
    WARNING: 'warning',
    INFO: 'info'
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CONFIG, ENDPOINTS, NOTE_TYPES, TOAST_TYPES };
}