import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';

const TrackDetail = () => {
  const { trackId } = useParams();
  const navigate = useNavigate();
  const [track, setTrack] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [sessionForm, setSessionForm] = useState({
    session_type: 'learning',
    duration_seconds: 1200,
    nodes_completed: 0,
    energy_level: 3,
    focus_quality: 3,
    notes: ''
  });
  const [verificationForm, setVerificationForm] = useState({
    evidence: [],
    rubric_scores: {},
    verifier: 'model'
  });
  const [submitting, setSubmitting] = useState(false);

  const API_BASE = '/api/tracks';

  const fetchTrack = async () => {
    try {
      const res = await fetch(`${API_BASE}/${trackId}`, {
        headers: { 'X-User-ID': '1' }
      });
      if (!res.ok) throw new Error('Track not found');
      const data = await res.json();
      setTrack(data);
    } catch (err) {
      console.error('Failed to fetch track:', err);
      navigate('/tracks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrack();
  }, [trackId]);

  const handleSessionSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/${trackId}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': '1'
        },
        body: JSON.stringify(sessionForm)
      });
      if (!res.ok) throw new Error('Failed to record session');
      fetchTrack();
      setSessionForm({ ...sessionForm, duration_seconds: 1200, nodes_completed: 0, notes: '' });
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerificationSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/${trackId}/verify/${track.current_ladder_rung}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': '1'
        },
        body: JSON.stringify(verificationForm)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Verification failed');
      alert(data.passed ? '✅ Verification passed! Advanced to next level.' : `❌ Verification failed: ${data.feedback}`);
      fetchTrack();
      setVerificationForm({ evidence: [], rubric_scores: {}, verifier: 'model' });
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleTrackAction = async (action) => {
    const statusMap = { pause: 'paused', resume: 'active', archive: 'archived' };
    try {
      await fetch(`${API_BASE}/${trackId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': '1'
        },
        body: JSON.stringify({ status: statusMap[action] })
      });
      fetchTrack();
    } catch (err) {
      console.error('Track action failed:', err);
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

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>Loading track details...</div>
      </div>
    );
  }

  if (!track) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>Track not found</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <Link to="/tracks" style={styles.backLink}>
          ← Back to Dashboard
        </Link>
        <div style={styles.headerRight}>
          <span style={{...styles.statusBadge, backgroundColor: getStatusColor(track.status)}}>
            {track.status.toUpperCase()}
          </span>
          {track.status === 'active' && (
            <button style={styles.actionBtn} onClick={() => handleTrackAction('pause')}>
              Pause Track
            </button>
          )}
          {track.status === 'paused' && (
            <button style={{...styles.actionBtn, background: '#4CAF50'}} onClick={() => handleTrackAction('resume')}>
              Resume Track
            </button>
          )}
          {track.status === 'done' && (
            <button style={{...styles.actionBtn, background: '#9E9E9E'}} onClick={() => handleTrackAction('archive')}>
              Archive
            </button>
          )}
        </div>
      </div>

      {/* Track Title & Meta */}
      <div style={styles.trackMeta}>
        <h1 style={styles.trackTitle}>{track.skill_tag}</h1>
        <div style={styles.metaRow}>
          <span style={styles.metaItem}>{getGoalTypeLabel(track.goal_type)}</span>
          <span style={styles.metaItem}>Target: {track.goal_level}</span>
          <span style={styles.metaItem}>Ref: {track.skill_graph_ref}</span>
          <span style={styles.metaItem}>Started: {new Date(track.started_at).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Progress Overview */}
      <div style={styles.progressSection}>
        <div style={styles.progressCard}>
          <div style={styles.progressRingContainer}>
            <svg style={styles.progressSvg} viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" stroke="#E0E0E0" strokeWidth="8" fill="none" />
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
            <div style={styles.progressCenter}>
              <div style={styles.progressValue}>{track.progress_pct.toFixed(1)}%</div>
              <div style={styles.progressLabel}>Overall Progress</div>
            </div>
          </div>
          <div style={styles.progressStats}>
            <div style={styles.stat}>
              <div style={styles.statValue}>{getLevelName(track.current_ladder_rung)}</div>
              <div style={styles.statLabel}>Current Level</div>
            </div>
            <div style={styles.stat}>
              <div style={styles.statValue}>{track.mastery_vector ? Object.keys(track.mastery_vector).length : 0}</div>
              <div style={styles.statLabel}>Sub-skills Tracked</div>
            </div>
            <div style={styles.stat}>
              <div style={styles.statValue}>
                {track.verification_checkpoints?.filter(c => c.status === 'verified').length || 0} / {track.verification_checkpoints?.length || 0}
              </div>
              <div style={styles.statLabel}>Verified Checkpoints</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={styles.tabs}>
        {['overview', 'ladder', 'mastery', 'sessions', 'verification'].map(tab => (
          <button
            key={tab}
            style={{...styles.tab, ...(activeTab === tab ? styles.activeTab : {})}}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={styles.tabContent}>
        {activeTab === 'overview' && <OverviewTab track={track} />}
        {activeTab === 'ladder' && <LadderTab track={track} />}
        {activeTab === 'mastery' && <MasteryTab track={track} />}
        {activeTab === 'sessions' && <SessionsTab track={track} onRecordSession={handleSessionSubmit} sessionForm={sessionForm} setSessionForm={setSessionForm} />}
        {activeTab === 'verification' && <VerificationTab track={track} onSubmit={handleVerificationSubmit} form={verificationForm} setForm={setVerificationForm} submitting={submitting} />}
      </div>

      {/* Coach Narrative */}
      {track.coach_narrative && (
        <div style={styles.coachCard}>
          <div style={styles.coachHeader}>🤖 Coach Narrative</div>
          <p style={styles.coachText}>{track.coach_narrative}</p>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Tab Components
// ============================================================================

const OverviewTab = ({ track }) => (
  <div style={styles.tabPanel}>
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>Current Rung: {track.current_rung?.level_name || 'Novice'}</h3>
      <p style={styles.cardSubtitle}>Focus on these foundational skills:</p>
      <div style={styles.skillsGrid}>
        {track.current_rung?.sub_skills?.map((skill, i) => (
          <div key={i} style={styles.skillCard}>
            <h4 style={styles.skillCardTitle}>{skill.name}</h4>
            <p style={styles.skillCardDesc}>{skill.description}</p>
            <div style={styles.canDoList}>
              {skill.can_do_statements?.map((stmt, j) => (
                <div key={j} style={styles.canDoItem}>
                  <span style={styles.checkmark}>✓</span>
                  <span>{stmt}</span>
                </div>
              ))}
            </div>
            {skill.prerequisites?.length && (
              <div style={styles.prereqs}>
                <small>Prerequisites: {skill.prerequisites.join(', ')}</small>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>

    {track.next_rung && (
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>Next Up: {track.next_rung.level_name}</h3>
        <p style={styles.cardSubtitle}>Preview of what you'll unlock:</p>
        <div style={styles.nextSkills}>
          {track.next_rung.sub_skills?.map((skill, i) => (
            <div key={i} style={styles.nextSkillItem}>
              <strong>{skill.name}</strong>
              <span style={styles.nextSkillDesc}>{skill.description}</span>
            </div>
          ))}
        </div>
      </div>
    )}

    <div style={styles.card}>
      <h3 style={styles.cardTitle}>Batch Schedule</h3>
      <div style={styles.scheduleGrid}>
        <div style={styles.scheduleItem}>
          <span style={styles.scheduleLabel}>Pace</span>
          <span style={styles.scheduleValue}>{track.batch_schedule?.pace || 'focus'}</span>
        </div>
        <div style={styles.scheduleItem}>
          <span style={styles.scheduleLabel}>Sessions/Week</span>
          <span style={styles.scheduleValue}>{track.batch_schedule?.target_sessions_per_week || 3}</span>
        </div>
        <div style={styles.scheduleItem}>
          <span style={styles.scheduleLabel}>Session Length</span>
          <span style={styles.scheduleValue}>{track.batch_schedule?.session_length_minutes || 20} min</span>
        </div>
        <div style={styles.scheduleItem}>
          <span style={styles.scheduleLabel}>Completed Sessions</span>
          <span style={styles.scheduleValue}>{track.batch_schedule?.session_count || 0}</span>
        </div>
      </div>
    </div>
  </div>
);

const LadderTab = ({ track }) => (
  <div style={styles.tabPanel}>
    <div style={styles.ladderContainer}>
      {track.current_rung && (
        <div style={styles.ladderRung}>
          <div style={styles.rungHeader}>
            <span style={styles.rungLevel}>Level {track.current_rung.level_index}: {track.current_rung.level_name}</span>
            <span style={styles.rungXP}>+{track.current_rung.xp_reward} XP</span>
          </div>
          <div style={styles.rungEvidence}>
            Evidence: {track.current_rung.evidence_types.join(', ')}
          </div>
          <div style={styles.rungSkills}>
            {track.current_rung.sub_skills.map((skill, i) => (
              <div key={i} style={styles.ladderSkill}>
                <div style={styles.ladderSkillName}>{skill.name}</div>
                <div style={styles.ladderSkillDesc}>{skill.description}</div>
                <div style={styles.ladderCanDo}>
                  {skill.can_do_statements?.map((stmt, j) => (
                    <span key={j} style={styles.canDoTag}>✓ {stmt}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>

    <div style={styles.ladderFull}>
      <h3 style={styles.cardTitle}>Full Ladder ({track.goal_type})</h3>
      <div style={styles.ladderSteps}>
        {[
          { index: 0, name: 'Novice' },
          { index: 1, name: 'Competent' },
          { index: 2, name: 'Proficient' },
          { index: 3, name: 'Expert' }
        ].map((level, i) => (
          <div key={level.index} style={{
            ...styles.ladderStep,
            opacity: i <= track.current_ladder_rung ? 1 : 0.4,
            borderLeftColor: i <= track.current_ladder_rung ? getStatusColor(track.status) : '#E0E0E0'
          }}>
            <div style={styles.stepNumber}>{level.index}</div>
            <div style={styles.stepContent}>
              <div style={styles.stepName}>{level.name}</div>
              <div style={styles.stepStatus}>
                {i < track.current_ladder_rung ? '✅ Completed' :
                 i === track.current_ladder_rung ? '🔄 In Progress' :
                 '🔒 Locked'}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

const MasteryTab = ({ track }) => (
  <div style={styles.tabPanel}>
    <h3 style={styles.cardTitle}>Mastery Vector</h3>
    <p style={styles.cardSubtitle}>Per-sub-skill proficiency tracking with confidence scores</p>
    {track.mastery_vector && Object.entries(track.mastery_vector).map(([skillName, data]) => (
      <div key={skillName} style={styles.masteryCard}>
        <div style={styles.masteryHeader}>
          <span style={styles.masteryName}>{skillName}</span>
          <span style={styles.masteryLevel}>Level {data.level_index}: {data.level_name}</span>
        </div>
        <div style={styles.masteryBarContainer}>
          <div style={{
            ...styles.masteryBar,
            width: `${data.score}%`,
            background: data.score >= 70 ? '#4CAF50' : data.score >= 40 ? '#FF9800' : '#F44336'
          }} />
        </div>
        <div style={styles.masteryStats}>
          <span>Score: {data.score}/100</span>
          <span>Confidence: {(data.confidence * 100).toFixed(0)}%</span>
          <span>Evidence: {data.evidence_count}</span>
        </div>
        {data.can_do_statements?.length && (
          <div style={styles.canDoList}>
            {data.can_do_statements.map((stmt, j) => (
              <div key={j} style={styles.canDoItem}>
                <span style={styles.checkmark}>✓</span>
                <span>{stmt}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    ))}
    {!track.mastery_vector && <p style={styles.empty}>No mastery data yet. Complete sessions to build your vector.</p>}
  </div>
);

const SessionsTab = ({ track, onRecordSession, sessionForm, setSessionForm }) => (
  <div style={styles.tabPanel}>
    <h3 style={styles.cardTitle}>Record Learning Session</h3>
    <form onSubmit={onRecordSession} style={styles.sessionForm}>
      <div style={styles.formRow}>
        <div style={styles.formGroup}>
          <label style={styles.label}>Session Type</label>
          <select
            style={styles.select}
            value={sessionForm.session_type}
            onChange={e => setSessionForm({...sessionForm, session_type: e.target.value})}
          >
            <option value="learning">📚 Learning</option>
            <option value="practice">🏋️ Practice</option>
            <option value="verification">✅ Verification</option>
            <option value="recap">🔄 Recap/Review</option>
            <option value="diagnostic">🔍 Diagnostic</option>
          </select>
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Duration (minutes)</label>
          <input
            style={styles.input}
            type="number"
            value={sessionForm.duration_seconds / 60}
            onChange={e => setSessionForm({...sessionForm, duration_seconds: parseInt(e.target.value) * 60})}
            min="1"
            max="480"
          />
        </div>
      </div>
      <div style={styles.formRow}>
        <div style={styles.formGroup}>
          <label style={styles.label}>Nodes Completed</label>
          <input
            style={styles.input}
            type="number"
            value={sessionForm.nodes_completed}
            onChange={e => setSessionForm({...sessionForm, nodes_completed: parseInt(e.target.value) || 0})}
            min="0"
          />
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Energy Level (1-5)</label>
          <input
            style={styles.input}
            type="number"
            value={sessionForm.energy_level}
            onChange={e => setSessionForm({...sessionForm, energy_level: parseInt(e.target.value) || 3})}
            min="1"
            max="5"
          />
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Focus Quality (1-5)</label>
          <input
            style={styles.input}
            type="number"
            value={sessionForm.focus_quality}
            onChange={e => setSessionForm({...sessionForm, focus_quality: parseInt(e.target.value) || 3})}
            min="1"
            max="5"
          />
        </div>
      </div>
      <div style={styles.formGroup}>
        <label style={styles.label}>Notes</label>
        <textarea
          style={{...styles.input, minHeight: '80px', resize: 'vertical'}}
          value={sessionForm.notes}
          onChange={e => setSessionForm({...sessionForm, notes: e.target.value})}
          placeholder="What did you work on? Any insights or blockers?"
        />
      </div>
      <button type="submit" style={styles.submitBtn} disabled={submitting}>
        Record Session
      </button>
    </form>

    <div style={styles.card} style={{marginTop: '24px'}}>
      <h3 style={styles.cardTitle}>Recent Sessions</h3>
      <p style={styles.cardSubtitle}>Session history would appear here (requires session log API)</p>
    </div>
  </div>
);

const VerificationTab = ({ track, onSubmit, form, setForm, submitting }) => (
  <div style={styles.tabPanel}>
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>Current Verification Checkpoint</h3>
      {track.verification_checkpoints && track.verification_checkpoints.map(cp => (
        <div key={cp.level_index} style={{...styles.verificationCard, borderLeft: `4px solid ${cp.status === 'verified' ? '#4CAF50' : cp.status === 'failed' ? '#F44336' : '#FF9800'}`}}>
          <div style={styles.verificationHeader}>
            <span style={styles.verificationLevel}>Level {cp.level_index}: {track.current_rung?.level_name || 'Current'}</span>
            <span style={{
              ...styles.verificationStatus,
              background: cp.status === 'verified' ? '#E8F5E9' : cp.status === 'failed' ? '#FDEDEC' : '#FFF3E0'
            }}>
              {cp.status.toUpperCase()}
            </span>
          </div>
          <div style={styles.verificationDetails}>
            <div>Evidence Types: {cp.evidence_refs?.length || 0} submitted</div>
            <div>Rubric Criteria: {Object.keys(cp.rubric_scores || {}).length}</div>
            <div>Verifier: {cp.verifier}</div>
            {cp.verified_at && <div>Verified: {new Date(cp.verified_at).toLocaleDateString()}</div>}
            {cp.expires_at && <div>Expires: {new Date(cp.expires_at).toLocaleDateString()}</div>}
          </div>
        </div>
      ))}
      {!track.verification_checkpoints?.length && (
        <p style={styles.empty}>No verification checkpoints yet. Complete learning to unlock verification.</p>
      )}
    </div>

    {track.verification_checkpoints?.some(cp => cp.status === 'pending' || cp.status === 'in_progress') && (
      <div style={styles.card} style={{marginTop: '24px'}}>
        <h3 style={styles.cardTitle}>Submit Verification Evidence</h3>
        <form onSubmit={onSubmit} style={styles.sessionForm}>
          <div style={styles.formGroup}>
            <label style={styles.label}>Evidence (JSON array)</label>
            <textarea
              style={{...styles.input, minHeight: '100px', fontFamily: 'monospace', fontSize: '12px'}}
              value={JSON.stringify(form.evidence, null, 2)}
              onChange={e => {
                try { setForm({...form, evidence: JSON.parse(e.target.value) }); }
                catch { setForm({...form, evidence: e.target.value }); }
              }}
              placeholder='[{"type": "project", "uri": "github.com/user/repo", "description": "Built a budget tracker"}]'
            />
          </div>
          <div style={styles.formGroup}>
            <label style={styles.label}>Rubric Scores (JSON)</label>
            <textarea
              style={{...styles.input, minHeight: '100px', fontFamily: 'monospace', fontSize: '12px'}}
              value={JSON.stringify(form.rubric_scores, null, 2)}
              onChange={e => {
                try { setForm({...form, rubric_scores: JSON.parse(e.target.value) }); }
                catch { setForm({...form, rubric_scores: e.target.value }); }
              }}
              placeholder='{"code_quality": {"score": 85, "confidence": 0.9, "rationale": "Clean architecture"}, "functionality": {"score": 90, "confidence": 0.95, "rationale": "All tests pass"}}'
            />
          </div>
          <div style={styles.formGroup}>
            <label style={styles.label}>Verifier</label>
            <select style={styles.select} value={form.verifier} onChange={e => setForm({...form, verifier: e.target.value})}>
              <option value="model">🤖 Model</option>
              <option value="human">👤 Human</option>
              <option value="peer">👥 Peer</option>
            </select>
          </div>
          <button type="submit" style={styles.submitBtn} disabled={submitting}>
            {submitting ? 'Submitting...' : 'Submit for Verification'}
          </button>
        </form>
      </div>
    )}
  </div>
);

// ============================================================================
// Styles
// ============================================================================

const styles = {
  container: {
    padding: '24px',
    maxWidth: '1000px',
    margin: '0 auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  loading: {
    textAlign: 'center',
    padding: '60px',
    fontSize: '18px',
    color: '#666'
  },
  error: {
    textAlign: 'center',
    padding: '60px',
    fontSize: '18px',
    color: '#F44336'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px'
  },
  backLink: {
    color: '#1976D2',
    textDecoration: 'none',
    fontWeight: '500'
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  statusBadge: {
    padding: '6px 12px',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '600',
    color: 'white',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  actionBtn: {
    background: '#1976D2',
    color: 'white',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  trackMeta: {
    marginBottom: '24px'
  },
  trackTitle: {
    margin: '0 0 12px 0',
    fontSize: '32px',
    fontWeight: '700',
    color: '#1a1a1a'
  },
  metaRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '16px',
    color: '#666',
    fontSize: '14px'
  },
  metaItem: {
    background: '#F5F5F5',
    padding: '6px 12px',
    borderRadius: '20px'
  },
  progressSection: {
    marginBottom: '24px'
  },
  progressCard: {
    background: 'white',
    border: '1px solid #E0E0E0',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 2px 12px rgba(0,0,0,0.04)'
  },
  progressRingContainer: {
    display: 'flex',
    justifyContent: 'center',
    position: 'relative',
    marginBottom: '24px'
  },
  progressSvg: {
    width: '120px',
    height: '120px',
    transform: 'rotate(-90deg)'
  },
  progressCircle: {
    transition: 'stroke-dashoffset 0.5s ease-out'
  },
  progressCenter: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    textAlign: 'center'
  },
  progressValue: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#1a1a1a'
  },
  progressLabel: {
    fontSize: '12px',
    color: '#999',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  progressStats: {
    display: 'flex',
    justifyContent: 'space-around',
    paddingTop: '16px',
    borderTop: '1px solid #E0E0E0'
  },
  stat: {
    textAlign: 'center'
  },
  statValue: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#1a1a1a'
  },
  statLabel: {
    fontSize: '12px',
    color: '#999',
    marginTop: '4px'
  },
  tabs: {
    display: 'flex',
    gap: '4px',
    marginBottom: '24px',
    borderBottom: '1px solid #E0E0E0',
    paddingBottom: '8px'
  },
  tab: {
    background: 'none',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '8px 8px 0 0',
    fontSize: '14px',
    fontWeight: '500',
    color: '#666',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  activeTab: {
    background: '#E3F2FD',
    color: '#1976D2',
    borderBottom: '3px solid #1976D2'
  },
  tabContent: {
    minHeight: '400px'
  },
  tabPanel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px'
  },
  card: {
    background: 'white',
    border: '1px solid #E0E0E0',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
  },
  cardTitle: {
    margin: '0 0 8px 0',
    fontSize: '18px',
    fontWeight: '600',
    color: '#1a1a1a'
  },
  cardSubtitle: {
    margin: '0 0 16px 0',
    color: '#666',
    fontSize: '14px'
  },
  skillsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '16px'
  },
  skillCard: {
    padding: '16px',
    background: '#F5F5F5',
    borderRadius: '10px'
  },
  skillCardTitle: {
    margin: '0 0 8px 0',
    fontSize: '15px',
    fontWeight: '600',
    color: '#333'
  },
  skillCardDesc: {
    margin: '0 0 12px 0',
    fontSize: '13px',
    color: '#666'
  },
  canDoList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  canDoItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    color: '#4CAF50'
  },
  checkmark: {
    fontWeight: 'bold'
  },
  prereqs: {
    marginTop: '8px',
    color: '#999'
  },
  nextSkills: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  nextSkillItem: {
    padding: '12px',
    background: '#E3F2FD',
    borderRadius: '8px'
  },
  nextSkillDesc: {
    display: 'block',
    marginTop: '4px',
    fontSize: '13px',
    color: '#1565C0'
  },
  scheduleGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: '16px'
  },
  scheduleItem: {
    textAlign: 'center',
    padding: '16px',
    background: '#F5F5F5',
    borderRadius: '10px'
  },
  scheduleLabel: {
    display: 'block',
    fontSize: '12px',
    color: '#999',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '4px'
  },
  scheduleValue: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#1a1a1a'
  },
  ladderContainer: {
    marginBottom: '24px'
  },
  ladderRung: {
    background: 'white',
    border: '1px solid #E0E0E0',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
  },
  rungHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px'
  },
  rungLevel: {
    fontSize: '20px',
    fontWeight: '700',
    color: '#1a1a1a'
  },
  rungXP: {
    background: '#FFF3E0',
    color: '#F57F17',
    padding: '4px 12px',
    borderRadius: '16px',
    fontSize: '13px',
    fontWeight: '600'
  },
  rungEvidence: {
    color: '#666',
    fontSize: '13px',
    marginBottom: '16px'
  },
  rungSkills: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  ladderSkill: {
    padding: '16px',
    background: '#F5F5F5',
    borderRadius: '10px'
  },
  ladderSkillName: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '4px'
  },
  ladderSkillDesc: {
    fontSize: '13px',
    color: '#666',
    marginBottom: '8px'
  },
  ladderCanDo: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px'
  },
  canDoTag: {
    fontSize: '11px',
    color: '#4CAF50',
    background: '#E8F5E9',
    padding: '3px 8px',
    borderRadius: '4px'
  },
  ladderFull: {},
  ladderSteps: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  ladderStep: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px 20px',
    background: 'white',
    border: '1px solid #E0E0E0',
    borderLeftWidth: '4px',
    borderRadius: '0 10px 10px 0',
    transition: 'all 0.2s'
  },
  stepNumber: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    background: '#F5F5F5',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: '700',
    fontSize: '16px',
    color: '#666'
  },
  stepContent: {
    flex: 1
  },
  stepName: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#1a1a1a',
    marginBottom: '4px'
  },
  stepStatus: {
    fontSize: '13px',
    color: '#666'
  },
  masteryCard: {
    background: 'white',
    border: '1px solid #E0E0E0',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '16px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
  },
  masteryHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px'
  },
  masteryName: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#1a1a1a'
  },
  masteryLevel: {
    fontSize: '12px',
    color: '#1976D2',
    background: '#E3F2FD',
    padding: '4px 10px',
    borderRadius: '12px'
  },
  masteryBarContainer: {
    height: '8px',
    background: '#E0E0E0',
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '8px'
  },
  masteryBar: {
    height: '100%',
    borderRadius: '4px',
    transition: 'width 0.3s ease'
  },
  masteryStats: {
    display: 'flex',
    gap: '16px',
    fontSize: '12px',
    color: '#666'
  },
  empty: {
    textAlign: 'center',
    padding: '40px',
    color: '#999'
  },
  sessionForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  formRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: '16px'
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
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
  submitBtn: {
    background: '#1976D2',
    color: 'white',
    border: 'none',
    padding: '14px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    marginTop: '8px'
  },
  verificationCard: {
    background: 'white',
    border: '1px solid #E0E0E0',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '16px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
  },
  verificationHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px'
  },
  verificationLevel: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#1a1a1a'
  },
  verificationStatus: {
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: '600',
    textTransform: 'uppercase'
  },
  verificationDetails: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '16px',
    fontSize: '13px',
    color: '#666'
  },
  coachCard: {
    marginTop: '24px',
    padding: '20px',
    background: '#FFF8E1',
    border: '1px solid #FFE082',
    borderRadius: '12px'
  },
  coachHeader: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#F57F17',
    marginBottom: '8px'
  },
  coachText: {
    margin: 0,
    fontSize: '14px',
    color: '#F57F17',
    lineHeight: '1.6',
    fontStyle: 'italic'
  }
};

export default TrackDetail;