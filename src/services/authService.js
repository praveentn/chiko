// src/services/authService.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

class AuthService {
  constructor() {
    this.token = localStorage.getItem('token');
  }

  async apiCall(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    // Add auth token if available
    if (this.token) {
      config.headers.Authorization = `Bearer ${this.token}`;
    }

    try {
      console.log(`API Call: ${config.method || 'GET'} ${url}`);
      const response = await fetch(url, config);
      
      // Handle 401 unauthorized responses
      if (response.status === 401) {
        this.logout();
        window.location.href = '/login';
        return null;
      }

      return response;
    } catch (error) {
      console.error('API call failed:', error);
      throw error;
    }
  }

  async login(email, password) {
    try {
      const response = await this.apiCall('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });

      if (response && response.ok) {
        const data = await response.json();
        this.token = data.access_token;
        localStorage.setItem('token', this.token);
        return { success: true, user: data.user, token: data.access_token };
      } else {
        const errorData = response ? await response.json() : { error: 'Login failed' };
        return { success: false, error: errorData.error };
      }
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: 'Network error occurred' };
    }
  }

  async logout() {
    try {
      if (this.token) {
        // Attempt to logout on server
        await this.apiCall('/auth/logout', {
          method: 'POST',
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear local storage
      this.token = null;
      localStorage.removeItem('token');
    }
  }

  async getCurrentUser() {
    try {
      if (!this.token) {
        return null;
      }

      const response = await this.apiCall('/auth/profile');
      
      if (response && response.ok) {
        const data = await response.json();
        return data.user;
      } else {
        // Token might be invalid
        this.logout();
        return null;
      }
    } catch (error) {
      console.error('Get current user error:', error);
      this.logout();
      return null;
    }
  }

  async verifyToken() {
    try {
      if (!this.token) {
        return false;
      }

      const response = await this.apiCall('/auth/verify');
      
      if (response && response.ok) {
        const data = await response.json();
        return data.valid;
      } else {
        this.logout();
        return false;
      }
    } catch (error) {
      console.error('Token verification error:', error);
      this.logout();
      return false;
    }
  }

  async register(userData) {
    try {
      const response = await this.apiCall('/auth/register', {
        method: 'POST',
        body: JSON.stringify(userData),
      });

      if (response && response.ok) {
        const data = await response.json();
        return { success: true, message: data.message };
      } else {
        const errorData = response ? await response.json() : { error: 'Registration failed' };
        return { success: false, error: errorData.error };
      }
    } catch (error) {
      console.error('Registration error:', error);
      return { success: false, error: 'Network error occurred' };
    }
  }

  async updateProfile(profileData) {
    try {
      const response = await this.apiCall('/auth/profile', {
        method: 'PUT',
        body: JSON.stringify(profileData),
      });

      if (response && response.ok) {
        const data = await response.json();
        return { success: true, user: data.user };
      } else {
        const errorData = response ? await response.json() : { error: 'Profile update failed' };
        return { success: false, error: errorData.error };
      }
    } catch (error) {
      console.error('Profile update error:', error);
      return { success: false, error: 'Network error occurred' };
    }
  }

  async changePassword(passwordData) {
    try {
      const response = await this.apiCall('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify(passwordData),
      });

      if (response && response.ok) {
        const data = await response.json();
        return { success: true, message: data.message };
      } else {
        const errorData = response ? await response.json() : { error: 'Password change failed' };
        return { success: false, error: errorData.error };
      }
    } catch (error) {
      console.error('Change password error:', error);
      return { success: false, error: 'Network error occurred' };
    }
  }

  async getUserSessions() {
    try {
      const response = await this.apiCall('/auth/sessions');
      
      if (response && response.ok) {
        const data = await response.json();
        return { success: true, sessions: data.sessions };
      } else {
        const errorData = response ? await response.json() : { error: 'Failed to get sessions' };
        return { success: false, error: errorData.error };
      }
    } catch (error) {
      console.error('Get sessions error:', error);
      return { success: false, error: 'Network error occurred' };
    }
  }

  async revokeSession(sessionId) {
    try {
      const response = await this.apiCall(`/auth/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      if (response && response.ok) {
        const data = await response.json();
        return { success: true, message: data.message };
      } else {
        const errorData = response ? await response.json() : { error: 'Failed to revoke session' };
        return { success: false, error: errorData.error };
      }
    } catch (error) {
      console.error('Revoke session error:', error);
      return { success: false, error: 'Network error occurred' };
    }
  }

  isAuthenticated() {
    return !!this.token;
  }

  getToken() {
    return this.token;
  }
}

const authService = new AuthService();
export default authService;