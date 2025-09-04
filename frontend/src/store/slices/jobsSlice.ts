import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { JobsState, Job, JobSearchParams, JobSearchResult } from '../../types';
import * as jobsService from '../../services/jobsService';

const initialState: JobsState = {
  jobs: [],
  bookmarkedJobs: [],
  currentJob: null,
  searchResults: null,
  isLoading: false,
  error: null,
  searchParams: {
    page: 1,
    limit: 20,
    sortBy: 'date',
    sortOrder: 'desc',
  },
};

// Async thunks
export const searchJobs = createAsyncThunk(
  'jobs/searchJobs',
  async (params: JobSearchParams, { rejectWithValue }) => {
    try {
      const response = await jobsService.searchJobs(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Job search failed');
    }
  }
);

export const getJobById = createAsyncThunk(
  'jobs/getJobById',
  async (jobId: string, { rejectWithValue }) => {
    try {
      const job = await jobsService.getJobById(jobId);
      return job;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to get job details');
    }
  }
);

export const bookmarkJob = createAsyncThunk(
  'jobs/bookmarkJob',
  async (jobId: string, { rejectWithValue }) => {
    try {
      await jobsService.bookmarkJob(jobId);
      return jobId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to bookmark job');
    }
  }
);

export const unbookmarkJob = createAsyncThunk(
  'jobs/unbookmarkJob',
  async (jobId: string, { rejectWithValue }) => {
    try {
      await jobsService.unbookmarkJob(jobId);
      return jobId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to unbookmark job');
    }
  }
);

export const getBookmarkedJobs = createAsyncThunk(
  'jobs/getBookmarkedJobs',
  async (_, { rejectWithValue }) => {
    try {
      const jobs = await jobsService.getBookmarkedJobs();
      return jobs;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to get bookmarked jobs');
    }
  }
);

export const updateApplicationStatus = createAsyncThunk(
  'jobs/updateApplicationStatus',
  async ({ jobId, status, notes }: { jobId: string; status: string; notes?: string }, { rejectWithValue }) => {
    try {
      const updatedJob = await jobsService.updateApplicationStatus(jobId, status, notes);
      return updatedJob;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update application status');
    }
  }
);

const jobsSlice = createSlice({
  name: 'jobs',
  initialState,
  reducers: {
    setSearchParams: (state, action: PayloadAction<Partial<JobSearchParams>>) => {
      state.searchParams = { ...state.searchParams, ...action.payload };
    },
    clearSearchResults: (state) => {
      state.searchResults = null;
    },
    clearCurrentJob: (state) => {
      state.currentJob = null;
    },
    clearError: (state) => {
      state.error = null;
    },
    updateJobInList: (state, action: PayloadAction<Job>) => {
      const updatedJob = action.payload;
      
      // Update in main jobs list
      const jobIndex = state.jobs.findIndex(job => job.id === updatedJob.id);
      if (jobIndex !== -1) {
        state.jobs[jobIndex] = updatedJob;
      }
      
      // Update in search results
      if (state.searchResults) {
        const searchJobIndex = state.searchResults.jobs.findIndex(job => job.id === updatedJob.id);
        if (searchJobIndex !== -1) {
          state.searchResults.jobs[searchJobIndex] = updatedJob;
        }
      }
      
      // Update in bookmarked jobs
      const bookmarkedIndex = state.bookmarkedJobs.findIndex(job => job.id === updatedJob.id);
      if (bookmarkedIndex !== -1) {
        state.bookmarkedJobs[bookmarkedIndex] = updatedJob;
      }
      
      // Update current job if it matches
      if (state.currentJob && state.currentJob.id === updatedJob.id) {
        state.currentJob = updatedJob;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Search Jobs
      .addCase(searchJobs.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(searchJobs.fulfilled, (state, action) => {
        state.isLoading = false;
        state.searchResults = action.payload;
        state.jobs = action.payload.jobs;
      })
      .addCase(searchJobs.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Get Job By ID
      .addCase(getJobById.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getJobById.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentJob = action.payload;
      })
      .addCase(getJobById.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Bookmark Job
      .addCase(bookmarkJob.fulfilled, (state, action) => {
        const jobId = action.payload;
        
        // Update bookmark status in all relevant arrays
        [state.jobs, state.searchResults?.jobs || [], state.bookmarkedJobs].forEach(jobArray => {
          const job = jobArray.find(j => j.id === jobId);
          if (job) {
            job.isBookmarked = true;
          }
        });
        
        if (state.currentJob && state.currentJob.id === jobId) {
          state.currentJob.isBookmarked = true;
        }
      })
      .addCase(bookmarkJob.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Unbookmark Job
      .addCase(unbookmarkJob.fulfilled, (state, action) => {
        const jobId = action.payload;
        
        // Update bookmark status and remove from bookmarked jobs
        [state.jobs, state.searchResults?.jobs || []].forEach(jobArray => {
          const job = jobArray.find(j => j.id === jobId);
          if (job) {
            job.isBookmarked = false;
          }
        });
        
        state.bookmarkedJobs = state.bookmarkedJobs.filter(job => job.id !== jobId);
        
        if (state.currentJob && state.currentJob.id === jobId) {
          state.currentJob.isBookmarked = false;
        }
      })
      .addCase(unbookmarkJob.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Get Bookmarked Jobs
      .addCase(getBookmarkedJobs.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(getBookmarkedJobs.fulfilled, (state, action) => {
        state.isLoading = false;
        state.bookmarkedJobs = action.payload;
      })
      .addCase(getBookmarkedJobs.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Update Application Status
      .addCase(updateApplicationStatus.fulfilled, (state, action) => {
        const updatedJob = action.payload;
        
        // Update job in all relevant arrays
        [state.jobs, state.searchResults?.jobs || [], state.bookmarkedJobs].forEach(jobArray => {
          const jobIndex = jobArray.findIndex(j => j.id === updatedJob.id);
          if (jobIndex !== -1) {
            jobArray[jobIndex] = updatedJob;
          }
        });
        
        if (state.currentJob && state.currentJob.id === updatedJob.id) {
          state.currentJob = updatedJob;
        }
      })
      .addCase(updateApplicationStatus.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const {
  setSearchParams,
  clearSearchResults,
  clearCurrentJob,
  clearError,
  updateJobInList,
} = jobsSlice.actions;

export default jobsSlice.reducer;