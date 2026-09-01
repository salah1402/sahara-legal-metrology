import type { User, LoginCredentials, AuthResponse } from '../types/auth';
import { getApiConfig } from './api';

const TOKEN_KEY = 'sahara_auth_token';
const USER_KEY = 'sahara_auth_user';

export const DEMO_INSPECTOR: User = {
  id: "USR-LM-2026-881",
  name: "Rajesh Kumar",
  email: "rajesh.kumar@metrology.gov.in",
  role: "inspector",
  designation: "Legal Metrology Officer (Class-I)",
  department: "Department of Consumer Affairs & Legal Metrology",
  jurisdictionZone: "Zone-4 / North-West Division",
  badgeId: "LM-DEL-8814",
  avatarUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=128&auto=format&fit=crop&q=80",
};

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  const config = getApiConfig();

  if (!config.useDemoFixtures) {
    try {
      const response = await fetch(`${config.baseUrl}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        throw new Error('Invalid credentials or unauthorized station code.');
      }

      const data: AuthResponse = await response.json();
      localStorage.setItem(TOKEN_KEY, data.token);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      return data;
    } catch (err: any) {
      throw new Error(err.message || 'Authentication service unreachable.');
    }
  }

  // Demo authentication fallback
  const user: User = {
    ...DEMO_INSPECTOR,
    email: credentials.email || DEMO_INSPECTOR.email,
    name: credentials.email ? credentials.email.split('@')[0].replace('.', ' ').toUpperCase() : DEMO_INSPECTOR.name,
  };
  const token = `demo_jwt_token_${Date.now()}`;

  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));

  return { user, token };
}

export function getCurrentUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
