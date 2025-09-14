// Comprehensive logging system for NoteMesh Frontend
class Logger {
    static levels = {
        ERROR: 0,
        WARN: 1,
        INFO: 2,
        DEBUG: 3,
        TRACE: 4
    };

    static levelNames = ['ERROR', 'WARN', 'INFO', 'DEBUG', 'TRACE'];
    static currentLevel = Logger.levels.DEBUG; // Default to DEBUG
    static logBuffer = [];
    static maxBufferSize = 1000;

    static init() {
        // Set log level from localStorage or environment
        const savedLevel = localStorage.getItem('notemesh_log_level');
        if (savedLevel && Logger.levels[savedLevel] !== undefined) {
            Logger.currentLevel = Logger.levels[savedLevel];
        }

        // Enable/disable based on environment
        const isLocal = window.location.hostname === 'localhost' ||
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname === '0.0.0.0';

        if (!isLocal) {
            Logger.currentLevel = Logger.levels.WARN; // Only warnings and errors in production
        }

        Logger.info('Logger initialized', {
            level: Logger.levelNames[Logger.currentLevel],
            hostname: window.location.hostname,
            isLocal
        });
    }

    static setLevel(level) {
        if (typeof level === 'string') {
            level = Logger.levels[level.toUpperCase()];
        }
        if (level !== undefined) {
            Logger.currentLevel = level;
            localStorage.setItem('notemesh_log_level', Logger.levelNames[level]);
            Logger.info(`Log level set to ${Logger.levelNames[level]}`);
        }
    }

    static _log(level, message, data = null, error = null) {
        if (level > Logger.currentLevel) return;

        const timestamp = new Date().toISOString();
        const levelName = Logger.levelNames[level];
        const logEntry = {
            timestamp,
            level: levelName,
            message,
            data,
            error: error ? {
                name: error.name,
                message: error.message,
                stack: error.stack
            } : null,
            url: window.location.href,
            userAgent: navigator.userAgent.split(' ')[0] // Simplified UA
        };

        // Add to buffer
        Logger.logBuffer.push(logEntry);
        if (Logger.logBuffer.length > Logger.maxBufferSize) {
            Logger.logBuffer.shift();
        }

        // Console output with styling
        const style = Logger._getStyle(level);
        const prefix = `%c[${timestamp.split('T')[1].split('.')[0]}] ${levelName}`;

        if (data || error) {
            console.log(prefix, style, message, data || error);
        } else {
            console.log(prefix, style, message);
        }
    }

    static _getStyle(level) {
        const styles = {
            [Logger.levels.ERROR]: 'color: #e74c3c; font-weight: bold',
            [Logger.levels.WARN]: 'color: #f39c12; font-weight: bold',
            [Logger.levels.INFO]: 'color: #3498db; font-weight: bold',
            [Logger.levels.DEBUG]: 'color: #2ecc71',
            [Logger.levels.TRACE]: 'color: #95a5a6'
        };
        return styles[level] || '';
    }

    static error(message, data = null, error = null) {
        Logger._log(Logger.levels.ERROR, message, data, error);
    }

    static warn(message, data = null) {
        Logger._log(Logger.levels.WARN, message, data);
    }

    static info(message, data = null) {
        Logger._log(Logger.levels.INFO, message, data);
    }

    static debug(message, data = null) {
        Logger._log(Logger.levels.DEBUG, message, data);
    }

    static trace(message, data = null) {
        Logger._log(Logger.levels.TRACE, message, data);
    }

    // Get recent logs
    static getLogs(count = 100) {
        return Logger.logBuffer.slice(-count);
    }

    // Export logs as JSON
    static exportLogs() {
        const logs = {
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            logs: Logger.logBuffer
        };
        return JSON.stringify(logs, null, 2);
    }

    // Clear log buffer
    static clearLogs() {
        Logger.logBuffer = [];
        Logger.info('Log buffer cleared');
    }
}

// Debug utilities for NoteMesh
class DebugHelper {
    static enabled = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    static log(message, data = null) {
        Logger.debug(`[Debug] ${message}`, data);
    }

    static error(message, error = null) {
        Logger.error(`[Debug] ${message}`, null, error);
    }

    static warn(message, data = null) {
        Logger.warn(`[Debug] ${message}`, data);
    }

