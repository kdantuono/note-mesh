// UI utilities and components for NoteMesh

// Loading spinner management
function showSpinner(show) {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.classList.toggle('hidden', !show);
    }
}

// Toast notification system
function showToast(message, type = TOAST_TYPES.INFO, duration = CONFIG.TOAST_DURATION) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    // Toast icon based on type
    let icon = '';
    switch (type) {
        case TOAST_TYPES.SUCCESS:
            icon = '<i class="fas fa-check-circle"></i>';
            break;
        case TOAST_TYPES.ERROR:
            icon = '<i class="fas fa-exclamation-circle"></i>';
            break;
        case TOAST_TYPES.WARNING:
            icon = '<i class="fas fa-exclamation-triangle"></i>';
            break;
        case TOAST_TYPES.INFO:
        default:
            icon = '<i class="fas fa-info-circle"></i>';
            break;
    }

    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            ${icon}
            <span>${escapeHtml(message)}</span>
            <button onclick="this.parentElement.parentElement.remove()" style="margin-left: auto; background: none; border: none; cursor: pointer; opacity: 0.7;">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    container.appendChild(toast);

    // Auto-remove after duration
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideOutRight 0.3s ease-in forwards';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

// Sharing management
class SharingManager {
    constructor() {
        this.currentNote = null;
        this.sharedUsers = [];
    }

    // Show share modal
    showShareModal(note) {
        this.currentNote = note;
        this.loadNoteShares();
        document.getElementById('shareModal').classList.remove('hidden');
    }

    // Hide share modal
    hideShareModal() {
        document.getElementById('shareModal').classList.add('hidden');
        this.currentNote = null;
        this.sharedUsers = [];
    }

    // Load existing shares for the note
    async loadNoteShares() {
        if (!this.currentNote) return;

        try {
            // Get shares for this note (this would need to be implemented in the API)
            // For now, we'll use a placeholder
            this.sharedUsers = [];
            this.renderSharedUsers();

        } catch (error) {
            console.error('Failed to load note shares:', error);
        }
    }

    // Add user to share list
    async addUserToShare() {
        const usernameInput = document.getElementById('shareWithUser');
        const username = usernameInput.value.trim();

        if (!username) {
            showToast('Please enter a username', TOAST_TYPES.ERROR);
            return;
        }

        if (username === authManager.getCurrentUser()?.username) {
            showToast('You cannot share a note with yourself', TOAST_TYPES.ERROR);
            return;
        }

        // Basic username validation
        if (!/^[a-zA-Z0-9_]{3,20}$/.test(username)) {
            showToast('Username must be 3-20 characters (letters, numbers, underscore only)', TOAST_TYPES.ERROR);
            return;
        }

        // Check if user is already in the list
        if (this.sharedUsers.some(user => user.username === username)) {
            showToast('User is already in the share list', TOAST_TYPES.WARNING);
            return;
        }

        // Add to local list (will be saved when modal is confirmed)
        this.sharedUsers.push({
            username: username,
            permission: 'read', // Always read-only as per specs
            pending: true // Mark as pending until API call
        });

        this.renderSharedUsers();
        usernameInput.value = '';
    }

    // Remove user from share list
    removeUserFromShare(username) {
        this.sharedUsers = this.sharedUsers.filter(user => user.username !== username);
        this.renderSharedUsers();
    }

