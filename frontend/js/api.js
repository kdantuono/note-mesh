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
        // For successful responses with no content (like 204 No Content), return null
        if (response.ok && (response.status === 204 || response.status === 205)) {
            return null;
        }

        const contentType = response.headers.get('content-type');
        const isJson = contentType && contentType.includes('application/json');

        let data = null;

        // Check if there's actually content to read
        const contentLength = response.headers.get('content-length');
        if (contentLength === '0') {
            data = null;
        } else {
            try {
                if (isJson) {
                    data = await response.json();
                } else {
                    const text = await response.text();
                    data = text || null;
                }
            } catch (parseError) {
                console.warn('Failed to parse response:', parseError);
                data = null;
            }
        }

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

            if (data) {
                if (typeof data === 'string') {
                    errorMessage = data;
                } else if (data.detail) {
                    if (typeof data.detail === 'string') {
                        errorMessage = data.detail;
                    } else if (Array.isArray(data.detail)) {
                        // Handle Pydantic validation errors
                        const validationErrors = data.detail.map(err => {
                            const location = err.loc ? err.loc.join('.') : 'unknown';
                            return `${location}: ${err.msg}`;
                        }).join(', ');
                        errorMessage = `Validation errors: ${validationErrors}`;
                    } else {
                        errorMessage = JSON.stringify(data.detail);
                    }
                } else if (data.message) {
                    errorMessage = data.message;
                } else {
                    errorMessage = JSON.stringify(data);
                }
            }

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
        try {
            return await this.makeRequest(ENDPOINTS.NOTE_BY_ID(noteId));
        } catch (error) {
            // Fallback: if note not found, try shared note endpoint (for recipients)
            const msg = (error?.message || '').toLowerCase();
            if (msg.includes('not found') || msg.includes('404')) {
                try {
                    const shared = await this.getSharedNote(noteId);
                    if (shared) {
                        return this._mapSharedNoteToRegular(shared);
                    }
                } catch (e) {
                    // Re-throw original error if fallback fails too
                }
            }
            throw error;
        }
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
        if (!noteId) {
            throw new Error('Note ID is required for deletion');
        }

        console.log('Deleting note via API:', { noteId, endpoint: ENDPOINTS.NOTE_BY_ID(noteId) });

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
        const payload = {
            note_id: noteId,
            shared_with_usernames: [username], // Backend expects array
            permission_level: permission // FIXED: was 'permission', should be 'permission_level'
        };

        console.log('Sharing payload (single user):', payload);

        try {
            return await this.makeRequest(ENDPOINTS.SHARE_NOTE, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
        } catch (error) {
            // Enhance error messages for sharing-specific problems
            if (error.message.includes('500')) {
                throw new Error(`Could not share with user "${username}". The user may not exist in the system, or there may be a server issue.`);
            } else if (error.message.includes('404')) {
                throw new Error('Note not found or you do not have permission to share it.');
            } else if (error.message.includes('403')) {
                throw new Error('You do not have permission to share this note.');
            }
            // Re-throw original error for other cases
            throw error;
        }
    }

    // Share note with multiple users in a single API call (more efficient)
    async shareNoteWithUsers(noteId, usernames, permission = 'read') {
        // Validate inputs
        if (!noteId) {
            throw new Error('Note ID is required');
        }

        if (!usernames || !Array.isArray(usernames) || usernames.length === 0) {
            throw new Error('At least one username is required');
        }

        if (usernames.length > 20) {
            throw new Error('Cannot share with more than 20 users at once');
        }

        if (!['read', 'write'].includes(permission)) {
            throw new Error('Permission level must be "read" or "write"');
        }

        const payload = {
            note_id: noteId,
            shared_with_usernames: usernames, // Array of usernames
            permission_level: permission
        };

        console.log('Sharing payload (multiple users):', payload);

        try {
            return await this.makeRequest(ENDPOINTS.SHARE_NOTE, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
        } catch (error) {
            // Enhance error messages for sharing-specific problems
            if (error.message.includes('500')) {
                if (usernames.length === 1) {
                    throw new Error(`Could not share with user "${usernames[0]}". The user may not exist in the system, or there may be a server issue.`);
                } else {
                    throw new Error(`Could not share with one or more users: ${usernames.join(', ')}. Some users may not exist in the system, or there may be a server issue.`);
                }
            } else if (error.message.includes('404')) {
                throw new Error('Note not found or you do not have permission to share it.');
            } else if (error.message.includes('403')) {
                throw new Error('You do not have permission to share this note.');
            }
            // Re-throw original error for other cases
            throw error;
        }
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

    // Map SharedNoteResponse to a NoteResponse-like object used across the app
    _mapSharedNoteToRegular(shared) {
        return {
            id: shared.id,
            title: shared.title,
            content: shared.content,
            tags: shared.tags || [],
            hyperlinks: shared.hyperlinks || [],
            is_public: false,
            owner_id: shared.owner_id,
            owner_username: shared.owner_username,
            is_shared: true,
            can_edit: !!shared.can_write,
            created_at: shared.created_at,
            updated_at: shared.updated_at,
            view_count: 0,
            share_count: 0
        };
    }

    // Health check
    async healthCheck() {
        return await this.makeRequest(ENDPOINTS.HEALTH);
    }
}

// Create global API client instance
const apiClient = new ApiClient();