// Authentication module for NoteMesh
class AuthManager {
    constructor() {
        this.currentUser = null;
        this.loadUserFromStorage();
    }

    // Load user data from localStorage
    loadUserFromStorage() {
        const userData = localStorage.getItem(CONFIG.USER_KEY);
        if (userData) {
            try {
                this.currentUser = JSON.parse(userData);
            } catch (error) {
                console.error('Failed to parse user data:', error);
                localStorage.removeItem(CONFIG.USER_KEY);
            }
        }
    }

    // Check if user is authenticated
    isAuthenticated() {
        return !!(apiClient.token && this.currentUser);
    }

    // Get current user
    getCurrentUser() {
        return this.currentUser;
    }

    // Handle login form submission
    async handleLogin(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const username = formData.get('username').trim();
        const password = formData.get('password');

        if (!username || !password) {
            showToast('Please fill in all fields', TOAST_TYPES.ERROR);
            return;
        }

        try {
            const response = await apiClient.login(username, password);
            this.currentUser = response.user;

            showToast(`Welcome back, ${this.currentUser.full_name || this.currentUser.username}!`, TOAST_TYPES.SUCCESS);
            this.showDashboard();

        } catch (error) {
            console.error('Login failed:', error);
            showToast(error.message || 'Login failed', TOAST_TYPES.ERROR);
        }
    }

    // Handle register form submission
    async handleRegister(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const userData = {
            username: formData.get('username').trim(),
            email: formData.get('email').trim(),
            full_name: formData.get('full_name').trim(),
            password: formData.get('password'),
            confirm_password: formData.get('confirm_password')
        };

        // Validate form data
        if (!this.validateRegisterForm(userData)) {
            return;
        }

        try {
            await apiClient.register(userData);
            showToast('Registration successful! Please log in.', TOAST_TYPES.SUCCESS);
            this.showLoginForm();

        } catch (error) {
            console.error('Registration failed:', error);
            showToast(error.message || 'Registration failed', TOAST_TYPES.ERROR);
        }
    }

    // Validate registration form
    validateRegisterForm(userData) {
        const { username, email, full_name, password, confirm_password } = userData;

        if (!username || !email || !full_name || !password || !confirm_password) {
            showToast('Please fill in all fields', TOAST_TYPES.ERROR);
            return false;
        }

        if (username.length < 3) {
            showToast('Username must be at least 3 characters long', TOAST_TYPES.ERROR);
            return false;
        }

        if (!this.isValidEmail(email)) {
            showToast('Please enter a valid email address', TOAST_TYPES.ERROR);
            return false;
        }

        if (password.length < 8) {
            showToast('Password must be at least 8 characters long', TOAST_TYPES.ERROR);
            return false;
        }

        if (password !== confirm_password) {
            showToast('Passwords do not match', TOAST_TYPES.ERROR);
            return false;
        }

        return true;
    }

    // Validate email format
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Handle logout
    async handleLogout() {
        try {
            await apiClient.logout();
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.currentUser = null;
            this.showAuthSection();
            showToast('You have been logged out', TOAST_TYPES.INFO);
        }
    }

    // Show authentication section
    showAuthSection() {
        document.getElementById('authSection').classList.remove('hidden');
        document.getElementById('dashboardSection').classList.add('hidden');
        document.getElementById('noteDetailSection').classList.add('hidden');
        document.getElementById('noteEditorSection').classList.add('hidden');

        // Hide navigation
        document.querySelector('.nav-links').style.display = 'none';
        document.getElementById('userInfo').style.display = 'none';
    }

    // Show dashboard
    showDashboard() {
        document.getElementById('authSection').classList.add('hidden');
        document.getElementById('dashboardSection').classList.remove('hidden');
        document.getElementById('noteDetailSection').classList.add('hidden');
        document.getElementById('noteEditorSection').classList.add('hidden');

        // Show navigation
        document.querySelector('.nav-links').style.display = 'flex';
        document.getElementById('userInfo').style.display = 'block';
        document.getElementById('currentUser').textContent =
            this.currentUser?.full_name || this.currentUser?.username || 'User';

        // Load notes
        notesManager.loadNotes();
    }

    // Show login form
    showLoginForm() {
        document.getElementById('loginForm').classList.remove('hidden');
        document.getElementById('registerForm').classList.add('hidden');
        document.getElementById('authTitle').textContent = 'Login to NoteMesh';
        document.getElementById('authSubtitle').textContent = 'Manage and share your notes securely';

        // Clear forms
        document.getElementById('loginForm').reset();
        document.getElementById('registerForm').reset();
    }

    // Show register form
    showRegisterForm() {
        document.getElementById('loginForm').classList.add('hidden');
        document.getElementById('registerForm').classList.remove('hidden');
        document.getElementById('authTitle').textContent = 'Join NoteMesh';
        document.getElementById('authSubtitle').textContent = 'Create your account to start sharing notes';

        // Clear forms
        document.getElementById('loginForm').reset();
        document.getElementById('registerForm').reset();
    }

    // Initialize authentication UI
    initializeAuth() {
        // Set up form event listeners
        document.getElementById('loginForm').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('registerForm').addEventListener('submit', (e) => this.handleRegister(e));

        // Set up form switchers
        document.getElementById('showRegister').addEventListener('click', (e) => {
            e.preventDefault();
            this.showRegisterForm();
        });

        document.getElementById('showLogin').addEventListener('click', (e) => {
            e.preventDefault();
            this.showLoginForm();
        });

        // Set up logout link
        document.getElementById('logoutLink').addEventListener('click', (e) => {
            e.preventDefault();
            this.handleLogout();
        });

        // Check if user is already authenticated
        if (this.isAuthenticated()) {
            this.showDashboard();
        } else {
            this.showAuthSection();
            this.showLoginForm();
        }
    }
}

// Create global auth manager instance
const authManager = new AuthManager();