    // Test API connectivity
    static async testAPI() {
        this.log('Testing API connectivity...');

        try {
            // Test health endpoint
            const healthResponse = await fetch(`${CONFIG.API_BASE_URL}/health`);
            const healthData = await healthResponse.json();
            this.log('Health check response:', healthData);

            // Test if user is authenticated
            const token = localStorage.getItem(CONFIG.TOKEN_KEY);
            if (token) {
                this.log('User token found, testing authentication...');
                try {
                    const profileResponse = await fetch(`${CONFIG.API_BASE_URL}/auth/me`, {
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    if (profileResponse.ok) {
                        const profileData = await profileResponse.json();
                        this.log('User profile:', profileData);
                    } else {
                        this.warn('Token appears to be invalid or expired');
                    }
                } catch (error) {
                    this.error('Failed to validate user token:', error);
                }
            } else {
                this.log('No user token found - user is not authenticated');
            }

        } catch (error) {
            this.error('API connectivity test failed:', error);
            showToast('Unable to connect to the server. Please check if the backend is running.', TOAST_TYPES.ERROR);
        }
    }

    // Clear all application data
    static clearAllData() {
        if (!this.enabled) return;

        const confirmation = confirm('This will clear all local data including login tokens. Continue?');
        if (!confirmation) return;

        localStorage.clear();
        sessionStorage.clear();
        this.log('All local data cleared');
        window.location.reload();
    }

    // Show current application state
    static showAppState() {
        if (!this.enabled) return;

        const state = {
            authenticated: authManager?.isAuthenticated() || false,
            currentUser: authManager?.getCurrentUser() || null,
            apiBaseUrl: CONFIG.API_BASE_URL,
            tokens: {
                hasAccessToken: !!localStorage.getItem(CONFIG.TOKEN_KEY),
                hasRefreshToken: !!localStorage.getItem(CONFIG.REFRESH_TOKEN_KEY)
            },
            notesCount: notesManager?.currentNotes?.length || 0,
            currentPage: notesManager?.currentPage || 1,
            currentFilters: notesManager?.currentFilters || {}
        };

        console.table(state);
        return state;
    }

    // Enable/disable debug mode
    static setDebugMode(enabled) {
        this.enabled = enabled;
        localStorage.setItem('notemesh_debug', enabled ? 'true' : 'false');
        this.log(`Debug mode ${enabled ? 'enabled' : 'disabled'}`);
    }

    // Initialize debug mode from localStorage
    static init() {
        // Initialize Logger first
        Logger.init();

        const savedDebug = localStorage.getItem('notemesh_debug');
        if (savedDebug !== null) {
            this.enabled = savedDebug === 'true';
        }

        Logger.info('Debug Helper initialized', { enabled: this.enabled });

        // Make debug functions available globally
        window.debugNoteMesh = {
            testAPI: () => this.testAPI(),
            clearData: () => this.clearAllData(),
            showState: () => this.showAppState(),
            setDebug: (enabled) => this.setDebugMode(enabled),
            setLogLevel: (level) => Logger.setLevel(level),
            getLogs: (count) => Logger.getLogs(count),
            exportLogs: () => Logger.exportLogs(),
            clearLogs: () => Logger.clearLogs(),
            log: (msg, data) => this.log(msg, data)
        };
        Logger.info('Debug utilities available at window.debugNoteMesh');
    }
}

// Enhanced error handling
window.addEventListener('error', (event) => {
    Logger.error('JavaScript Error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
    }, event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    Logger.error('Unhandled Promise Rejection', null, event.reason);
    event.preventDefault(); // Prevent console spam
});

// Initialize debug helper
DebugHelper.init();

// Monitor fetch requests
const originalFetch = window.fetch;
window.fetch = async (...args) => {
    const [url, options] = args;
    const method = options?.method || 'GET';
    const requestId = Math.random().toString(36).substr(2, 9);

    Logger.trace(`→ HTTP ${method} ${url}`, {
        requestId,
        headers: options?.headers,
        body: options?.body ? JSON.parse(options.body) : null
    });

    const startTime = Date.now();

    try {
        const response = await originalFetch(...args);
        const duration = Date.now() - startTime;

        if (response.ok) {
            Logger.debug(`← ${response.status} ${method} ${url} (${duration}ms)`, { requestId });
        } else {
            Logger.warn(`← ${response.status} ${method} ${url} (${duration}ms)`, {
                requestId,
                statusText: response.statusText
            });
        }

        return response;
    } catch (error) {
        const duration = Date.now() - startTime;
        Logger.error(`✘ ${method} ${url} (${duration}ms)`, { requestId }, error);
        throw error;
    }
};