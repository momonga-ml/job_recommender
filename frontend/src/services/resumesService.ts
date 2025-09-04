import { apiService } from './api';
import api from './api';
import { Resume, ParsedResumeData } from '../types';

export const getResumes = async (): Promise<Resume[]> => {
  return apiService.get<Resume[]>('/resumes');
};

export const getResumeById = async (resumeId: string): Promise<Resume> => {
  return apiService.get<Resume>(`/resumes/${resumeId}`);
};

export const uploadResume = async (
  file: File,
  onProgress?: (progress: number) => void
): Promise<Resume> => {
  const formData = new FormData();
  formData.append('file', file);
  
  return apiService.upload<Resume>('/resumes/upload', formData, onProgress);
};

export const deleteResume = async (resumeId: string): Promise<void> => {
  return apiService.delete<void>(`/resumes/${resumeId}`);
};

export const updateResume = async (resumeId: string, data: Partial<Resume>): Promise<Resume> => {
  return apiService.patch<Resume>(`/resumes/${resumeId}`, data);
};

export const setActiveResume = async (resumeId: string): Promise<Resume> => {
  return apiService.post<Resume>(`/resumes/${resumeId}/set-active`);
};

export const reprocessResume = async (resumeId: string): Promise<Resume> => {
  return apiService.post<Resume>(`/resumes/${resumeId}/reprocess`);
};

export const downloadResume = async (resumeId: string): Promise<Blob> => {
  const response = await api.get(`/resumes/${resumeId}/download`, {
    responseType: 'blob',
  });
  return response.data;
};

export const getResumeText = async (resumeId: string): Promise<string> => {
  return apiService.get<string>(`/resumes/${resumeId}/text`);
};

export const updateParsedData = async (
  resumeId: string,
  parsedData: ParsedResumeData
): Promise<Resume> => {
  return apiService.patch<Resume>(`/resumes/${resumeId}/parsed-data`, {
    parsedData,
  });
};

export const getResumeSuggestions = async (resumeId: string): Promise<{
  improvementSuggestions: string[];
  skillGaps: string[];
  keywordOptimization: string[];
  formattingTips: string[];
}> => {
  return apiService.get(`/resumes/${resumeId}/suggestions`);
};

export const compareResumes = async (resumeIds: string[]): Promise<{
  skills: {
    byResume: { [resumeId: string]: string[] };
    common: string[];
    unique: { [resumeId: string]: string[] };
  };
  experience: {
    [resumeId: string]: number;
  };
  education: {
    [resumeId: string]: string[];
  };
}> => {
  return apiService.post('/resumes/compare', { resumeIds });
};

export const generateResumeVersion = async (
  resumeId: string,
  targetJob?: string,
  customizations?: {
    emphasizeSkills?: string[];
    highlightExperience?: string[];
    customSummary?: string;
  }
): Promise<Resume> => {
  return apiService.post<Resume>(`/resumes/${resumeId}/generate-version`, {
    targetJob,
    customizations,
  });
};

export const getResumeAnalytics = async (resumeId: string): Promise<{
  viewCount: number;
  downloadCount: number;
  analysisCount: number;
  lastViewed: string;
  popularSkills: string[];
  matchingJobs: number;
}> => {
  return apiService.get(`/resumes/${resumeId}/analytics`);
};

export const validateResumeFormat = async (file: File): Promise<{
  isValid: boolean;
  issues: string[];
  suggestions: string[];
  estimatedParsingSuccess: number;
}> => {
  const formData = new FormData();
  formData.append('file', file);
  
  return apiService.post('/resumes/validate', formData);
};

export const getResumeTemplates = async (): Promise<Array<{
  id: string;
  name: string;
  description: string;
  previewUrl: string;
  category: string;
}>> => {
  return apiService.get('/resumes/templates');
};

export const exportResume = async (
  resumeId: string,
  format: 'pdf' | 'docx' | 'txt',
  templateId?: string
): Promise<Blob> => {
  const response = await api.post(`/resumes/${resumeId}/export`, {
    format,
    templateId,
  }, {
    responseType: 'blob',
  });
  return response.data;
};