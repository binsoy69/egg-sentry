import api from './api';

export const authService = {
  login: async (username, password) => {
    const response = await api.post('/auth/login', {
      username,
      password,
    });

    if (response.data.access_token) {
      localStorage.setItem('token', response.data.access_token);
    }

    const meResponse = await api.get('/auth/me');
    localStorage.setItem('user', JSON.stringify(meResponse.data));
    return meResponse.data;
  },

  changePassword: async (currentPassword, newPassword) => {
    const response = await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },

  getCurrentUser: () => {
    const storedUser = localStorage.getItem('user');
    return storedUser ? JSON.parse(storedUser) : null;
  },

  isAuthenticated: () => {
    return !!localStorage.getItem('token');
  }
};
