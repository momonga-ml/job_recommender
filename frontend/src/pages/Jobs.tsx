import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Search as SearchIcon,
  LocationOn as LocationIcon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { searchJobs, setSearchParams } from '../store/slices/jobsSlice';
import { JobSearchParams } from '../types';
import { useNavigate } from 'react-router-dom';

const Jobs: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { searchResults, isLoading, error, searchParams } = useSelector((state: RootState) => state.jobs);

  const [searchQuery, setSearchQuery] = useState(searchParams.query || '');
  const [locationQuery, setLocationQuery] = useState(searchParams.location || '');

  const handleSearch = () => {
    const params: JobSearchParams = {
      query: searchQuery || undefined,
      location: locationQuery || undefined,
      page: 1,
      limit: 20,
    };

    dispatch(setSearchParams(params));
    dispatch(searchJobs(params));
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Find Your Next Opportunity
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Discover jobs that match your skills and experience
        </Typography>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { xs: '1fr', md: '2fr 1fr 1fr' }, 
            gap: 2, 
            alignItems: 'center' 
          }}>
            <TextField
              fullWidth
              placeholder="Search jobs, companies, or keywords"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              InputProps={{
                startAdornment: <SearchIcon sx={{ color: 'text.secondary', mr: 1 }} />,
              }}
            />
            <TextField
              fullWidth
              placeholder="Location"
              value={locationQuery}
              onChange={(e) => setLocationQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              InputProps={{
                startAdornment: <LocationIcon sx={{ color: 'text.secondary', mr: 1 }} />,
              }}
            />
            <Button
              fullWidth
              variant="contained"
              onClick={handleSearch}
              disabled={isLoading}
              sx={{ height: 56 }}
            >
              {isLoading ? <CircularProgress size={24} color="inherit" /> : 'Search'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {searchResults && searchResults.jobs.length === 0 && (
        <Box textAlign="center" sx={{ py: 8 }}>
          <SearchIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No jobs found
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Try adjusting your search criteria or exploring different keywords.
          </Typography>
          <Button variant="contained" onClick={handleSearch}>
            Search Again
          </Button>
        </Box>
      )}

      {/* Job Results would go here */}
      {searchResults && searchResults.jobs.length > 0 && (
        <Box>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Found {searchResults.total} jobs
          </Typography>
          {/* Job cards would be rendered here */}
        </Box>
      )}
    </Container>
  );
};

export default Jobs;