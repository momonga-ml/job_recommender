import { apiService } from './api';
import api from './api';
import { JobAnalysis } from '../types';

export const analyzeJobMatch = async (jobId: string, resumeId: string): Promise<JobAnalysis> => {
  return apiService.post<JobAnalysis>('/analysis/job-match', {
    jobId,
    resumeId,
  });
};

export const getAnalyses = async (params: {
  resumeId?: string;
  jobId?: string;
  page?: number;
  limit?: number;
  sortBy?: 'match' | 'date';
  sortOrder?: 'asc' | 'desc';
}): Promise<JobAnalysis[]> => {
  return apiService.get<JobAnalysis[]>('/analysis', params);
};

export const getAnalysisById = async (analysisId: string): Promise<JobAnalysis> => {
  return apiService.get<JobAnalysis>(`/analysis/${analysisId}`);
};

export const deleteAnalysis = async (analysisId: string): Promise<void> => {
  return apiService.delete<void>(`/analysis/${analysisId}`);
};

export const bulkAnalyzeJobs = async (jobIds: string[], resumeId: string): Promise<JobAnalysis[]> => {
  return apiService.post<JobAnalysis[]>('/analysis/bulk-analyze', {
    jobIds,
    resumeId,
  });
};

export const getTopSkills = async (resumeId: string): Promise<Array<{
  skill: string;
  frequency: number;
  importance: number;
  hasSkill: boolean;
}>> => {
  return apiService.get(`/analysis/${resumeId}/top-skills`);
};

export const getSkillGapAnalysis = async (resumeId: string): Promise<{
  missingSkills: Array<{
    skill: string;
    importance: number;
    frequency: number;
    relatedJobs: number;
  }>;
  skillDemand: Array<{
    skill: string;
    currentLevel: number;
    marketDemand: number;
    gap: number;
  }>;
  recommendations: string[];
}> => {
  return apiService.get(`/analysis/${resumeId}/skill-gaps`);
};

export const getSalaryInsights = async (params: {
  resumeId: string;
  location?: string;
  experience?: string;
  skills?: string[];
}): Promise<{
  currentMarketValue: {
    min: number;
    max: number;
    median: number;
    average: number;
  };
  experienceImpact: {
    currentLevel: string;
    nextLevel: string;
    salaryIncrease: number;
  };
  skillImpact: Array<{
    skill: string;
    salaryBoost: number;
    hasSkill: boolean;
  }>;
  locationImpact: Array<{
    location: string;
    salaryMultiplier: number;
  }>;
  recommendations: string[];
}> => {
  return apiService.get(`/analysis/salary-insights`, params);
};

export const getCareerProgression = async (resumeId: string): Promise<{
  currentLevel: string;
  nextRoles: Array<{
    title: string;
    requiredSkills: string[];
    missingSkills: string[];
    salaryRange: { min: number; max: number };
    timeToTransition: string;
  }>;
  skillDevelopmentPlan: Array<{
    skill: string;
    priority: 'high' | 'medium' | 'low';
    estimatedLearningTime: string;
    resources: string[];
  }>;
  certificationRecommendations: Array<{
    name: string;
    provider: string;
    value: number;
    timeToComplete: string;
  }>;
}> => {
  return apiService.get(`/analysis/${resumeId}/career-progression`);
};

export const getIndustryAnalysis = async (resumeId: string): Promise<{
  currentIndustry: string;
  relatedIndustries: Array<{
    industry: string;
    matchScore: number;
    averageSalary: number;
    growthRate: number;
    requiredSkills: string[];
  }>;
  growthPotential: {
    currentIndustryGrowth: number;
    recommendedTransitions: string[];
    emergingTrends: string[];
  };
}> => {
  return apiService.get(`/analysis/${resumeId}/industry-analysis`);
};

export const getCompetitiveAnalysis = async (resumeId: string, jobId?: string): Promise<{
  overallCompetitiveness: number;
  strengths: string[];
  weaknesses: string[];
  differentiators: string[];
  improvementAreas: Array<{
    area: string;
    impact: 'high' | 'medium' | 'low';
    actionItems: string[];
  }>;
  benchmarking: {
    skillsVsMarket: Array<{
      skill: string;
      yourLevel: number;
      marketAverage: number;
      topPerformerLevel: number;
    }>;
    experienceVsMarket: {
      yourExperience: number;
      marketAverage: number;
      recommendedExperience: number;
    };
  };
}> => {
  return apiService.get(`/analysis/${resumeId}/competitive-analysis`, jobId ? { jobId } : {});
};

export const generateResumeRecommendations = async (
  resumeId: string,
  targetJobIds?: string[]
): Promise<{
  contentRecommendations: Array<{
    section: string;
    suggestion: string;
    impact: 'high' | 'medium' | 'low';
    example: string;
  }>;
  keywordOptimization: Array<{
    keyword: string;
    currentUsage: number;
    recommendedUsage: number;
    context: string[];
  }>;
  structureImprovements: Array<{
    improvement: string;
    rationale: string;
    priority: number;
  }>;
  atsOptimization: {
    score: number;
    issues: string[];
    fixes: string[];
  };
}> => {
  return apiService.post(`/analysis/${resumeId}/resume-recommendations`, {
    targetJobIds,
  });
};

export const exportAnalysis = async (
  analysisIds: string[],
  format: 'pdf' | 'excel' | 'csv'
): Promise<Blob> => {
  const response = await api.post('/analysis/export', {
    analysisIds,
    format,
  }, {
    responseType: 'blob',
  });
  return response.data;
};

export const shareAnalysis = async (analysisId: string, options: {
  includePersonalInfo: boolean;
  expiresIn: number; // days
  password?: string;
}): Promise<{
  shareUrl: string;
  expiresAt: string;
}> => {
  return apiService.post(`/analysis/${analysisId}/share`, options);
};