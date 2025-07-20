// src/services/authService.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

class AuthService {
  async login(email, password) {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        return {
          success: true,
          user: data.user,
          token: data.access_token,
        };
      } else {
        return {
          success: false,
          error: data.error || 'Login failed',
        };
      }
    } catch (error) {
      return {
        success: false,
        error: 'Network error: ' + error.message,
      };
    }
  }

  async register(userData) {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      const data = await response.json();

      if (response.ok) {
        return {
          success: true,
          message: data.message,
        };
      } else {
        return {
          success: false,
          error: data.error || 'Registration failed',
        };
      }
    } catch (error) {
      return {
        success: false,
        error: 'Network error: ' + error.message,
      };
    }
  }

  async getCurrentUser() {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        return null;
      }

      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        return data.user;
      } else {
        // Token is invalid, remove it
        localStorage.removeItem('token');
        return null;
      }
    } catch (error) {
      console.error('Error getting current user:', error);
      localStorage.removeItem('token');
      return null;
    }
  }

  async refreshToken() {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        return null;
      }

      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        return data.access_token;
      } else {
        localStorage.removeItem('token');
        return null;
      }
    } catch (error) {
      console.error('Error refreshing token:', error);
      localStorage.removeItem('token');
      return null;
    }
  }

  async changePassword(oldPassword, newPassword) {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      return {
        success: response.ok,
        error: response.ok ? null : (data.error || 'Password change failed'),
        message: response.ok ? data.message : null,
      };
    } catch (error) {
      return {
        success: false,
        error: 'Network error: ' + error.message,
      };
    }
  }

  async forgotPassword(email) {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      return {
        success: response.ok,
        error: response.ok ? null : (data.error || 'Request failed'),
        message: response.ok ? data.message : null,
      };
    } catch (error) {
      return {
        success: false,
        error: 'Network error: ' + error.message,
      };
    }
  }

  async resetPassword(token, newPassword) {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      return {
        success: response.ok,
        error: response.ok ? null : (data.error || 'Password reset failed'),
        message: response.ok ? data.message : null,
      };
    } catch (error) {
      return {
        success: false,
        error: 'Network error: ' + error.message,
      };
    }
  }

  logout() {
    localStorage.removeItem('token');
    // Optionally call server-side logout endpoint
    this.serverLogout();
  }

  async serverLogout() {
    try {
      const token = localStorage.getItem('token');
      if (token) {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      }
    } catch (error) {
      // Ignore logout errors
      console.error('Logout error:', error);
    }
  }

  isAuthenticated() {
    return !!localStorage.getItem('token');
  }

  getToken() {
    return localStorage.getItem('token');
  }

  // Utility method to make authenticated API calls
  async apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
      },
    };

    const finalOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, finalOptions);
      
      // Handle token expiration
      if (response.status === 401) {
        // Try to refresh token
        const newToken = await this.refreshToken();
        if (newToken) {
          // Retry the request with new token
          finalOptions.headers.Authorization = `Bearer ${newToken}`;
          return await fetch(`${API_BASE_URL}${endpoint}`, finalOptions);
        } else {
          // Refresh failed, redirect to login
          this.logout();
          window.location.href = '/login';
          return null;
        }
      }

      return response;
    } catch (error) {
      console.error('API call error:', error);
      throw error;
    }
  }

  // Check if user has specific role
  hasRole(user, requiredRole) {
    if (!user || !user.role) {
      return false;
    }
    
    if (Array.isArray(requiredRole)) {
      return requiredRole.includes(user.role);
    }
    
    return user.role === requiredRole;
  }

  // Check if user has specific permission
  hasPermission(user, permission) {
    if (!user || !user.permissions) {
      return false;
    }
    
    return user.permissions.includes(permission);
  }
}

const authService = new AuthService();
export default authService;