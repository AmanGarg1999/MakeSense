import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const TrackDashboard = () => {
  const navigate = useNavigate();
  const [tracks, setTracks] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [activeTab, setActiveTab] = useState('active');
  const [newTrack, setNewTrack] = useState({
    skill_graph_ref: '',
    skill_tag: '',
    goal_level: 'novice',
    goal_type: 'hobby'
  });
  const [availableLadders, setAvailableLadders] = useState([]);
  const [creating, setCreating] = useState(false);

  const API_BASE = '/api/tracks';

  const fetchTracks = async () => {
    try {
      const res = await fetch(`${API_BASE}/dashboard`, {
        headers: { 'X-User-ID': '1' }
      });
      const data = await res.json();
      setTracks(data.tracks || []);
      setSuggestions(data.pacing_suggestions || []);
    } catch (err) {
      console.error('Failed to fetch tracks:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableLadders = async () => {
    try {
      const res = await fetch(`${API_BASE}/ladders/available`, {
        headers: { 'X-User-ID': '1' }
      });
      const data = await res.json();
      setAvailableLadders(data);
    } catch (err) {
      console.error('Failed to fetch ladders:', err);
    }
  };

  useEffect(() => {
    fetchTracks();
    fetchAvailableLadders();
  }, []);

  const handleCreateTrack = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const res = await fetch(API_BASE, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': '1'
        },
        body: JSON.stringify(newTrack)
      });
      if (!res.ok) throw new Error('Failed to create track');
      setShowCreateModal(false);
      setNewTrack({ skill_graph_ref: '', skill_tag: '', goal_level: 'novice', goal_type: 'hobby' });
      fetchTracks();
    } catch (err) {
      alert(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleTrackAction = async (trackId, action) => {
    try {
      if (action === 'pause' || action === 'resume' || action === 'archive') {
        const statusMap = { pause: 'paused', resume: 'active', archive: 'archived' };
        await fetch(`${API_BASE}/${trackId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-User-ID': '1'
          },
          body: JSON.stringify({ status: statusMap[action] })
        });
      }
      fetchTracks();
    } catch (err) {
      console.error('Track action failed:', err);
    }
  };

  const handleSuggestionAction = async (suggestionId, action) => {
    try {
      await fetch(`${API_BASE}/pacing/${suggestionId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': '1'
        },
        body: JSON.stringify({ action })
      });
      setSuggestions(suggestions.filter(s => s.id !== suggestionId));
    } catch (err) {
      console.error('Suggestion action failed:', err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#4CAF50';
      case 'paused': return '#FF9800';
      case 'done': return '#2196F3';
      case 'archived': return '#9E9E9E';
      default: return '#757575';
    }
  };

  const getGoalTypeLabel = (type) => {
    const labels = { hobby: '🎯 Hobby', 'job-ready': '💼 Job-Ready', expert: '🏆 Expert' };
    return labels[type] || type;
  };

  const getLevelName = (rung) => {
    const names = ['Novice', 'Competent', 'Proficient', 'Expert'];
    return names[rung] || `Level ${rung}`;
  };

  const filteredTracks = tracks.filter(t => {
    if (activeTab === 'active') return t.status === 'active';
    if (activeTab === 'paused') return t.status === 'paused';
    if (activeTab === 'done') return t.status === 'done';
    return true;
  });

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>Loading your learning tracks...</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>Learning Tracks Dashboard</h1>
        <button style={styles.createBtn} onClick={() => { setShowCreateModal(true); fetchAvailableLadders(); }}>
          + Start New Track
        </button>
      </div>

      {/* Pacing Suggestions */}
      {suggestions.length > 0 && (
        <div style={styles.suggestionsSection}>
          <h3 style={styles.sectionTitle}>🧭 Companion Suggestions</h3>
          <div style={styles.suggestionsGrid}>
            {suggestions.map(s => (
              <div key={s.id} style={{...styles.suggestionCard, borderLeft: `4px solid ${s.confidence > 0.7 ? '#4CAF50' : '#FF9800'}`}}>
                <div style={styles.suggestionHeader}>
                  <span style={{...styles.suggestionType, backgroundColor: s.confidence > 0.7 ? '#E8F5E9' : '#FFF3E0'}}>
                    {s.suggestion_type.replace('_', ' ').toUpperCase()}
                  </span>
                  <span style={styles.confidence}>{Math.round(s.confidence * 100)}% confidence</span>
                </div>
                <p style={styles.suggestionText}>{s.rationale}</p>
                <div style={styles.suggestionActions}>
                  <button style={styles.acceptBtn} onClick={() => handleSuggestionAction(s.id, 'accept')}>
                    Accept
                  </button>
                  <button style={styles.dismissBtn} onClick={() => handleSuggestionAction(s.id, 'dismiss')}>
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Track Tabs */}
      <div style={styles.tabs}>
        {['all', 'active', 'paused', 'done'].map(tab => (
          <button
            key={tab}
            style={{...styles.tab, ...(activeTab === tab ? styles.activeTab : {})}}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)} {tab !== 'all' && `(${tracks.filter(t => t.status === tab).length})`}
          </button>
        ))}
      </div>

      {/* Tracks Grid */}
      <div style={styles.tracksGrid}>
        {filteredTracks.length === 0 ? (
          <div style={styles.emptyState}>
            {activeTab === 'all' ? (
              <>
                <div style={styles.emptyIcon}>📚</div>
                <p>No learning tracks yet. Start your first skill journey!</p>
                <button style={styles.createBtn} onClick={() => { setShowCreateModal(true); fetchAvailableLadders(); }}>
                  Create Your First Track
                </button>
              </>
            ) : (
              <p>No {activeTab} tracks. Check other tabs or create a new track.</p>
            )}
          </div>
        ) : (
          filteredTracks.map(track => (
            <div key={track.id} style={styles.trackCard}>
              <div style={{...styles.trackHeader, backgroundColor: getStatusColor(track.status)}}>
                <div>
                  <h3 style={styles.trackTitle}>{track.skill_tag}</h3>
                  <span style={styles.trackMeta}>{getGoalTypeLabel(track.goal_type)} • {getLevelName(track.current_ladder_rung)}</span>
                </div>
                <span style={{...styles.statusBadge, backgroundColor: 'rgba(255,255,255,0.2)'}}>
                  {track.status.toUpperCase()}
                </span>
              </div>

              <div style={styles.trackBody}>
                {/* Progress Ring */}
                <div style={styles.progressContainer}>
                  <svg style={styles.progressSvg} viewBox="0 0 100 100">
                    <circle
                      cx="50" cy="50" r="45"
                      stroke="#E0E0E0" strokeWidth="8" fill="none"
                    />
                    <circle
                      cx="50" cy="50" r="45"
                      stroke={getStatusColor(track.status)}
                      strokeWidth="8"
                      fill="none"
                      strokeDasharray={`${track.progress_pct * 2.83} 283`}
                      strokeDashoffset="283"
                      strokeLinecap="round"
                      style={styles.progressCircle}
                    />
                  </svg>
                  <div style={styles.progressText}>
                    <span style={styles.progressValue}>{track.progress_pct.toFixed(0)}%</span>
                    <span style={styles.progressLabel}>Complete</span>
                  </div>
                </div>

                {/* Current Rung Skills */}
                {track.current_rung && (
                  <div style={styles.rungSection}>
                    <h4 style={styles.rungTitle}>Current: {track.current_rung.level_name}</h4>
                    <div style={styles.skillsList}>
                      {track.current_rung.sub_skills?.slice(0, 3).map((skill, i) => (
                        <div key={i} style={styles.skillItem}>
                          <span style={styles.skillName}>{skill.name}</span>
                          <div style={styles.skillCanDo}>
                            {skill.can_do_statements?.slice(0, 1).map((stmt, j) => (
                              <span key={j} style={styles.canDoTag}>✓ {stmt}</span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Next Rung Preview */}
                {track.next_rung && (
                  <div style={styles.nextRung}>
                    <span style={styles.nextRungLabel}>Next: {track.next_rung.level_name}</span>
                    <span style={styles.nextRungSkills}>
                      {track.next_rung.sub_skills?.slice(0, 2).map(s => s.name).join(', ')}
                    </span>
                  </div>
                )}

                {/* Coach Narrative */}
                {track.coach_narrative && (
                  <div style={styles.coachNote}>
                    💬 {track.coach_narrative}
                  </div>
                )}

                {/* Actions */}
                <div style={styles.trackActions}>
                  {track.status === 'active' && (
                    <>
                      <button style={styles.actionBtn} onClick={() => navigate(`/tracks/${track.id}`)}>
                        Continue Learning
                      </button>
                      <button style={{...styles.actionBtn, ...styles.secondaryBtn}} onClick={() => handleTrackAction(track.id, 'pause')}>
                        Pause
                      </button>
                    </>
                  )}
                  {track.status === 'paused' && (
                    <button style={styles.actionBtn} onClick={() => handleTrackAction(track.id, 'resume')}>
                      Resume
                    </button>
                  )}
                  {track.status === 'done' && (
                    <button style={{...styles.actionBtn, ...styles.secondaryBtn}} onClick={() => handleTrackAction(track.id, 'archive')}>
                      Archive
                    </button>
                  )}
                  <button style={{...styles.actionBtn, ...styles.ghostBtn}} onClick={() => navigate(`/tracks/${track.id}`)}>
                    Details
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Track Modal */}
      {showCreateModal && (
        <div style={styles.modalOverlay} onClick={() => setShowCreateModal(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <h2 style={styles.modalTitle}>Start a New Skill Track</h2>
            <form onSubmit={handleCreateTrack} style={styles.form}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Skill / Topic</label>
                <select
                  style={styles.select}
                  value={newTrack.skill_tag}
                  onChange={e => setNewTrack({...newTrack, skill_tag: e.target.value})}
                  required
                >
                  <option value="">Select a skill...</option>
                  {availableLadders.map(ladder => (
                    <option key={`${ladder.skill_tag}-${ladder.goal_type}`} value={ladder.skill_tag}>
                      {ladder.skill_tag} ({ladder.goal_type}, {ladder.rung_count} levels, ~{ladder.total_xp} XP)
                    </option>
                  ))}
                </select>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Skill Graph Reference</label>
                <input
                  style={styles.input}
                  type="text"
                  value={newTrack.skill_graph_ref}
                  onChange={e => setNewTrack({...newTrack, skill_graph_ref: e.target.value})}
                  placeholder="e.g., competency_kg:personal_finance"
                  required
                />
              </div>

              <div style={styles.formRow}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Goal Level</label>
                  <select
                    style={styles.select}
                    value={newTrack.goal_level}
                    onChange={e => setNewTrack({...newTrack, goal_level: e.target.value})}
                  >
                    <option value="novice">Novice</option>
                    <option value="competent">Competent</option>
                    <option value="proficient">Proficient</option>
                    <option value="expert">Expert</option>
                  </select>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>Goal Type</label>
                  <select
                    style={styles.select}
                    value={newTrack.goal_type}
                    onChange={e => setNewTrack({...newTrack, goal_type: e.target.value})}
                  >
                    <option value="hobby">🎯 Hobby</option>
                    <option value="job-ready">💼 Job-Ready</option>
                    <option value="expert">🏆 Expert</option>
                  </select>
                </div>
              </div>

              <div style={styles.modalActions}>
                <button type="button" style={styles.cancelBtn} onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" style={styles.createBtn} disabled={creating}>
                  {creating ? 'Creating...' : 'Create Track'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '24px',
    maxWidth: '1200px',
    margin: '0 auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  loading: {
    textAlign: 'center',
    padding: '60px',
    fontSize: '18px',
    color: '#666'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px'
  },
  title: {
    margin: 0,
    fontSize: '28px',
    fontWeight: '600',
    color: '#1a1a1a'
  },
  createBtn: {
    background: '#1976D2',
    color: 'white',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background 0.2s'
  },
  suggestionsSection: {
    marginBottom: '24px'
  },
  sectionTitle: {
    margin: '0 0 16px 0',
    fontSize: '18px',
    fontWeight: '600',
    color: '#333'
  },
  suggestionsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '12px'
  },
  suggestionCard: {
    background: '#fff',
    border: '1px solid #E0E0E0',
    borderRadius: '12px',
    padding: '16px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
  },
  suggestionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px'
  },
  suggestionType: {
    fontSize: '11px',
    fontWeight: '600',
    padding: '4px 8px',
    borderRadius: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  confidence: {
    fontSize: '12px',
    color: '#666',
    fontWeight: '500'
  },
  suggestionText: {
    margin: '0 0 12px 0',
    fontSize: '14px',
    color: '#444',
    lineHeight: '1.5'
  },
  suggestionActions: {
    display: 'flex',
    gap: '8px'
  },
  acceptBtn: {
    background: '#4CAF50',
    color: 'white',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  dismissBtn: {
    background: '#fff',
    color: '#666',
    border: '1px solid #E0E0E0',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  tabs: {
    display: 'flex',
    gap: '8px',
    marginBottom: '24px',
    borderBottom: '1px solid #E0E0E0',
    paddingBottom: '8px'
  },
  tab: {
    background: 'none',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#666',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  activeTab: {
    background: '#E3F2FD',
    color: '#1976D2'
  },
  tracksGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
    gap: '20px'
  },
  emptyState: {
    gridColumn: '1 / -1',
    textAlign: 'center',
    padding: '60px 20px',
    color: '#999'
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '16px'
  },
  trackCard: {
    background: '#fff',
    border: '1px solid #E0E0E0',
    borderRadius: '16px',
    overflow: 'hidden',
    boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
    transition: 'transform 0.2s, box-shadow 0.2s'
  },
  trackHeader: {
    color: 'white',
    padding: '16px 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start'
  },
  trackTitle: {
    margin: '0 0 4px 0',
    fontSize: '18px',
    fontWeight: '600'
  },
  trackMeta: {
    fontSize: '13px',
    opacity: 0.9
  },
  statusBadge: {
    padding: '4px 10px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  trackBody: {
    padding: '20px'
  },
  progressContainer: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: '20px'
  },
  progressSvg: {
    width: '100px',
    height: '100px',
    transform: 'rotate(-90deg)'
  },
  progressCircle: {
    transition: 'stroke-dashoffset 0.5s ease-out'
  },
  progressText: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    textAlign: 'center',
    pointerEvents: 'none'
  },
  progressValue: {
    display: 'block',
    fontSize: '24px',
    fontWeight: '700',
    color: '#1a1a1a'
  },
  progressLabel: {
    display: 'block',
    fontSize: '11px',
    color: '#999',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  rungSection: {
    marginBottom: '16px'
  },
  rungTitle: {
    margin: '0 0 12px 0',
    fontSize: '14px',
    fontWeight: '600',
    color: '#333'
  },
  skillsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  skillItem: {
    padding: '10px 12px',
    background: '#F5F5F5',
    borderRadius: '8px'
  },
  skillName: {
    display: 'block',
    fontSize: '13px',
    fontWeight: '500',
    color: '#333',
    marginBottom: '4px'
  },
  skillCanDo: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px'
  },
  canDoTag: {
    fontSize: '11px',
    color: '#4CAF50',
    background: '#E8F5E9',
    padding: '2px 8px',
    borderRadius: '4px'
  },
  nextRung: {
    padding: '12px',
    background: '#E3F2FD',
    borderRadius: '8px',
    marginBottom: '16px'
  },
  nextRungLabel: {
    display: 'block',
    fontSize: '13px',
    fontWeight: '600',
    color: '#1976D2',
    marginBottom: '4px'
  },
  nextRungSkills: {
    fontSize: '12px',
    color: '#1565C0'
  },
  coachNote: {
    padding: '12px',
    background: '#FFF8E1',
    borderRadius: '8px',
    fontSize: '13px',
    color: '#F57F17',
    lineHeight: '1.5',
    marginBottom: '16px',
    fontStyle: 'italic'
  },
  trackActions: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap'
  },
  actionBtn: {
    flex: 1,
    minWidth: '120px',
    padding: '10px 16px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
    border: 'none',
    transition: 'all 0.2s'
  },
  secondaryBtn: {
    background: '#E0E0E0',
    color: '#333'
  },
  ghostBtn: {
    background: 'transparent',
    color: '#1976D2',
    border: '1px solid #1976D2'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0,0,0,0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px'
  },
  modal: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    width: '100%',
    maxWidth: '500px',
    maxHeight: '90vh',
    overflow: 'auto'
  },
  modalTitle: {
    margin: '0 0 24px 0',
    fontSize: '22px',
    fontWeight: '600'
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  formRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px'
  },
  label: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#333'
  },
  input: {
    padding: '12px',
    border: '1px solid #E0E0E0',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none'
  },
  select: {
    padding: '12px',
    border: '1px solid #E0E0E0',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    background: 'white'
  },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '8px'
  },
  cancelBtn: {
    padding: '12px 24px',
    border: '1px solid #E0E0E0',
    background: 'white',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#666',
    cursor: 'pointer'
  }
};

export default TrackDashboard;