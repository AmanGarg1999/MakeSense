import React, { useState } from 'react';
import { HashRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import LessonViewer from './pages/LessonViewer';
import QuizPage from './pages/QuizPage';
import LearningPathView from './pages/LearningPathView';
import ReviewDeck from './pages/ReviewDeck';
import TrackDashboard from './pages/TrackDashboard';
import TrackDetail from './pages/TrackDetail';
import MentorProfilingModal from './components/MentorProfilingModal';
import { getUserId, useApi } from './hooks/useApi';
import './index.css';

function StreakCounter() {
  const userId = getUserId();
  const { data: streakData } = useApi(`/api/streaks/${userId}`);

  if (!streakData) return null;

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      background: 'rgba(245, 158, 11, 0.1)',
      color: '#f59e0b',
      padding: '4px 12px',
      borderRadius: '20px',
      fontWeight: 700,
      fontSize: '0.9rem',
      marginLeft: '12px'
    }}>
      <span>🔥</span>
      <span>{streakData.current_streak}</span>
    </div>
  );
}

function CurateRedirect({ onOpenModal }) {
  const navigate = useNavigate();
  React.useEffect(() => {
    onOpenModal();
    navigate('/', { replace: true });
  }, [onOpenModal, navigate]);
  return null;
}

export default function App() {
  const [isMentorModalOpen, setIsMentorModalOpen] = useState(false);

  return (
    <HashRouter>
      <div className="app">
        <nav className="app-nav">
          <div className="nav-brand">
            <a href="/">
              <span style={{
                background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
                color: '#fff',
                width: 32,
                height: 32,
                borderRadius: 10,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1rem',
                marginRight: 6
              }}>🧠</span>
              <span>MakeSense</span>
            </a>
            <StreakCounter />
          </div>
          <div className="nav-links">
            <button
              onClick={() => setIsMentorModalOpen(true)}
              style={{
                background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
                color: '#fff',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 2px 8px rgba(79, 70, 229, 0.3)'
              }}
            >
              <span>🧠</span>
              <span>Curate 3D Path</span>
            </button>
            <NavLink to="/tracks" className={({ isActive }) => isActive ? 'active' : ''}>Tracks</NavLink>
            <a href="/">Submit</a>
            <a href="/library.html">Library</a>
            <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>Dashboard</NavLink>
            <a href="/admin-dashboard.html">Admin</a>
          </div>
        </nav>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard onOpenCurate={() => setIsMentorModalOpen(true)} />} />
            <Route path="/curate" element={<CurateRedirect onOpenModal={() => setIsMentorModalOpen(true)} />} />
            <Route path="/path/:pathId" element={<LearningPathView />} />
            <Route path="/lesson/:lessonId" element={<LessonViewer />} />
            <Route path="/quiz/:lessonId" element={<QuizPage />} />
            <Route path="/reviews" element={<ReviewDeck />} />
            <Route path="/tracks" element={<TrackDashboard />} />
            <Route path="/tracks/:trackId" element={<TrackDetail />} />
          </Routes>
        </main>

        <MentorProfilingModal
          isOpen={isMentorModalOpen}
          onClose={() => setIsMentorModalOpen(false)}
        />
      </div>
    </HashRouter>
  );
}
