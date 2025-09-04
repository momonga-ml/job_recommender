import { apiService } from './api';
import api from './api';
import { Job, JobSearchParams, JobSearchResult, DashboardStats } from '../types';

export const searchJobs = async (params: JobSearchParams): Promise<JobSearchResult> => {
  return apiService.get<JobSearchResult>('/jobs/search', params);
};

export const getJobById = async (jobId: string): Promise<Job> => {
  return apiService.get<Job>(`/jobs/${jobId}`);
};

export const getRecommendedJobs = async (params: {
  resumeId?: string;
  limit?: number;
  page?: number;
}): Promise<JobSearchResult> => {
  return apiService.get<JobSearchResult>('/jobs/recommended', params);
};

export const getSimilarJobs = async (jobId: string, limit: number = 10): Promise<Job[]> => {
  return apiService.get<Job[]>(`/jobs/${jobId}/similar`, { limit });
};

export const bookmarkJob = async (jobId: string): Promise<void> => {
  return apiService.post<void>(`/jobs/${jobId}/bookmark`);
};

export const unbookmarkJob = async (jobId: string): Promise<void> => {
  return apiService.delete<void>(`/jobs/${jobId}/bookmark`);
};

export const getBookmarkedJobs = async (params?: {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}): Promise<Job[]> => {
  return apiService.get<Job[]>('/jobs/bookmarked', params);
};

export const updateApplicationStatus = async (
  jobId: string,
  status: string,
  notes?: string
): Promise<Job> => {
  return apiService.patch<Job>(`/jobs/${jobId}/application`, {
    status,
    notes,
  });
};

export const getApplicationHistory = async (jobId: string): Promise<any[]> => {
  return apiService.get<any[]>(`/jobs/${jobId}/application/history`);
};

export const getTrendingJobs = async (params?: {
  location?: string;
  timeframe?: 'day' | 'week' | 'month';
  limit?: number;
}): Promise<Job[]> => {
  return apiService.get<Job[]>('/jobs/trending', params);
};

export const getJobsByCompany = async (company: string, params?: {
  page?: number;
  limit?: number;
}): Promise<JobSearchResult> => {
  return apiService.get<JobSearchResult>(`/jobs/company/${encodeURIComponent(company)}`, params);
};

export const getJobCategories = async (): Promise<string[]> => {
  return apiService.get<string[]>('/jobs/categories');
};

export const getPopularSkills = async (params?: {
  category?: string;
  location?: string;
  limit?: number;
}): Promise<Array<{ skill: string; count: number }>> => {
  return apiService.get<Array<{ skill: string; count: number }>>('/jobs/skills/popular', params);
};

export const getSalaryInsights = async (params: {
  title?: string;
  location?: string;
  experience?: string;
  skills?: string[];
}): Promise<{
  average: number;
  median: number;
  min: number;
  max: number;
  percentiles: { [key: string]: number };
}> => {
  return apiService.get('/jobs/salary-insights', params);
};

export const getJobStats = async (): Promise<{
  totalJobs: number;
  newJobsToday: number;
  newJobsThisWeek: number;
  topCompanies: Array<{ company: string; count: number }>;
  topLocations: Array<{ location: string; count: number }>;
}> => {
  return apiService.get('/jobs/stats');
};

export const exportJobs = async (params: {
  format: 'csv' | 'excel';
  jobIds?: string[];
  searchParams?: JobSearchParams;
}): Promise<Blob> => {
  const response = await api.post('/jobs/export', params, {
    responseType: 'blob',
  });
  return response.data;
};

export const reportJob = async (jobId: string, reason: string, details?: string): Promise<void> => {
  return apiService.post<void>(`/jobs/${jobId}/report`, {
    reason,
    details,
  });
};

export const getDashboardStats = async (): Promise<DashboardStats> => {
  return apiService.get<DashboardStats>('/jobs/dashboard-stats');
};