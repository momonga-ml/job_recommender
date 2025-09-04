export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
}

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  requirements: string[];
  skills: string[];
  salaryMin?: number;
  salaryMax?: number;
  jobType: 'full-time' | 'part-time' | 'contract' | 'internship';
  experience: 'entry' | 'mid' | 'senior' | 'executive';
  remote: boolean;
  url: string;
  datePosted: string;
  source: string;
  isBookmarked?: boolean;
  applicationStatus?: ApplicationStatus;
}

export interface JobSearchParams {
  query?: string;
  location?: string;
  jobType?: string[];
  experience?: string[];
  remote?: boolean;
  salaryMin?: number;
  salaryMax?: number;
  skills?: string[];
  page?: number;
  limit?: number;
  sortBy?: 'date' | 'salary' | 'relevance';
  sortOrder?: 'asc' | 'desc';
}

export interface JobSearchResult {
  jobs: Job[];
  total: number;
  page: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface JobsState {
  jobs: Job[];
  bookmarkedJobs: Job[];
  currentJob: Job | null;
  searchResults: JobSearchResult | null;
  isLoading: boolean;
  error: string | null;
  searchParams: JobSearchParams;
}

export interface Resume {
  id: string;
  filename: string;
  originalName: string;
  uploadDate: string;
  status: 'processing' | 'completed' | 'error';
  size: number;
  parsedData?: ParsedResumeData;
  isActive: boolean;
}

export interface ParsedResumeData {
  personalInfo: {
    name?: string;
    email?: string;
    phone?: string;
    location?: string;
  };
  summary?: string;
  skills: string[];
  experience: WorkExperience[];
  education: Education[];
  certifications?: Certification[];
}

export interface WorkExperience {
  company: string;
  position: string;
  startDate: string;
  endDate?: string;
  description: string;
  skills: string[];
}

export interface Education {
  institution: string;
  degree: string;
  field?: string;
  startDate?: string;
  endDate?: string;
  gpa?: number;
}

export interface Certification {
  name: string;
  issuer: string;
  dateIssued?: string;
  expiryDate?: string;
  credentialId?: string;
}

export interface ResumesState {
  resumes: Resume[];
  activeResume: Resume | null;
  isLoading: boolean;
  error: string | null;
  uploadProgress: number;
}

export interface SkillMatch {
  skill: string;
  hasSkill: boolean;
  proficiency?: number;
  importance: number;
}

export interface JobAnalysis {
  jobId: string;
  resumeId: string;
  overallMatch: number;
  skillsMatch: SkillMatch[];
  missingSkills: string[];
  strengths: string[];
  recommendations: string[];
  salaryFit: {
    resumeExpectedSalary?: number;
    jobSalaryRange: {
      min?: number;
      max?: number;
    };
    fit: 'below' | 'within' | 'above';
  };
  experienceMatch: {
    required: string;
    current: string;
    match: boolean;
  };
  analysisDate: string;
}

export interface AnalysisState {
  analyses: JobAnalysis[];
  currentAnalysis: JobAnalysis | null;
  isLoading: boolean;
  error: string | null;
}

export interface ApplicationStatus {
  status: 'saved' | 'applied' | 'interviewing' | 'offered' | 'rejected' | 'accepted';
  dateApplied?: string;
  notes?: string;
}

export interface DashboardStats {
  totalJobs: number;
  bookmarkedJobs: number;
  applications: number;
  analyses: number;
  averageMatch: number;
  topSkills: string[];
  recentActivity: ActivityItem[];
}

export interface ActivityItem {
  id: string;
  type: 'job_saved' | 'resume_uploaded' | 'analysis_completed' | 'application_submitted';
  title: string;
  description: string;
  date: string;
  metadata?: Record<string, any>;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, any>;
}

export interface PaginationParams {
  page: number;
  limit: number;
}

export interface SortParams {
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

export interface FileUploadResponse {
  id: string;
  filename: string;
  originalName: string;
  url: string;
  size: number;
}

export interface ChartData {
  name: string;
  value: number;
  color?: string;
}

export interface RadarChartData {
  skill: string;
  current: number;
  required: number;
}