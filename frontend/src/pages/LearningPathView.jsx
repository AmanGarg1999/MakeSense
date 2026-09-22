import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import LearningPathTree3D from '../components/LearningPathTree3D';

export default function LearningPathView() {
  const { pathId } = useParams();
  const navigate = useNavigate();
  const [path, setPath] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [viewMode, setViewMode] = useState('3d'); // '3d' or '2d'
  const [unlocking, setUnlocking] = useState(false);

  useEffect(() => {
    fetchPath();
  }, [pathId]);

  const fetchPath = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/paths/${pathId}`);
      if (!res.ok) throw new Error('Failed to load learning path');
      const data = await res.json();
      setPath(data);
      // Select first unlocked node by default
      const defaultNode = (data.nodes || []).find(n => n.status === 'unlocked') || data.nodes?.[0];
      setSelectedNode(defaultNode);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartMilestone = async (node) => {
    if (!node || node.status === 'locked') return;

    try {
      setUnlocking(true);
      // Ensure lesson is generated
      const res = await fetch(`/api/paths/${pathId}/nodes/${node.id}/unlock`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Failed to prepare lesson');
      const data = await res.json();
      
      // Navigate to lesson viewer, passing pathId & nodeId in state
      navigate(`/lesson/${data.lesson_id}`, {
        state: { pathId, nodeId: node.id, pathTitle: path.title }
      });
    } catch (err) {
      alert(`Could not open lesson: ${err.message}`);
    } finally {
      setUnlocking(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '5rem 1rem', color: 'var(--text-muted)' }}>
        <div className="spinner" style={{ margin: '0 auto 1.5rem', width: 32, height: 32, border: '3px solid #818cf8', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <h2>Consulting your AI Mentor...</h2>
        <p style={{ marginTop: '0.5rem' }}>Aligning your 3D Skill Tree and calculating progress.</p>
      </div>
    );
  }

  if (error || !path) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem' }}>
        <h2>Could not find learning path</h2>
        <p style={{ color: 'var(--error)', margin: '1rem 0' }}>{error || 'Path does not exist.'}</p>
        <Link to="/" className="btn-secondary">Return to Dashboard</Link>
      </div>
    );
  }

  const completedCount = (path.nodes || []).filter(n => n.status === 'completed').length;
  const totalCount = (path.nodes || []).length;

  return (
    <div className="learning-path-container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '1rem 1.5rem 4rem' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <Link to="/" style={{ color: 'var(--text-muted)', textDecoration: 'none', fontSize: '0.875rem', display: 'inline-flex', alignItems: 'center', gap: '4px', marginBottom: '6px' }}>
            &larr; Back to Dashboard
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>{path.title}</h1>
            <span style={{ background: '#4f46e5', color: '#fff', fontSize: '0.75rem', fontWeight: 700, padding: '3px 10px', borderRadius: '20px', textTransform: 'uppercase' }}>
              {path.category}
            </span>
          </div>
        </div>

        {/* View Mode & Progress */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {path.completion_rate === 100 && (
            <button 
              onClick={() => alert('Certificate of Completion! You have mastered this domain. (Certificate render coming in future update)')}
              style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '12px', fontWeight: 800, cursor: 'pointer', boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)' }}
            >
              🎓 Claim Certificate
            </button>
          )}

          <div style={{ background: 'var(--surface-card)', border: '1px solid var(--card-border)', borderRadius: '12px', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Progress:</span>
            <div style={{ width: '100px', height: '8px', background: 'var(--card-border)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${path.completion_rate}%`, height: '100%', background: 'linear-gradient(90deg, #10b981, #06b6d4)', transition: 'width 0.5s ease' }} />
            </div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#10b981' }}>{path.completion_rate}% ({completedCount}/{totalCount})</span>
          </div>

          <div style={{ display: 'flex', background: 'var(--card-border)', borderRadius: '8px', padding: '2px' }}>
            <button
              onClick={() => setViewMode('3d')}
              style={{
                border: 'none',
                background: viewMode === '3d' ? '#4f46e5' : 'transparent',
                color: viewMode === '3d' ? '#fff' : 'var(--text-muted)',
                padding: '6px 14px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem'
              }}
            >
              🌌 3D Orbit
            </button>
            <button
              onClick={() => setViewMode('2d')}
              style={{
                border: 'none',
                background: viewMode === '2d' ? '#4f46e5' : 'transparent',
                color: viewMode === '2d' ? '#fff' : 'var(--text-muted)',
                padding: '6px 14px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem'
              }}
            >
              📋 Roadmap
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Grid: Visualizer on Left/Center, Mentor Briefing on Right */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.8fr) minmax(320px, 1fr)', gap: '1.5rem', alignItems: 'start' }}>
        {/* Visualizer Container */}
        <div>
          {viewMode === '3d' ? (
            <LearningPathTree3D
              nodes={path.nodes || []}
              activeNodeId={selectedNode?.id}
              onSelectNode={(n) => setSelectedNode(n)}
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {(path.nodes || []).map((node, index) => {
                const isSelected = selectedNode?.id === node.id;
                const isCompleted = node.status === 'completed';
                const isUnlocked = node.status === 'unlocked';
                const isLocked = node.status === 'locked';

                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    style={{
                      background: isSelected ? 'var(--primary-light)' : 'var(--card-bg)',
                      border: isSelected ? '2px solid #4f46e5' : '1px solid var(--card-border)',
                      borderRadius: '12px',
                      padding: '1rem 1.25rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'all 0.2s ease',
                      opacity: isLocked ? 0.75 : 1
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontSize: '0.9rem',
                          background: isCompleted ? '#10b981' : (isUnlocked ? '#06b6d4' : '#64748b'),
                          color: '#fff'
                        }}
                      >
                        {isCompleted ? '✓' : (index + 1)}
                      </div>
                      <div>
                        <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)' }}>{node.title}</h4>
                        <p style={{ margin: '3px 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          ⏱️ {node.estimated_time_minutes} mins &bull; {node.difficulty}
                        </p>
                      </div>
                    </div>

                    <div>
                      {isCompleted && <span style={{ color: '#10b981', fontWeight: 700, fontSize: '0.85rem' }}>Completed</span>}
                      {isUnlocked && <span style={{ color: '#06b6d4', fontWeight: 700, fontSize: '0.85rem' }}>Active Milestone</span>}
                      {isLocked && <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>🔒 Locked</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Mentor Briefing Drawer */}
        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: '16px', padding: '1.5rem', boxShadow: 'var(--shadow-md)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingBottom: '1rem', borderBottom: '1px solid var(--card-border)', marginBottom: '1.25rem' }}>
            <span style={{ fontSize: '1.5rem', background: '#eef2ff', width: 42, height: 42, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🧠</span>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)' }}>AI Mentor Guidance</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Adaptive Curriculum Intelligence</span>
            </div>
          </div>

          {selectedNode ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    padding: '3px 8px',
                    borderRadius: '6px',
                    background: selectedNode.status === 'completed' ? '#ecfdf5' : (selectedNode.status === 'unlocked' ? '#e0f2fe' : '#f1f5f9'),
                    color: selectedNode.status === 'completed' ? '#10b981' : (selectedNode.status === 'unlocked' ? '#0284c7' : '#64748b')
                  }}
                >
                  {selectedNode.status === 'completed' ? '✅ Completed' : (selectedNode.status === 'unlocked' ? '⚡ Ready to Study' : '🔒 Locked')}
                </span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  ⏱️ {selectedNode.estimated_time_minutes} mins
                </span>
              </div>

              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.5rem 0' }}>
                {selectedNode.title}
              </h2>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: '0 0 1.25rem' }}>
                {selectedNode.description}
              </p>

              {/* Mentor Rationale */}
              <div style={{ background: '#f8fafc', borderLeft: '4px solid #4f46e5', padding: '12px', borderRadius: '4px 8px 8px 4px', marginBottom: '1.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#4f46e5', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
                  Why Your Mentor Curated This:
                </span>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#334155', lineHeight: 1.5 }}>
                  {selectedNode.mentor_rationale}
                </p>
              </div>

              {/* Action Button */}
              {selectedNode.status !== 'locked' ? (
                <button
                  onClick={() => handleStartMilestone(selectedNode)}
                  disabled={unlocking}
                  style={{
                    width: '100%',
                    padding: '12px',
                    borderRadius: '10px',
                    background: selectedNode.status === 'completed' ? '#10b981' : 'linear-gradient(135deg, #4f46e5, #7c3aed)',
                    color: '#fff',
                    border: 'none',
                    fontWeight: 700,
                    fontSize: '0.95rem',
                    cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(79, 70, 229, 0.25)',
                    transition: 'transform 0.1s'
                  }}
                >
                  {unlocking ? 'Synthesizing Lesson...' : (selectedNode.status === 'completed' ? 'Review Lesson & Quiz ↺' : 'Start Milestone Lesson &rarr;')}
                </button>
              ) : (
                <div style={{ textAlign: 'center', padding: '12px', background: '#f8fafc', borderRadius: '10px', border: '1px dashed #cbd5e1', color: '#94a3b8', fontSize: '0.85rem' }}>
                  🔒 Complete prerequisite milestone to unlock this branch.
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Click any node on the 3D Skill Tree to inspect milestone details and mentor reasoning.
            </p>
          )}

          {/* Mentor Notes Footer */}
          <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--card-border)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Overall Roadmap Strategy
            </span>
            <p style={{ fontSize: '0.8rem', color: '#475569', marginTop: '6px', lineHeight: 1.5 }}>
              {path.mentor_notes?.split('\n\n')[0] || path.mentor_notes}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