    // Render shared users list
    renderSharedUsers() {
        const container = document.getElementById('sharedUsers');

        if (this.sharedUsers.length === 0) {
            container.innerHTML = '<p class="text-muted">No users selected for sharing</p>';
            return;
        }

        const html = this.sharedUsers.map(user => `
            <div class="shared-user">
                <div class="shared-user-info">
                    <div class="shared-user-name">${escapeHtml(user.username)}</div>
                    <div class="shared-user-permission">Read Only Access</div>
                </div>
                <button onclick="sharingManager.removeUserFromShare('${escapeHtml(user.username)}')"
                        class="btn btn-outline" style="padding: 0.25rem 0.5rem;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    // Confirm sharing
    async confirmShare() {
        if (!this.currentNote || this.sharedUsers.length === 0) {
            showToast('No users selected for sharing', TOAST_TYPES.WARNING);
            return;
        }

        try {
            showSpinner(true);

            // Share with each user (read-only access)
            const sharePromises = this.sharedUsers.map(user =>
                apiClient.shareNote(this.currentNote.id, user.username, 'read')
            );

            const results = await Promise.allSettled(sharePromises);

            // Check results and provide detailed feedback
            const successful = results.filter(result => result.status === 'fulfilled').length;
            const failed = results.filter(result => result.status === 'rejected');

            if (successful > 0) {
                showToast(`Note shared with ${successful} user(s) (read-only access)`, TOAST_TYPES.SUCCESS);
            }

            if (failed.length > 0) {
                const failedUsernames = failed.map((result, index) => this.sharedUsers[results.indexOf(result)].username);
                showToast(`Failed to share with: ${failedUsernames.join(', ')}. They may not exist in the system.`, TOAST_TYPES.WARNING);
            }

            if (successful > 0) {
                this.hideShareModal();
                // Refresh the note detail to show updated sharing info
                if (notesManager && notesManager.currentNote) {
                    notesManager.showNoteDetail(notesManager.currentNote.id);
                }
            }

        } catch (error) {
            console.error('Failed to share note:', error);
            let errorMessage = 'Failed to share note';

            if (error.message && error.message !== '[object Object]') {
                errorMessage = error.message;
            } else if (error.detail) {
                errorMessage = error.detail;
            }

            showToast(errorMessage, TOAST_TYPES.ERROR);
        } finally {
            showSpinner(false);
        }
    }

    // Initialize sharing UI
    initializeSharing() {
        // Modal event listeners
        document.getElementById('closeShareModal').addEventListener('click', () => this.hideShareModal());
        document.getElementById('cancelShare').addEventListener('click', () => this.hideShareModal());
        document.getElementById('confirmShare').addEventListener('click', () => this.confirmShare());

        // Add user button
        document.getElementById('addShareUser').addEventListener('click', () => this.addUserToShare());

        // Allow Enter key to add user
        document.getElementById('shareWithUser').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.addUserToShare();
            }
        });

        // Close modal when clicking outside
        document.getElementById('shareModal').addEventListener('click', (e) => {
            if (e.target.id === 'shareModal') {
                this.hideShareModal();
            }
        });
    }
}

// Mobile navigation toggle
function initializeMobileNav() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
        });

        // Close mobile menu when clicking a link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
            });
        });

        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
                navMenu.classList.remove('active');
            }
        });
    }
}

// Navigation management
function initializeNavigation() {
    // Dashboard link
    document.getElementById('dashboardLink').addEventListener('click', (e) => {
        e.preventDefault();
        if (authManager.isAuthenticated()) {
            notesManager.showDashboard();
        }
    });

    // Profile link (placeholder)
    document.getElementById('profileLink').addEventListener('click', (e) => {
        e.preventDefault();
        showToast('Profile management coming soon!', TOAST_TYPES.INFO);
    });
}

// Utility function for HTML escaping
function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Keyboard shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Only handle shortcuts when not in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        // Ctrl/Cmd + N: New note
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            if (authManager.isAuthenticated()) {
                notesManager.showNoteEditor();
            }
        }

        // Escape: Close modals or go back
        if (e.key === 'Escape') {
            const shareModal = document.getElementById('shareModal');
            if (!shareModal.classList.contains('hidden')) {
                sharingManager.hideShareModal();
            } else {
                // Go back to dashboard
                if (authManager.isAuthenticated()) {
                    notesManager.showDashboard();
                }
            }
        }

        // Ctrl/Cmd + F: Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('searchInput');
            if (searchInput && !searchInput.closest('.hidden')) {
                searchInput.focus();
            }
        }
    });
}

// Form validation helpers
function validateNoteForm(formData) {
    const title = formData.get('title')?.trim();
    const content = formData.get('content')?.trim();

    if (!title) {
        showToast('Please enter a note title', TOAST_TYPES.ERROR);
        return false;
    }

    if (title.length > 200) {
        showToast('Note title must be less than 200 characters', TOAST_TYPES.ERROR);
        return false;
    }

    if (!content) {
        showToast('Please enter note content', TOAST_TYPES.ERROR);
        return false;
    }

    return true;
}

// Auto-save functionality (placeholder for future implementation)
function initializeAutoSave() {
    let autoSaveTimeout;
    const noteContentInput = document.getElementById('noteContentInput');
    const noteTitleInput = document.getElementById('noteTitleInput');

    function scheduleAutoSave() {
        clearTimeout(autoSaveTimeout);
        autoSaveTimeout = setTimeout(() => {
            // Auto-save implementation would go here
            console.log('Auto-save triggered');
        }, 30000); // Save every 30 seconds
    }

    if (noteContentInput && noteTitleInput) {
        [noteContentInput, noteTitleInput].forEach(input => {
            input.addEventListener('input', scheduleAutoSave);
        });
    }
}

// Create global sharing manager instance
const sharingManager = new SharingManager();

// Initialize all UI components
function initializeUI() {
    initializeMobileNav();
    initializeNavigation();
    initializeKeyboardShortcuts();
    initializeAutoSave();
    sharingManager.initializeSharing();
}