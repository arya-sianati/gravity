import axios from 'axios';

export interface User {
  id: number;
  username: string;
  email: string;
  display_name: string;
  total_xp: number;
  current_level: number;
  level_start_xp: number;
  next_level_xp: number;
  level_progress: number;
  location_privacy_mode: 'hidden' | 'blurred' | 'friends' | 'exact';
  created_at: string;
  updated_at: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  email?: string;
  display_name?: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface UpdateProfilePayload {
  display_name?: string;
  email?: string;
  location_privacy_mode?: 'hidden' | 'blurred' | 'friends' | 'exact';
}

function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null;
  }
  return null;
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

// Ensure CSRF token is attached to mutating requests
apiClient.interceptors.request.use(async (config) => {
  const method = config.method?.toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method || '')) {
    let token = getCookie('csrftoken');
    if (!token) {
      try {
        const res = await axios.get('/api/auth/csrf/', { withCredentials: true });
        token = res.data.csrfToken || getCookie('csrftoken');
      } catch (err) {
        console.warn('Could not fetch CSRF token:', err);
      }
    }
    if (token) {
      config.headers['X-CSRFToken'] = token;
    }
  }
  return config;
});

export const checkHealth = async () => {
  const response = await apiClient.get('/health/');
  return response.data;
};

export const initCsrf = async () => {
  const response = await apiClient.get('/auth/csrf/');
  return response.data;
};

export const registerUser = async (data: RegisterPayload): Promise<User> => {
  const response = await apiClient.post<User>('/auth/register/', data);
  return response.data;
};

export const loginUser = async (data: LoginPayload): Promise<User> => {
  const response = await apiClient.post<User>('/auth/login/', data);
  return response.data;
};

export const logoutUser = async (): Promise<void> => {
  await apiClient.post('/auth/logout/');
};

export const getMe = async (): Promise<User> => {
  const response = await apiClient.get<User>('/me/');
  return response.data;
};

export const updateMe = async (data: UpdateProfilePayload): Promise<User> => {
  const response = await apiClient.patch<User>('/me/', data);
  return response.data;
};

export interface XPTransaction {
  id: number;
  amount: number;
  reason: string;
  description: string;
  activity_type: string | null;
  created_at: string;
}

export const getXPHistory = async (): Promise<XPTransaction[]> => {
  const response = await apiClient.get<XPTransaction[]>('/me/xp-history/');
  return response.data;
};

export interface BadgeEarned {
  slug: string;
  name: string;
  description: string;
  icon: string;
  earned_at: string;
}

export interface StreakInfo {
  current: number;
  longest: number;
}

export interface MyBadgesResponse {
  badges: BadgeEarned[];
  streak: StreakInfo;
}

export const getMyBadges = async (): Promise<MyBadgesResponse> => {
  const response = await apiClient.get<MyBadgesResponse>('/me/badges/');
  return response.data;
};
