import React from 'react';
import { Link } from 'react-router-dom';
import LevelBadge from '../components/LevelBadge';
import XPProgressBar from '../components/XPProgressBar';
import SkillTagsCloud from '../components/SkillTagsCloud';
import PointsHistoryChart from '../components/PointsHistoryChart';
import { getUserId, useApi } from '../hooks/useApi';

export default function Dashboard({ onOpenCurate }) {
  const userId = getUserId();
  const [notifyStatus, setNotifyStatus] = React.useState(Notification.permission);
  
  const enableNotifications = async () => {
    const perm = await Notification.requestPermission();
    setNotifyStatus(perm);
    if (perm === 'granted') {
      new Notification("MakeSense Mentor", {
        body: "I'll remind you when your memory reviews are due!",
        icon: "/icon-192x192.png"
      });
    }
  };

  const { data: profile, loading: profileLoading } = useApi(`/api/users/${userId}/profile`);
  const currentTier = profile?.current_level || 1;
  const { data: skills } = useApi(`/api/users/${userId}/skills`);
  const { data: pointsHistory } = useApi(`/api/users/${userId}/points?limit=30`);
  const { data: leaderboard } = useApi(`/api/leaderboard?period=week&tier=${currentTier}`);
  const { data: pathsData } = useApi(`/api/paths?user_id=${userId}`);
  const { data: achievements } = useApi(`/api/achievements/${userId}`);
  const { data: dueReviews } = useApi(`/api/reviews/${userId}/due`);

  if (profileLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
        <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>Loading your learning dashboard...</p>
      </div>
    );
  }

  const safeProfile = profile || {
    level_name: 'Novice',
    current_level: 1,
    total_xp: 0,
    xp_to_next_level: 100,
    current_level_xp: 0,
    points_breakdown: {}
  };

  const activePaths = pathsData || [];

  return (
    <div className="dashboard-container">
      <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>Your Learning Dashboard</h1>
          <p>Track your Bayesian skill growth, XP milestones, and community leaderboard standing.</p>
        </div>
        {onOpenCurate && (
          <button
            onClick={onOpenCurate}
            style={{
              background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
              color: '#fff',
              border: 'none',
              padding: '10px 18px',
              borderRadius: '10px',
              fontWeight: 700,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 12px rgba(79, 70, 229, 0.25)'
            }}
          >
            <span>🧠</span>
            <span>+ Curate Adaptive Path</span>
          </button>
        )}
      </div>

      {/* Sprint 2: Micro-Challenge Feed & Reviews */}
      <div style={{ marginBottom: '2.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 800, margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>⚡</span>
          <span>Daily Challenges</span>
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          
          {/* Spaced Repetition Challenge */}
          <div style={{ background: 'linear-gradient(135deg, #eff6ff, #dbeafe)', border: '1px solid #bfdbfe', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#2563eb', textTransform: 'uppercase', marginBottom: '4px' }}>Active Recall</div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#1e3a8a', fontWeight: 800 }}>Daily Review Deck</h3>
              </div>
              <div style={{ background: '#3b82f6', color: '#fff', fontWeight: 800, padding: '4px 10px', borderRadius: '12px', fontSize: '0.9rem' }}>
                {dueReviews ? dueReviews.length : 0} Due
              </div>
            </div>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#3b82f6', opacity: 0.9 }}>
              Solidify your memory. Uses the SM-2 algorithm to surface concepts right before you forget them.
            </p>
            <Link 
              to="/reviews" 
              style={{ display: 'block', textAlign: 'center', background: '#2563eb', color: '#fff', textDecoration: 'none', padding: '10px', borderRadius: '10px', fontWeight: 700, opacity: (!dueReviews || dueReviews.length === 0) ? 0.5 : 1, pointerEvents: (!dueReviews || dueReviews.length === 0) ? 'none' : 'auto' }}
            >
              Start Review Session &rarr;
            </Link>
          </div>

          {/* Learn Something New Challenge */}
          <div style={{ background: 'linear-gradient(135deg, #f0fdf4, #dcfce7)', border: '1px solid #bbf7d0', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', marginBottom: '4px' }}>Discovery</div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#14532d', fontWeight: 800 }}>Complete a Milestone</h3>
              </div>
              <div style={{ background: '#22c55e', color: '#fff', fontWeight: 800, padding: '4px 10px', borderRadius: '12px', fontSize: '0.9rem' }}>
                +25 XP
              </div>
            </div>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#16a34a', opacity: 0.9 }}>
              Jump into one of your active skill trees and conquer a new topic today to build your streak.
            </p>
            <button 
              onClick={() => document.getElementById('skill-trees').scrollIntoView({ behavior: 'smooth' })}
              style={{ display: 'block', width: '100%', border: 'none', cursor: 'pointer', textAlign: 'center', background: '#16a34a', color: '#fff', textDecoration: 'none', padding: '10px', borderRadius: '10px', fontWeight: 700 }}
            >
              Explore Paths &darr;
            </button>
          </div>

          {/* Notification Challenge */}
          {notifyStatus !== 'granted' && (
            <div style={{ background: 'linear-gradient(135deg, #fef2f2, #fee2e2)', border: '1px solid #fecaca', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#dc2626', textTransform: 'uppercase', marginBottom: '4px' }}>Habit Building</div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#991b1b', fontWeight: 800 }}>Enable Mentorship</h3>
                </div>
                <div style={{ background: '#ef4444', color: '#fff', fontWeight: 800, padding: '4px 10px', borderRadius: '12px', fontSize: '0.9rem' }}>
                  +50 XP
                </div>
              </div>
              <p style={{ margin: 0, fontSize: '0.9rem', color: '#dc2626', opacity: 0.9 }}>
                Allow your AI Mentor to notify you when you have active recall items due, so you never break your streak.
              </p>
              <button 
                onClick={enableNotifications}
                style={{ display: 'block', width: '100%', border: 'none', cursor: 'pointer', textAlign: 'center', background: '#dc2626', color: '#fff', textDecoration: 'none', padding: '10px', borderRadius: '10px', fontWeight: 700 }}
              >
                Enable Notifications 🔔
              </button>
            </div>
          )}

        </div>
      </div>

      {/* Active AI Mentor Paths */}
      <div id="skill-trees" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🌌</span>
            <span>Active 3D Skill Trees</span>
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Adaptive DAG Curriculums
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
          {activePaths.map((p) => (
            <Link
              key={p.id}
              to={`/path/${p.id}`}
              style={{
                textDecoration: 'none',
                color: 'inherit',
                background: 'var(--card-bg, #ffffff)',
                border: '1px solid var(--card-border)',
                borderRadius: '14px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'transform 0.2s, box-shadow 0.2s',
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ background: '#eef2ff', color: '#4f46e5', fontSize: '0.75rem', fontWeight: 700, padding: '2px 8px', borderRadius: '12px', textTransform: 'uppercase' }}>
                    {p.category}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {p.completed_node_count || 0} / {p.node_count || 0} Milestones
                  </span>
                </div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: '0 0 6px', color: 'var(--text-main)' }}>
                  {p.title}
                </h3>
              </div>

              <div style={{ marginTop: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                  <span>Mastery</span>
                  <span style={{ color: '#10b981' }}>{p.completion_rate}%</span>
                </div>
                <div style={{ height: '6px', background: 'var(--card-border)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${p.completion_rate}%`, height: '100%', background: 'linear-gradient(90deg, #10b981, #06b6d4)' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
                  <span style={{ color: '#4f46e5', fontSize: '0.85rem', fontWeight: 700 }}>
                    Enter 3D Orbit &rarr;
                  </span>
                </div>
              </div>
            </Link>
          ))}

          {activePaths.length === 0 && (
            <div style={{ gridColumn: '1 / -1', background: 'var(--card-bg)', border: '1px dashed var(--card-border)', borderRadius: '14px', padding: '2rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🌱</div>
              <h3 style={{ margin: '0 0 0.5rem', fontWeight: 700 }}>No Active Learning Trees Yet</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', maxWidth: '480px', margin: '0 auto 1.25rem' }}>
                Tell our AI Mentor what you'd like to learn, your background, and goals. It will curate an interactive 3D skill tree tailored exclusively to you.
              </p>
              {onOpenCurate && (
                <button
                  onClick={onOpenCurate}
                  style={{
                    background: '#4f46e5',
                    color: '#fff',
                    border: 'none',
                    padding: '8px 18px',
                    borderRadius: '8px',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  Start AI Mentor Diagnostic &rarr;
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Level */}
        <div className="card card-level">
          <h2>📊 Mastery Tier</h2>
          <LevelBadge
            levelName={safeProfile.level_name}
            currentLevel={safeProfile.current_level}
          />
        </div>

        {/* XP Progress */}
        <div className="card card-xp">
          <h2>⚡ XP Momentum</h2>
          <XPProgressBar
            currentXp={safeProfile.current_level_xp || safeProfile.total_xp}
            xpToNextLevel={safeProfile.xp_to_next_level}
          />
        </div>

        {/* Points Breakdown */}
        <div className="card card-breakdown">
          <h2>💰 Earned Points</h2>
          <div className="points-breakdown">
            {Object.entries(safeProfile.points_breakdown || {}).map(([source, pts]) => (
              <div key={source} className="breakdown-item">
                <span className="source-label">{source.replace(/_/g, ' ')}</span>
                <span className="source-points">+{pts} pts</span>
              </div>
            ))}
            {Object.keys(safeProfile.points_breakdown || {}).length === 0 && (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Complete lessons and quizzes to earn points!</p>
            )}
          </div>
        </div>

        {/* Skills */}
        <div className="card card-skills">
          <h2>🎯 Skill Heatmap</h2>
          <SkillTagsCloud skills={skills || []} />
        </div>

        {/* Points History Chart */}
        <div className="card card-chart">
          <h2>📈 Engagement Trajectory</h2>
          <PointsHistoryChart data={pointsHistory || []} />
        </div>

        {/* Leaderboard */}
        <div className="card card-leaderboard">
          <h2>🏆 Weekly League Standings (Tier {currentTier})</h2>
          <table className="leaderboard-table">
            <thead>
              <tr>
                <th style={{ width: 80 }}>Rank</th>
                <th>Learner</th>
                <th>Mastery Level</th>
                <th style={{ textAlign: 'right' }}>Total Points</th>
              </tr>
            </thead>
            <tbody>
              {(leaderboard || []).map((entry, i) => {
                const rankNum = entry.rank || i + 1;
                const isCurrentUser = entry.user_id == userId;
                let medal = rankNum === 1 ? '🥇' : rankNum === 2 ? '🥈' : rankNum === 3 ? '🥉' : `#${rankNum}`;

                return (
                  <tr key={i} className={isCurrentUser ? 'current-user' : ''}>
                    <td>
                      <span className={`rank-badge ${rankNum <= 3 ? `rank-${rankNum}` : ''}`}>{medal}</span>
                    </td>
                    <td>
                      <strong>{entry.user_name || 'Learner'}</strong>
                      {isCurrentUser && <span style={{ marginLeft: 8, fontSize: '0.75rem', background: 'var(--primary)', color: '#fff', padding: '2px 6px', borderRadius: 4 }}>You</span>}
                    </td>
                    <td>Level {entry.current_level || 1} &bull; {entry.level_name || 'Novice'}</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>{entry.points || 0} pts</td>
                  </tr>
                );
              })}
              {(!leaderboard || leaderboard.length === 0) && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No leaderboard activity recorded yet. Be the first to score!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {/* Achievements Showcase */}
        <div className="card card-achievements" style={{ gridColumn: '1 / -1' }}>
          <h2>🌟 Earned Achievements</h2>
          {achievements && achievements.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
              {achievements.filter(a => a.earned_at).map(ach => (
                <div key={ach.id} style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'linear-gradient(135deg, #f8fafc, #f1f5f9)', padding: '12px 16px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '2rem', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))' }}>{ach.icon}</div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#1e293b' }}>{ach.name}</div>
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{ach.description}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
              Complete lessons and build your streak to unlock achievements!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
