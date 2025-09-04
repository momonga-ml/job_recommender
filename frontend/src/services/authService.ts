import { apiService } from './api';
import { User, LoginCredentials, RegisterData } from '../types';

export interface AuthResponse {
  user: User;
  token: string;
  refreshToken: string;
}

export interface RefreshTokenResponse {
  token: string;
  user: User;
}

export const login = async (credentials: LoginCredentials): Promise<AuthResponse> => {
  return apiService.post<AuthResponse>('/auth/login', credentials);
};

export const register = async (userData: RegisterData): Promise<AuthResponse> => {
  return apiService.post<AuthResponse>('/auth/register', userData);
};

export const logout = async (): Promise<void> => {
  return apiService.post<void>('/auth/logout');
};

export const getCurrentUser = async (): Promise<User> => {
  return apiService.get<User>('/auth/me');
};

export const refreshToken = async (): Promise<RefreshTokenResponse> => {
  const refreshToken = localStorage.getItem('refreshToken');
  return apiService.post<RefreshTokenResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  });
};

export const updateProfile = async (userData: Partial<User>): Promise<User> => {
  return apiService.patch<User>('/auth/profile', userData);
};

export const changePassword = async (data: {
  currentPassword: string;
  newPassword: string;
}): Promise<void> => {
  return apiService.post<void>('/auth/change-password', data);
};

export const forgotPassword = async (email: string): Promise<void> => {
  return apiService.post<void>('/auth/forgot-password', { email });
};

export const resetPassword = async (data: {
  token: string;
  password: string;
}): Promise<void> => {
  return apiService.post<void>('/auth/reset-password', data);
};

export const verifyEmail = async (token: string): Promise<void> => {
  return apiService.post<void>('/auth/verify-email', { token });
};

export const resendVerification = async (): Promise<void> => {
  return apiService.post<void>('/auth/resend-verification');
};