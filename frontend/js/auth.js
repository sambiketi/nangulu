/**
 * Authentication Management
 * Handles login, session management, and route protection
 */

class AuthManager {
    constructor() {
        this.api = window.NanguluAPI;
        this.currentUser = null;
        this.checkAuthStatus();
    }

    /**
     * Check authentication status on page load
     */
    async checkAuthStatus() {
        const token = localStorage.getItem('nangulu_token');
        const userStr = localStorage.getItem('nangulu_user');
        
        if (token && userStr) {
            try {
                this.currentUser = JSON.parse(userStr);
                this.api.setToken(token);
                
                // Verify token is still valid
                await this.validateToken();
                
                // Redirect to dashboard if on login page
                if (this.shouldRedirectToDashboard()) {
                    this.redirectToDashboard();
                }
                
            } catch (error) {
                console.warn('Invalid session:', error);
                this.clearSession();
            }
        } else {
            // No token found, clear any existing session
            this.clearSession();
            
            // Redirect to login if not on login page
            if (this.shouldRedirectToLogin()) {
                this.redirectToLogin();
            }
        }
    }

    /**
     * Validate token with backend
     */
    async validateToken() {
        try {
            await this.api.getAuthStatus();
            return true;
        } catch (error) {
            console.warn('Token validation failed:', error);
            this.clearSession();
            return false;
        }
    }

    /**
     * Handle login form submission
     */
    async handleLogin(event) {
        event.preventDefault();
        
        const form = event.target;
        const username = form.querySelector('#username').value.trim();
        const password = form.querySelector('#password').value;
        const submitBtn = form.querySelector('#loginBtn');
        const errorContainer = document.getElementById('errorContainer');
        const errorMessage = document.getElementById('errorMessage');
        
        // Show loading state
        this.setLoadingState(submitBtn, true);
        errorContainer.classList.add('hidden');
        
        try {
            const response = await this.api.login(username, password);
            
            if (response.access_token) {
                this.showSuccess('Login successful!');
                
                // Small delay for user to see success message
                setTimeout(() => {
                    this.redirectToDashboard();
                }, 1000);
            }
            
        } catch (error) {
            // Show error message
            errorMessage.textContent = error.message || 'Login failed. Please check your credentials.';
            errorContainer.classList.remove('hidden');
            
            // Clear password field
            form.querySelector('#password').value = '';
            
        } finally {
            this.setLoadingState(submitBtn, false);
        }
    }

    /**
     * Handle logout
     */
    async handleLogout() {
        try {
            this.api.clearAuth();
            this.currentUser = null;
            
            this.showSuccess('Logged out successfully');
            
            // Redirect to login
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 1000);
            
        } catch (error) {
            console.error('Logout error:', error);
            // Still clear local storage and redirect
            this.clearSession();
            window.location.href = 'index.html';
        }
    }

    /**
     * Set loading state for buttons
     */
    setLoadingState(button, isLoading) {
        const btnText = button.querySelector('.btn-text');
        const btnLoader = button.querySelector('.btn-loader');
        
        if (isLoading) {
            button.disabled = true;
            btnText.classList.add('hidden');
            btnLoader.classList.remove('hidden');
        } else {
            button.disabled = false;
            btnText.classList.remove('hidden');
            btnLoader.classList.add('hidden');
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        // Create toast notification
        this.showToast('success', 'Success', message);
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showToast('error', 'Error', message);
    }

    /**
     * Show toast notification
     */
    showToast(type, title, message) {
        const toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${this.getToastIcon(type)}</div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }

    /**
     * Get icon for toast type
     */
    getToastIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }

    /**
     * Create toast container if it doesn't exist
     */
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }

    /**
     * Clear session data
     */
    clearSession() {
        localStorage.removeItem('nangulu_token');
        localStorage.removeItem('nangulu_user');
        this.currentUser = null;
        this.api.clearAuth();
    }

    /**
     * Check if should redirect to dashboard
     */
    shouldRedirectToDashboard() {
        const currentPage = window.location.pathname;
        return currentPage.endsWith('index.html') || currentPage.endsWith('/');
    }

    /**
     * Check if should redirect to login
     */
    shouldRedirectToLogin() {
        const currentPage = window.location.pathname;
        const loginPages = ['index.html', 'login.html'];
        return !loginPages.some(page => currentPage.endsWith(page));
    }

    /**
     * Redirect to dashboard based on user role
     */
    redirectToDashboard() {
        const user = this.api.getCurrentUser();
        
        if (user && user.role === 'admin') {
            window.location.href = 'admin-dashboard.html';
        } else {
            window.location.href = 'cashier-dashboard.html';
        }
    }

    /**
     * Redirect to login page
     */
    redirectToLogin() {
        window.location.href = 'index.html';
    }

    /**
     * Update UI with user info
     */
    updateUserUI() {
        const user = this.api.getCurrentUser();
        
        if (!user) return;
        
        // Update user name in dashboard
        const userNameElements = document.querySelectorAll('#userName, .user-name');
        userNameElements.forEach(el => {
            if (el) el.textContent = user.full_name || user.username;
        });
        
        // Update user role
        const userRoleElements = document.querySelectorAll('#userRole, .user-role');
        userRoleElements.forEach(el => {
            if (el) el.textContent = user.role === 'admin' ? 'Admin Dashboard' : 'Cashier Dashboard';
        });
    }

    /**
     * Check API connection on login page
     */
    async checkAPIConnection() {
        const apiStatus = document.getElementById('apiStatus');
        if (!apiStatus) return;
        
        try {
            const response = await fetch(`${this.api.baseURL}/api/frontend/health`);
            
            if (response.ok) {
                apiStatus.textContent = 'API Connected ✓';
                apiStatus.className = 'api-status connected';
            } else {
                apiStatus.textContent = 'API Connection Failed';
                apiStatus.className = 'api-status disconnected';
            }
        } catch (error) {
            apiStatus.textContent = 'Cannot connect to API';
            apiStatus.className = 'api-status disconnected';
        }
    }
}

// Initialize auth manager when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
    
    // Setup login form if it exists
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => window.authManager.handleLogin(e));
    }
    
    // Setup logout button if it exists
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => window.authManager.handleLogout());
    }
    
    // Update user UI if on dashboard
    if (document.querySelector('.dashboard-page')) {
        window.authManager.updateUserUI();
    }
    
    // Check API connection on login page
    if (document.querySelector('.auth-page')) {
        window.authManager.checkAPIConnection();
    }
});
