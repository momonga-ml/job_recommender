import React, { useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as FileIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Schedule as ProcessingIcon,
  Star as StarIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import {
  getResumes,
  uploadResume,
  setActiveResume,
  clearError,
} from '../store/slices/resumesSlice';
import { Resume } from '../types';

const Resumes: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { resumes, isLoading, error } = useSelector((state: RootState) => state.resumes);
  const [uploading, setUploading] = React.useState(false);

  useEffect(() => {
    dispatch(getResumes());
  }, [dispatch]);

  const onDrop = React.useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (file) {
        setUploading(true);
        try {
          await dispatch(uploadResume(file)).unwrap();
        } catch (error) {
          console.error('Upload failed:', error);
        } finally {
          setUploading(false);
        }
      }
    },
    [dispatch]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    multiple: false,
  });

  const getStatusIcon = (status: Resume['status']) => {
    switch (status) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'processing':
        return <ProcessingIcon color="info" />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <ProcessingIcon />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Resume Management
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload and manage your resumes for job matching and analysis
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => dispatch(clearError())} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box
            {...getRootProps()}
            sx={{
              border: 2,
              borderColor: isDragActive ? 'primary.main' : 'grey.300',
              borderStyle: 'dashed',
              borderRadius: 2,
              p: 4,
              textAlign: 'center',
              bgcolor: isDragActive ? 'primary.light' : 'grey.50',
              cursor: 'pointer',
              transition: 'all 0.2s ease-in-out',
            }}
          >
            <input {...getInputProps()} disabled={uploading} />
            {uploading ? (
              <Box>
                <CircularProgress sx={{ mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Uploading Resume...
                </Typography>
              </Box>
            ) : (
              <Box>
                <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  {isDragActive ? 'Drop your resume here' : 'Upload your resume'}
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Drag and drop your resume file here, or click to select
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Supported formats: PDF, DOC, DOCX, TXT
                </Typography>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      {isLoading && resumes.length === 0 ? (
        <Box textAlign="center" sx={{ py: 4 }}>
          <CircularProgress />
          <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
            Loading resumes...
          </Typography>
        </Box>
      ) : (
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr', lg: '1fr 1fr 1fr' }, 
          gap: 3 
        }}>
          {resumes.map((resume) => (
            <Card key={resume.id} sx={{ height: 'fit-content', position: 'relative' }}>
              {resume.isActive && (
                <Box sx={{ position: 'absolute', top: 8, left: 8, zIndex: 1 }}>
                  <Chip icon={<StarIcon />} label="Active" size="small" color="primary" />
                </Box>
              )}
              <CardContent sx={{ pt: resume.isActive ? 5 : 2 }}>
                <Box display="flex" alignItems="center" sx={{ mb: 2 }}>
                  <FileIcon sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
                  <Box>
                    <Typography variant="h6" fontWeight="bold">
                      {resume.originalName}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {formatFileSize(resume.size)}
                    </Typography>
                  </Box>
                </Box>
                <Box display="flex" alignItems="center" gap={1} sx={{ mb: 2 }}>
                  {getStatusIcon(resume.status)}
                  <Chip label={resume.status} size="small" variant="outlined" />
                </Box>
              </CardContent>
              <CardActions>
                <Button
                  size="small"
                  disabled={resume.isActive}
                  onClick={() => dispatch(setActiveResume(resume.id))}
                >
                  {resume.isActive ? 'Active' : 'Set Active'}
                </Button>
              </CardActions>
            </Card>
          ))}
        </Box>
      )}

      {!isLoading && resumes.length === 0 && (
        <Box textAlign="center" sx={{ py: 8 }}>
          <FileIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No resumes uploaded yet
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Upload your first resume to get started with job matching and analysis.
          </Typography>
        </Box>
      )}
    </Container>
  );
};

export default Resumes;