// API Client for NoteMesh
class ApiClient {
    constructor() {
        this.baseURL = CONFIG.API_BASE_URL;
        this.token = localStorage.getItem(CONFIG.TOKEN_KEY);
        this.refreshToken = localStorage.getItem(CONFIG.REFRESH_TOKEN_KEY);
    }

    // Set authentication tokens
    setTokens(accessToken, refreshToken = null) {
        this.token = accessToken;
        localStorage.setItem(CONFIG.TOKEN_KEY, accessToken);

        if (refreshToken) {
            this.refreshToken = refreshToken;
            localStorage.setItem(CONFIG.REFRESH_TOKEN_KEY, refreshToken);
        }
    }

    // Clear authentication tokens
    clearTokens() {
        this.token = null;
        this.refreshToken = null;
        localStorage.removeItem(CONFIG.TOKEN_KEY);
        localStorage.removeItem(CONFIG.REFRESH_TOKEN_KEY);
        localStorage.removeItem(CONFIG.USER_KEY);
    }

    // Get authorization headers
    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        return headers;
    }

    // Make HTTP request with error handling and fallback
    async makeRequest(endpoint, options = {}) {
        let url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: this.getAuthHeaders(),
            ...options
        };

        try {
            showSpinner(true);
            let response = await fetch(url, config);

            // If primary API fails, try fallback URL
            if (!response.ok && response.status >= 500 && CONFIG.FALLBACK_API_URL) {
                console.warn('Primary API failed, trying fallback...');
                url = `${CONFIG.FALLBACK_API_URL}${endpoint}`;
                response = await fetch(url, config);
            }

            // Handle token expiration
            if (response.status === 401 && this.refreshToken) {
                const refreshed = await this.refreshAccessToken();
                if (refreshed) {
                    // Retry original request with new token
                    config.headers['Authorization'] = `Bearer ${this.token}`;
                    const retryResponse = await fetch(url, config);
                    return await this.handleResponse(retryResponse);
                } else {
                    // Refresh failed, redirect to login
                    this.clearTokens();
                    if (authManager && typeof authManager.showAuthSection === 'function') {
                        authManager.showAuthSection();
                    }
                    return null;
                }
            }

            return await this.handleResponse(response);
        } catch (error) {
            console.error('API Request failed:', error);

            // More specific error messages
            if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                showToast('Unable to connect to server. Please check your connection.', TOAST_TYPES.ERROR);
            } else if (error.message.includes('timeout')) {
                showToast('Request timed out. Please try again.', TOAST_TYPES.ERROR);
            } else {
                showToast('Network error occurred. Please try again.', TOAST_TYPES.ERROR);
            }
            throw error;
        } finally {
            showSpinner(false);
        }
    }

    // Handle API response
    async handleResponse(response) {
        const contentType = response.headers.get('content-type');
        const isJson = contentType && contentType.includes('application/json');

        let data = null;
        if (isJson) {
            data = await response.json();
        } else {
            data = await response.text();
        }

        if (!response.ok) {
            const errorMessage = data?.detail || data?.message || `HTTP ${response.status}: ${response.statusText}`;
            throw new Error(errorMessage);
        }

        return data;
    }

    // Refresh access token
    async refreshAccessToken() {
        try {
            const response = await fetch(`${this.baseURL}${ENDPOINTS.REFRESH}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    refresh_token: this.refreshToken
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.setTokens(data.access_token, data.refresh_token);
                return true;
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
        }

        return false;
    }

    // Authentication API calls
    async login(username, password) {
        const data = await this.makeRequest(ENDPOINTS.LOGIN, {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });

        if (data.access_token) {
            this.setTokens(data.access_token, data.refresh_token);
            localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(data.user));
        }

        return data;
    }

    async register(userData) {
        const data = await this.makeRequest(ENDPOINTS.REGISTER, {
            method: 'POST',
            body: JSON.stringify(userData)
        });

        return data;
    }

    async logout() {
        try {
            await this.makeRequest(ENDPOINTS.LOGOUT, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Logout API call failed:', error);
        } finally {
            this.clearTokens();
        }
    }

    async getProfile() {
        return await this.makeRequest(ENDPOINTS.PROFILE);
    }

    // Notes API calls
    async getNotes(page = 1, limit = CONFIG.ITEMS_PER_PAGE, filters = {}) {
        const params = new URLSearchParams({
            page: page.toString(),
            per_page: limit.toString(),
            ...filters
        });

        return await this.makeRequest(`${ENDPOINTS.NOTES}?${params}`);
    }

    async getNote(noteId) {
        return await this.makeRequest(ENDPOINTS.NOTE_BY_ID(noteId));
    }

    async createNote(noteData) {
        return await this.makeRequest(ENDPOINTS.NOTES, {
            method: 'POST',
            body: JSON.stringify(noteData)
        });
    }

    async updateNote(noteId, noteData) {
        return await this.makeRequest(ENDPOINTS.NOTE_BY_ID(noteId), {
            method: 'PUT',
            body: JSON.stringify(noteData)
        });
    }

    async deleteNote(noteId) {
        return await this.makeRequest(ENDPOINTS.NOTE_BY_ID(noteId), {
            method: 'DELETE'
        });
    }

    // Search API calls
    async searchNotes(query, filters = {}) {
        const params = new URLSearchParams({
            q: query
        });

        // Handle filters properly
        if (filters.tags && Array.isArray(filters.tags)) {
            filters.tags.forEach(tag => params.append('tags', tag));
        }
        if (filters.page) {
            params.set('page', filters.page.toString());
        }
        if (filters.per_page) {
            params.set('per_page', filters.per_page.toString());
        }

        return await this.makeRequest(`${ENDPOINTS.SEARCH}?${params}`);
    }

    async getTagSuggestions(query) {
        const params = new URLSearchParams({ q: query });
        return await this.makeRequest(`${ENDPOINTS.SEARCH_TAGS}?${params}`);
    }

    // Sharing API calls
    async shareNote(noteId, username, permission = 'read') {
        return await this.makeRequest(ENDPOINTS.SHARE_NOTE, {
            method: 'POST',
            body: JSON.stringify({
                note_id: noteId,
                shared_with_username: username,
                permission: permission
            })
        });
    }

    // Get shares (both given and received)
    async getShares(type = 'all', page = 1, limit = CONFIG.ITEMS_PER_PAGE) {
        const params = new URLSearchParams({
            type: type,  // 'given' or 'received' or 'all'
            page: page.toString(),
            per_page: limit.toString()
        });

        return await this.makeRequest(`${ENDPOINTS.SHARES}?${params}`);
    }

    // Legacy methods for compatibility
    async getMyShares(page = 1, limit = CONFIG.ITEMS_PER_PAGE) {
        return await this.getShares('given', page, limit);
    }

    async getSharedWithMe(page = 1, limit = CONFIG.ITEMS_PER_PAGE) {
        return await this.getShares('received', page, limit);
    }

    async revokeShare(shareId) {
        return await this.makeRequest(ENDPOINTS.REVOKE_SHARE(shareId), {
            method: 'DELETE'
        });
    }

    // Get shared note (for recipients)
    async getSharedNote(noteId) {
        return await this.makeRequest(ENDPOINTS.SHARED_NOTE(noteId));
    }

    // Health check
    async healthCheck() {
        return await this.makeRequest(ENDPOINTS.HEALTH);
    }
}

// Create global API client instance
const apiClient = new ApiClient();