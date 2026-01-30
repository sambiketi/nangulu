/**
 * Nangulu POS API Client
 * Pure JavaScript Fetch API implementation
 * Contract: Handles KG precision, JWT authentication, error handling
 */

class NanguluAPI {
    constructor(baseURL = '') {
        // Use relative path by default, can be overridden
        this.baseURL = baseURL || '';
        this.token = localStorage.getItem('nangulu_token');
        this.config = null;
    }

    /**
     * Initialize API configuration
     */
    async init() {
        try {
            const response = await this.request('/api/frontend/config');
            this.config = response;
            return response;
        } catch (error) {
            console.warn('Could not load frontend config:', error);
            return null;
        }
    }

    /**
     * Generic request handler with authentication
     */
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Add authorization token if available
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const config = {
            ...options,
            headers,
            credentials: 'include' // For CORS with credentials
        };

        try {
            const response = await fetch(url, config);
            
            // Handle authentication errors
            if (response.status === 401) {
                this.handleUnauthorized();
                throw new Error('Authentication required');
            }

            // Handle other errors
            if (!response.ok) {
                const error = await this.parseError(response);
                throw error;
            }

            // Parse JSON response
            const data = await response.json();
            return data;

        } catch (error) {
            // Network errors or JSON parsing errors
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('Network error. Please check your connection.');
            }
            throw error;
        }
    }

    /**
     * Parse error response
     */
    async parseError(response) {
        try {
            const errorData = await response.json();
            return new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
        } catch {
            return new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    }

    /**
     * Handle unauthorized access
     */
    handleUnauthorized() {
        localStorage.removeItem('nangulu_token');
        localStorage.removeItem('nangulu_user');
        
        // Redirect to login if not already there
        if (!window.location.pathname.includes('index.html')) {
            window.location.href = 'index.html';
        }
    }

    /**
     * Update authentication token
     */
    setToken(token) {
        this.token = token;
        localStorage.setItem('nangulu_token', token);
    }

    /**
     * Clear authentication
     */
    clearAuth() {
        this.token = null;
        localStorage.removeItem('nangulu_token');
        localStorage.removeItem('nangulu_user');
    }

    /**
     * Format KG value with 3 decimal places (Contract requirement)
     */
    formatKg(kg) {
        if (kg === null || kg === undefined) return '0.000 kg';
        
        try {
            const num = parseFloat(kg);
            if (isNaN(num)) return '0.000 kg';
            
            // Contract: 3 decimal places
            return `${num.toFixed(3)} kg`;
        } catch {
            return '0.000 kg';
        }
    }

    /**
     * Format price with currency
     */
    formatPrice(amount) {
        if (amount === null || amount === undefined) return '$0.00';
        
        try {
            const num = parseFloat(amount);
            if (isNaN(num)) return '$0.00';
            
            // Contract: 2 decimal places for currency
            return `$${num.toFixed(2)}`;
        } catch {
            return '$0.00';
        }
    }

    /**
     * Validate KG input (Contract: 3 decimal precision)
     */
    validateKgInput(kg) {
        if (!kg && kg !== 0) return false;
        
        const str = kg.toString();
        const parts = str.split('.');
        
        // Must have exactly 3 decimal places
        if (parts.length === 2 && parts[1].length !== 3) {
            return false;
        }
        
        // Must be a positive number
        const num = parseFloat(kg);
        return !isNaN(num) && num > 0;
    }

    /**
     * Convert KG to price
     */
    convertKgToPrice(kg, pricePerKg) {
        if (!this.validateKgInput(kg)) {
            throw new Error('Invalid KG format. Use 3 decimal places (e.g., 10.500)');
        }
        
        const kgNum = parseFloat(kg);
        const priceNum = parseFloat(pricePerKg);
        
        if (isNaN(kgNum) || isNaN(priceNum)) {
            throw new Error('Invalid numbers for conversion');
        }
        
        const total = kgNum * priceNum;
        return {
            kg: kgNum,
            price: total,
            formatted: {
                kg: this.formatKg(kgNum),
                price: this.formatPrice(total),
                pricePerKg: this.formatPrice(priceNum)
            }
        };
    }

    /**
     * Convert price to KG
     */
    convertPriceToKg(price, pricePerKg) {
        const priceNum = parseFloat(price);
        const pricePerKgNum = parseFloat(pricePerKg);
        
        if (isNaN(priceNum) || isNaN(pricePerKgNum) || pricePerKgNum === 0) {
            throw new Error('Invalid numbers for conversion');
        }
        
        const kg = priceNum / pricePerKgNum;
        
        // Contract: Round to 3 decimal places
        const roundedKg = Math.round(kg * 1000) / 1000;
        
        return {
            kg: roundedKg,
            price: priceNum,
            formatted: {
                kg: this.formatKg(roundedKg),
                price: this.formatPrice(priceNum),
                pricePerKg: this.formatPrice(pricePerKgNum)
            }
        };
    }

    // ===== API Endpoint Methods =====

    /**
     * Authentication
     */
    async login(username, password) {
        const response = await this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        
        if (response.access_token) {
            this.setToken(response.access_token);
            localStorage.setItem('nangulu_user', JSON.stringify(response.user));
        }
        
        return response;
    }

    async changePassword(currentPassword, newPassword) {
        return this.request('/api/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
    }

    async getAuthStatus() {
        return this.request('/api/auth/status');
    }

    /**
     * Frontend endpoints
     */
    async getFrontendConfig() {
        return this.request('/api/frontend/config');
    }

    async getFrontendHealth() {
        return this.request('/api/frontend/health');
    }

    async getInventorySimple() {
        return this.request('/api/frontend/inventory/simple');
    }

    async createSale(itemId, kgSold, customerName = '') {
        // Contract: Validate KG input
        if (!this.validateKgInput(kgSold)) {
            throw new Error('Invalid KG format. Use 3 decimal places (e.g., 10.500)');
        }
        
        return this.request('/api/frontend/sales/create', {
            method: 'POST',
            body: JSON.stringify({
                item_id: itemId,
                kg_sold: parseFloat(kgSold).toFixed(3),
                customer_name: customerName || undefined
            })
        });
    }

    async getDashboardData() {
        return this.request('/api/frontend/dashboard/current');
    }

    async convertKg(itemId, amount, isKg = true) {
        return this.request(`/api/frontend/utils/kg-convert?item_id=${itemId}&amount=${amount}&is_kg=${isKg}`);
    }

    /**
     * Cashier endpoints
     */
    async getCashierDashboard() {
        return this.request('/api/cashier/dashboard');
    }

    async getMySales(skip = 0, limit = 100) {
        return this.request(`/api/cashier/sales/me?skip=${skip}&limit=${limit}`);
    }

    async reverseSale(saleId, reason) {
        return this.request(`/api/cashier/sales/${saleId}/reverse`, {
            method: 'POST',
            body: JSON.stringify({ reversal_reason: reason })
        });
    }

    async getReceipt(saleId) {
        const response = await fetch(`${this.baseURL}/api/cashier/sales/${saleId}/receipt`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to get receipt');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        return url;
    }

    async getStockAlerts() {
        return this.request('/api/cashier/alerts/stock');
    }

    /**
     * Inventory endpoints
     */
    async getInventoryItems() {
        return this.request('/api/inventory/items');
    }

    async getItemStock(itemId) {
        return this.request(`/api/inventory/stock/${itemId}`);
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.token;
    }

    /**
     * Get current user
     */
    getCurrentUser() {
        try {
            const userStr = localStorage.getItem('nangulu_user');
            return userStr ? JSON.parse(userStr) : null;
        } catch {
            return null;
        }
    }

    /**
     * Get user role
     */
    getUserRole() {
        const user = this.getCurrentUser();
        return user ? user.role : null;
    }

    /**
     * Check if user is admin
     */
    isAdmin() {
        return this.getUserRole() === 'admin';
    }

    /**
     * Check if user is cashier
     */
    isCashier() {
        return this.getUserRole() === 'cashier';
    }
}

// Create global instance
window.NanguluAPI = new NanguluAPI();
