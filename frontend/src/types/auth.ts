/**
 * Authentication and Inspector Identity Types
 */

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'inspector' | 'senior_officer' | 'controller' | 'auditor';
  designation: string;
  department: string;
  jurisdictionZone: string;
  badgeId: string;
  avatarUrl?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
}

export interface LoginCredentials {
  email: string;
  password?: string;
  badgeId?: string;
}

export interface AuthResponse {
  user: User;
  token: string;
}
