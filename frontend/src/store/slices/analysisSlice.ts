import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { AnalysisState, JobAnalysis } from '../../types';
import * as analysisService from '../../services/analysisService';

const initialState: AnalysisState = {
  analyses: [],
  currentAnalysis: null,
  isLoading: false,
  error: null,
};

// Async thunks
export const analyzeJobMatch = createAsyncThunk(
  'analysis/analyzeJobMatch',
  async ({ jobId, resumeId }: { jobId: string; resumeId: string }, { rejectWithValue }) => {
    try {
      const analysis = await analysisService.analyzeJobMatch(jobId, resumeId);
      return analysis;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Job analysis failed');
    }
  }
);

export const getAnalyses = createAsyncThunk(
  'analysis/getAnalyses',
  async (params: { resumeId?: string; jobId?: string; page?: number; limit?: number }, { rejectWithValue }) => {
    try {
      const analyses = await analysisService.getAnalyses(params);
      return analyses;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to get analyses');
    }
  }
);

export const getAnalysisById = createAsyncThunk(
  'analysis/getAnalysisById',
  async (analysisId: string, { rejectWithValue }) => {
    try {
      const analysis = await analysisService.getAnalysisById(analysisId);
      return analysis;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to get analysis');
    }
  }
);

export const deleteAnalysis = createAsyncThunk(
  'analysis/deleteAnalysis',
  async (analysisId: string, { rejectWithValue }) => {
    try {
      await analysisService.deleteAnalysis(analysisId);
      return analysisId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to delete analysis');
    }
  }
);

export const bulkAnalyzeJobs = createAsyncThunk(
  'analysis/bulkAnalyzeJobs',
  async ({ jobIds, resumeId }: { jobIds: string[]; resumeId: string }, { rejectWithValue }) => {
    try {
      const analyses = await analysisService.bulkAnalyzeJobs(jobIds, resumeId);
      return analyses;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Bulk analysis failed');
    }
  }
);

export const getTopSkills = createAsyncThunk(
  'analysis/getTopSkills',
  async (resumeId: string, { rejectWithValue }) => {
    try {
      const skills = await analysisService.getTopSkills(resumeId);
      return skills;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to get top skills');
    }
  }
);

export const getSkillGapAnalysis = createAsyncThunk(
  'analysis/getSkillGapAnalysis',
  async (resumeId: string, { rejectWithValue }) => {
    try {
      const skillGaps = await analysisService.getSkillGapAnalysis(resumeId);
      return skillGaps;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to get skill gap analysis');
    }
  }
);

export const getSalaryInsights = createAsyncThunk(
  'analysis/getSalaryInsights',
  async (params: { resumeId: string; location?: string; experience?: string }, { rejectWithValue }) => {
    try {
      const insights = await analysisService.getSalaryInsights(params);
      return insights;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to get salary insights');
    }
  }
);

const analysisSlice = createSlice({
  name: 'analysis',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setCurrentAnalysis: (state, action: PayloadAction<JobAnalysis | null>) => {
      state.currentAnalysis = action.payload;
    },
    clearCurrentAnalysis: (state) => {
      state.currentAnalysis = null;
    },
    updateAnalysisInList: (state, action: PayloadAction<JobAnalysis>) => {
      const updatedAnalysis = action.payload;
      const analysisIndex = state.analyses.findIndex(a => 
        a.jobId === updatedAnalysis.jobId && a.resumeId === updatedAnalysis.resumeId
      );
      
      if (analysisIndex !== -1) {
        state.analyses[analysisIndex] = updatedAnalysis;
      } else {
        state.analyses.unshift(updatedAnalysis);
      }
      
      // Update current analysis if it matches
      if (state.currentAnalysis && 
          state.currentAnalysis.jobId === updatedAnalysis.jobId && 
          state.currentAnalysis.resumeId === updatedAnalysis.resumeId) {
        state.currentAnalysis = updatedAnalysis;
      }
    },
    sortAnalyses: (state, action: PayloadAction<'match' | 'date' | 'job'>) => {
      const sortBy = action.payload;
      
      state.analyses.sort((a, b) => {
        switch (sortBy) {
          case 'match':
            return b.overallMatch - a.overallMatch;
          case 'date':
            return new Date(b.analysisDate).getTime() - new Date(a.analysisDate).getTime();
          case 'job':
            return a.jobId.localeCompare(b.jobId);
          default:
            return 0;
        }
      });
    },
  },
  extraReducers: (builder) => {
    builder
      // Analyze Job Match
      .addCase(analyzeJobMatch.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(analyzeJobMatch.fulfilled, (state, action) => {
        state.isLoading = false;
        const analysis = action.payload;
        
        // Remove any existing analysis for the same job and resume
        state.analyses = state.analyses.filter(a => 
          !(a.jobId === analysis.jobId && a.resumeId === analysis.resumeId)
        );
        
        // Add the new analysis at the beginning
        state.analyses.unshift(analysis);
        state.currentAnalysis = analysis;
      })
      .addCase(analyzeJobMatch.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Get Analyses
      .addCase(getAnalyses.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getAnalyses.fulfilled, (state, action) => {
        state.isLoading = false;
        state.analyses = action.payload;
      })
      .addCase(getAnalyses.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Get Analysis By ID
      .addCase(getAnalysisById.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getAnalysisById.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentAnalysis = action.payload;
        
        // Update the analysis in the list if it exists
        const analysisIndex = state.analyses.findIndex(a => 
          a.jobId === action.payload.jobId && a.resumeId === action.payload.resumeId
        );
        
        if (analysisIndex !== -1) {
          state.analyses[analysisIndex] = action.payload;
        }
      })
      .addCase(getAnalysisById.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Delete Analysis
      .addCase(deleteAnalysis.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(deleteAnalysis.fulfilled, (state, action) => {
        state.isLoading = false;
        // Note: Since we only have analysisId, we need to find by it
        // In a real implementation, you might want to store analysisId in the JobAnalysis type
        const analysisId = action.payload;
        // For now, we'll just reload analyses or handle this differently
        // state.analyses = state.analyses.filter(a => a.id !== analysisId);
      })
      .addCase(deleteAnalysis.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Bulk Analyze Jobs
      .addCase(bulkAnalyzeJobs.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(bulkAnalyzeJobs.fulfilled, (state, action) => {
        state.isLoading = false;
        const newAnalyses = action.payload;
        
        // Remove existing analyses for the same jobs and resume
        newAnalyses.forEach(newAnalysis => {
          state.analyses = state.analyses.filter(a => 
            !(a.jobId === newAnalysis.jobId && a.resumeId === newAnalysis.resumeId)
          );
        });
        
        // Add new analyses at the beginning
        state.analyses = [...newAnalyses, ...state.analyses];
      })
      .addCase(bulkAnalyzeJobs.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const {
  clearError,
  setCurrentAnalysis,
  clearCurrentAnalysis,
  updateAnalysisInList,
  sortAnalyses,
} = analysisSlice.actions;

export default analysisSlice.reducer;