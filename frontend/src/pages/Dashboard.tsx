import React, { useEffect } from 'react';
import {
  Box,
  Container,
  Card,
  CardContent,
  Typography,
  Button,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  LinearProgress,
  IconButton,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  Work as WorkIcon,
  BookmarkBorder as BookmarkIcon,
  Assessment as AssessmentIcon,
  CloudUpload as UploadIcon,
  Search as SearchIcon,
  Person as PersonIcon,
  Business as BusinessIcon,
  Schedule as ScheduleIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { getDashboardStats } from '../services/jobsService';
import { DashboardStats } from '../types';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);
  const { resumes, activeResume } = useSelector((state: RootState) => state.resumes);
  
  const [dashboardData, setDashboardData] = React.useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);
        const data = await getDashboardStats();
        setDashboardData(data);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        // Mock data for development
        setDashboardData({
          totalJobs: 1250,
          bookmarkedJobs: 15,
          applications: 8,
          analyses: 12,
          averageMatch: 78,
          topSkills: ['React', 'JavaScript', 'TypeScript', 'Node.js'],
          recentActivity: []
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const stats = [
    {
      title: 'Total Jobs',
      value: dashboardData?.totalJobs || 0,
      icon: <WorkIcon sx={{ fontSize: 40, color: 'primary.main' }} />,
      action: () => navigate('/jobs'),
    },
    {
      title: 'Bookmarked',
      value: dashboardData?.bookmarkedJobs || 0,
      icon: <BookmarkIcon sx={{ fontSize: 40, color: 'secondary.main' }} />,
      action: () => navigate('/jobs'),
    },
    {
      title: 'Applications',
      value: dashboardData?.applications || 0,
      icon: <BusinessIcon sx={{ fontSize: 40, color: 'success.main' }} />,
      action: () => navigate('/jobs'),
    },
    {
      title: 'Analyses',
      value: dashboardData?.analyses || 0,
      icon: <AssessmentIcon sx={{ fontSize: 40, color: 'info.main' }} />,
      action: () => navigate('/analysis'),
    },
  ];

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Welcome Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          {getGreeting()}, {user?.firstName || 'User'}!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here's what's happening with your job search today.
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(4, 1fr)' }, 
        gap: 3, 
        mb: 4 
      }}>
        {stats.map((stat, index) => (
          <Card
            key={index}
            sx={{
              cursor: 'pointer',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: 4,
              },
            }}
            onClick={stat.action}
          >
            <CardContent sx={{ display: 'flex', alignItems: 'center' }}>
              <Box sx={{ mr: 2 }}>{stat.icon}</Box>
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h4" fontWeight="bold" color="primary.main">
                  {isLoading ? '-' : stat.value}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {stat.title}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Main Content Grid */}
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, 
        gap: 3,
        mb: 3
      }}>
        {/* Quick Actions */}
        <Card sx={{ height: 'fit-content' }}>
          <CardContent>
            <Typography variant="h6" fontWeight="bold" sx={{ mb: 2 }}>
              Quick Actions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Button
                fullWidth
                variant="contained"
                startIcon={<SearchIcon />}
                onClick={() => navigate('/jobs')}
                sx={{ py: 1.5 }}
              >
                Search Jobs
              </Button>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<UploadIcon />}
                onClick={() => navigate('/resumes')}
                sx={{ py: 1.5 }}
              >
                Upload Resume
              </Button>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<AssessmentIcon />}
                onClick={() => navigate('/analysis')}
                disabled={!activeResume}
                sx={{ py: 1.5 }}
              >
                Analyze Jobs
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Profile Summary */}
        <Card sx={{ height: 'fit-content' }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
              <Typography variant="h6" fontWeight="bold">
                Your Profile
              </Typography>
              <IconButton size="small" onClick={() => window.location.reload()}>
                <RefreshIcon />
              </IconButton>
            </Box>
            
            {activeResume ? (
              <Box>
                <Box display="flex" alignItems="center" sx={{ mb: 2 }}>
                  <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                    {user?.firstName?.[0]}{user?.lastName?.[0]}
                  </Avatar>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="medium">
                      Active Resume: {activeResume.filename}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Uploaded {new Date(activeResume.uploadDate).toLocaleDateString()}
                    </Typography>
                  </Box>
                </Box>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    Average Match Score
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={dashboardData?.averageMatch || 0}
                    sx={{ height: 8, borderRadius: 4, mb: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {dashboardData?.averageMatch || 0}%
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Top Skills
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {(dashboardData?.topSkills || []).slice(0, 4).map((skill, index) => (
                      <Chip key={index} label={skill} size="small" />
                    ))}
                  </Box>
                </Box>
              </Box>
            ) : (
              <Box textAlign="center" sx={{ py: 3 }}>
                <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                <Typography variant="body1" color="text.secondary" gutterBottom>
                  No resume uploaded yet
                </Typography>
                <Button
                  variant="contained"
                  onClick={() => navigate('/resumes')}
                  startIcon={<UploadIcon />}
                >
                  Upload Resume
                </Button>
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* Recent Activity */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight="bold" sx={{ mb: 2 }}>
            Recent Activity
          </Typography>
          
          {dashboardData?.recentActivity && dashboardData.recentActivity.length > 0 ? (
            <List>
              {dashboardData.recentActivity.slice(0, 5).map((activity, index) => (
                <React.Fragment key={activity.id}>
                  <ListItem>
                    <ListItemIcon>
                      <PersonIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary={activity.title}
                      secondary={activity.description}
                    />
                  </ListItem>
                  {index < dashboardData.recentActivity.length - 1 && index < 4 && (
                    <Divider component="li" />
                  )}
                </React.Fragment>
              ))}
            </List>
          ) : (
            <Box textAlign="center" sx={{ py: 3 }}>
              <ScheduleIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="body1" color="text.secondary">
                No recent activity yet. Start by uploading a resume or searching for jobs!
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </Container>
  );
};

export default Dashboard;