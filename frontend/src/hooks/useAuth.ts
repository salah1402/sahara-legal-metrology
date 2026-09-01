import { useState, useEffect, useCallback } from 'react';
import type { User, LoginCredentials } from '../types/auth';
import * as authService from '../services/authService';
import { showToast } from './useToast';

export function useAuth() {
  const [user, setUser] = useState<User | null>(() => authService.getCurrentUser());
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    setUser(currentUser);
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      const result = await authService.login(credentials);
      setUser(result.user);
      showToast('success', 'Signed In', `Welcome back, ${result.user.name}`);
      return true;
    } catch (err: any) {
      showToast('error', 'Authentication Failed', err.message || 'Could not verify credentials.');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    showToast('info', 'Signed Out', 'You have been logged out of the inspection terminal.');
  }, []);

  return {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
  };
}
