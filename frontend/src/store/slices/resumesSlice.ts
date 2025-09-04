import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ResumesState, Resume } from '../../types';
import * as resumesService from '../../services/resumesService';

const initialState: ResumesState = {
  resumes: [],
  activeResume: null,
  isLoading: false,
  error: null,
  uploadProgress: 0,
};

// Async thunks
export const getResumes = createAsyncThunk(
  'resumes/getResumes',
  async (_, { rejectWithValue }) => {
    try {
      const resumes = await resumesService.getResumes();
      return resumes;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to get resumes');
    }
  }
);

export const getResumeById = createAsyncThunk(
  'resumes/getResumeById',
  async (resumeId: string, { rejectWithValue }) => {
    try {
      const resume = await resumesService.getResumeById(resumeId);
      return resume;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to get resume');
    }
  }
);

export const uploadResume = createAsyncThunk(
  'resumes/uploadResume',
  async (file: File, { rejectWithValue, dispatch }) => {
    try {
      const resume = await resumesService.uploadResume(file, (progress) => {
        dispatch(setUploadProgress(progress));
      });
      return resume;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Resume upload failed');
    }
  }
);

export const deleteResume = createAsyncThunk(
  'resumes/deleteResume',
  async (resumeId: string, { rejectWithValue }) => {
    try {
      await resumesService.deleteResume(resumeId);
      return resumeId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to delete resume');
    }
  }
);

export const setActiveResume = createAsyncThunk(
  'resumes/setActiveResume',
  async (resumeId: string, { rejectWithValue }) => {
    try {
      const resume = await resumesService.setActiveResume(resumeId);
      return resume;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to set active resume');
    }
  }
);

export const updateResume = createAsyncThunk(
  'resumes/updateResume',
  async ({ resumeId, data }: { resumeId: string; data: Partial<Resume> }, { rejectWithValue }) => {
    try {
      const resume = await resumesService.updateResume(resumeId, data);
      return resume;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update resume');
    }
  }
);

export const reprocessResume = createAsyncThunk(
  'resumes/reprocessResume',
  async (resumeId: string, { rejectWithValue }) => {
    try {
      const resume = await resumesService.reprocessResume(resumeId);
      return resume;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to reprocess resume');
    }
  }
);

const resumesSlice = createSlice({
  name: 'resumes',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setUploadProgress: (state, action: PayloadAction<number>) => {
      state.uploadProgress = action.payload;
    },
    resetUploadProgress: (state) => {
      state.uploadProgress = 0;
    },
    clearActiveResume: (state) => {
      state.activeResume = null;
    },
    updateResumeStatus: (state, action: PayloadAction<{ resumeId: string; status: Resume['status'] }>) => {
      const { resumeId, status } = action.payload;
      const resume = state.resumes.find(r => r.id === resumeId);
      if (resume) {
        resume.status = status;
      }
      if (state.activeResume && state.activeResume.id === resumeId) {
        state.activeResume.status = status;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Get Resumes
      .addCase(getResumes.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getResumes.fulfilled, (state, action) => {
        state.isLoading = false;
        state.resumes = action.payload;
        
        // Set active resume if one exists
        const activeResume = action.payload.find(resume => resume.isActive);
        if (activeResume) {
          state.activeResume = activeResume;
        }
      })
      .addCase(getResumes.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Get Resume By ID
      .addCase(getResumeById.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getResumeById.fulfilled, (state, action) => {
        state.isLoading = false;
        
        // Update the resume in the list if it exists
        const resumeIndex = state.resumes.findIndex(r => r.id === action.payload.id);
        if (resumeIndex !== -1) {
          state.resumes[resumeIndex] = action.payload;
        } else {
          state.resumes.push(action.payload);
        }
        
        // Set as active resume if it's marked active
        if (action.payload.isActive) {
          state.activeResume = action.payload;
        }
      })
      .addCase(getResumeById.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Upload Resume
      .addCase(uploadResume.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(uploadResume.fulfilled, (state, action) => {
        state.isLoading = false;
        state.resumes.push(action.payload);
        state.uploadProgress = 0;
        
        // Set as active if it's the first resume
        if (state.resumes.length === 1) {
          state.activeResume = action.payload;
        }
      })
      .addCase(uploadResume.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        state.uploadProgress = 0;
      })
      // Delete Resume
      .addCase(deleteResume.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(deleteResume.fulfilled, (state, action) => {
        state.isLoading = false;
        const resumeId = action.payload;
        state.resumes = state.resumes.filter(resume => resume.id !== resumeId);
        
        // Clear active resume if it was deleted
        if (state.activeResume && state.activeResume.id === resumeId) {
          state.activeResume = state.resumes.find(resume => resume.isActive) || null;
        }
      })
      .addCase(deleteResume.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Set Active Resume
      .addCase(setActiveResume.fulfilled, (state, action) => {
        // Update all resumes' active status
        state.resumes.forEach(resume => {
          resume.isActive = resume.id === action.payload.id;
        });
        
        state.activeResume = action.payload;
      })
      .addCase(setActiveResume.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Update Resume
      .addCase(updateResume.fulfilled, (state, action) => {
        const updatedResume = action.payload;
        const resumeIndex = state.resumes.findIndex(r => r.id === updatedResume.id);
        
        if (resumeIndex !== -1) {
          state.resumes[resumeIndex] = updatedResume;
        }
        
        if (state.activeResume && state.activeResume.id === updatedResume.id) {
          state.activeResume = updatedResume;
        }
      })
      .addCase(updateResume.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Reprocess Resume
      .addCase(reprocessResume.fulfilled, (state, action) => {
        const reprocessedResume = action.payload;
        const resumeIndex = state.resumes.findIndex(r => r.id === reprocessedResume.id);
        
        if (resumeIndex !== -1) {
          state.resumes[resumeIndex] = reprocessedResume;
        }
        
        if (state.activeResume && state.activeResume.id === reprocessedResume.id) {
          state.activeResume = reprocessedResume;
        }
      })
      .addCase(reprocessResume.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const {
  clearError,
  setUploadProgress,
  resetUploadProgress,
  clearActiveResume,
  updateResumeStatus,
} = resumesSlice.actions;

export default resumesSlice.reducer;