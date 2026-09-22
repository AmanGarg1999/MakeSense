import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function MentorProfilingModal({ isOpen, onClose }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Profiling state
  const [topic, setTopic] = useState('');
  const [goal, setGoal] = useState('life_skill');
  const [baseline, setBaseline] = useState('beginner');
  const [modality, setModality] = useState('hands_on');
  const [pace, setPace] = useState('focus');
  const [painPoints, setPainPoints] = useState('');
  const [name, setName] = useState('');
  const [pathwayOptions, setPathwayOptions] = useState([]);
  const [selectedPathway, setSelectedPathway] = useState('fast_track');
  const [mentorPersona, setMentorPersona] = useState('encouraging');

  if (!isOpen) return null;

  const handleRequestOptions = async () => {
    if (!topic.trim()) {
      setError('Please specify what topic or skill you want to learn.');
      setStep(1);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const res = await fetch('/api/paths/preview-options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name || 'Learner',
          topic: topic.trim(),
          goal,
          baseline,
          modality,
          pace,
          pain_points: painPoints,
          mentor_persona: mentorPersona
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to curate learning pathways');
      }

      const options = await res.json();
      setPathwayOptions(options);
      const rec = options.find(o => o.recommended) || options[0];
      if (rec) setSelectedPathway(rec.id);
      setStep(4);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFinalSubmit = async (chosenTrackId) => {
    const trackToUse = chosenTrackId || selectedPathway || 'fast_track';
    try {
      setLoading(true);
      setError(null);

      const res = await fetch('/api/paths/curate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name || 'Learner',
          topic: topic.trim(),
          goal,
          baseline,
          modality,
          pace,
          pain_points: painPoints,
          track_type: trackToUse,
          mentor_persona: mentorPersona
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to curate learning path');
      }

      const pathData = await res.json();
      onClose();
      navigate(`/path/${pathData.id}`);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const suggestionChips = [
    { label: '💰 Personal Finance', val: 'Personal Finance' },
    { label: '🎸 Guitar Foundations', val: 'Guitar' },
    { label: '🤖 Machine Learning', val: 'Machine Learning' },
    { label: '⚡ System Design', val: 'System Design' },
    { label: '🐍 Python Data Science', val: 'Python Data Science' }
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '1rem'
      }}
    >
      <div
        style={{
          background: 'var(--card-bg, #ffffff)',
          width: '100%',
          maxWidth: step === 4 ? '840px' : '560px',
          maxHeight: '90vh',
          overflowY: 'auto',
          borderRadius: '20px',
          padding: '2rem',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          position: 'relative',
          transition: 'max-width 0.3s ease'
        }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '18px',
            right: '18px',
            background: 'none',
            border: 'none',
            fontSize: '1.25rem',
            cursor: 'pointer',
            color: 'var(--text-muted)'
          }}
        >
          ✕
        </button>

        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '1.5rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: 'linear-gradient(135deg, #4f46e5, #7c3aed)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', color: '#fff' }}>
            🧠
          </div>
          <div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
              AI Mentor Diagnostic & Pathway Synthesis
            </h2>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Step {step} of 4 &bull; {step === 4 ? 'Compare and inspect your curated pathways' : 'Profiling your learning needs'}
            </p>
          </div>
        </div>

        {error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '10px', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}

        {/* STEP 1: Topic & Name */}
        {step === 1 && (
          <div>
            <label style={{ display: 'block', fontWeight: 700, fontSize: '0.9rem', marginBottom: '6px', color: 'var(--text-main)' }}>
              What do you want to learn?
            </label>
            <input
              type="text"
              placeholder="e.g. Personal Finance, Guitar, Machine Learning, Rust..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '10px',
                border: '1px solid var(--card-border)',
                fontSize: '1rem',
                marginBottom: '10px'
              }}
            />

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '1.5rem' }}>
              {suggestionChips.map((chip, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setTopic(chip.val)}
                  style={{
                    padding: '5px 10px',
                    borderRadius: '20px',
                    border: '1px solid var(--card-border)',
                    background: topic === chip.val ? '#eef2ff' : '#f8fafc',
                    color: topic === chip.val ? '#4f46e5' : 'var(--text-muted)',
                    fontWeight: 600,
                    fontSize: '0.75rem',
                    cursor: 'pointer'
                  }}
                >
                  {chip.label}
                </button>
              ))}
            </div>

            <label style={{ display: 'block', fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-main)' }}>
              Your Name (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Alex"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '10px',
                border: '1px solid var(--card-border)',
                fontSize: '0.9rem',
                marginBottom: '1.5rem'
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                disabled={!topic.trim()}
                onClick={() => setStep(2)}
                style={{
                  background: '#4f46e5',
                  color: '#fff',
                  border: 'none',
                  padding: '10px 20px',
                  borderRadius: '10px',
                  fontWeight: 700,
                  cursor: topic.trim() ? 'pointer' : 'not-allowed',
                  opacity: topic.trim() ? 1 : 0.6
                }}
              >
                Next: Your Goals &rarr;
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: Goal & Baseline */}
        {step === 2 && (
          <div>
            <label style={{ display: 'block', fontWeight: 700, fontSize: '0.9rem', marginBottom: '8px', color: 'var(--text-main)' }}>
              What is your primary desired outcome?
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '1.25rem' }}>
              {[
                { id: 'life_skill', icon: '💡', title: 'Daily Life Mastery', desc: 'Practical decisions & habits' },
                { id: 'career', icon: '💼', title: 'Career & Interview', desc: 'Professional fluency & depth' },
                { id: 'project', icon: '🛠️', title: 'Build a Project', desc: 'Create working solutions' },
                { id: 'hobby', icon: '🎸', title: 'Creative Hobby', desc: 'Play, create & enjoy' }
              ].map((g) => (
                <div
                  key={g.id}
                  onClick={() => setGoal(g.id)}
                  style={{
                    padding: '10px',
                    borderRadius: '10px',
                    border: goal === g.id ? '2px solid #4f46e5' : '1px solid var(--card-border)',
                    background: goal === g.id ? '#eef2ff' : '#f8fafc',
                    cursor: 'pointer'
                  }}
                >
                  <div style={{ fontSize: '1.2rem' }}>{g.icon}</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-main)', marginTop: '2px' }}>{g.title}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{g.desc}</div>
                </div>
              ))}
            </div>

            <label style={{ display: 'block', fontWeight: 700, fontSize: '0.9rem', marginBottom: '8px', color: 'var(--text-main)' }}>
              Where are you starting from?
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '1.5rem' }}>
              {[
                { id: 'beginner', title: 'Total Beginner', sub: 'Zero prior knowledge' },
                { id: 'intermediate', title: 'Foundational', sub: 'Know basic concepts' },
                { id: 'practitioner', title: 'Practitioner', sub: 'Want advanced depth' }
              ].map((b) => (
                <div
                  key={b.id}
                  onClick={() => setBaseline(b.id)}
                  style={{
                    padding: '8px',
                    borderRadius: '10px',
                    textAlign: 'center',
                    border: baseline === b.id ? '2px solid #4f46e5' : '1px solid var(--card-border)',
                    background: baseline === b.id ? '#eef2ff' : '#f8fafc',
                    cursor: 'pointer'
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--text-main)' }}>{b.title}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{b.sub}</div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <button
                type="button"
                onClick={() => setStep(1)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontWeight: 600 }}
              >
                &larr; Back
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                style={{ background: '#4f46e5', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '10px', fontWeight: 700, cursor: 'pointer' }}
              >
                Next: Pacing & Style &rarr;
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: Modality, Pace & Pain Points */}
        {step === 3 && (
          <div>
            <label style={{ display: 'block', fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-main)' }}>
              Daily Commitment & Pacing
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '1.25rem' }}>
              {[
                { id: 'micro', label: '⏱️ Micro', desc: '10 mins/day' },
                { id: 'focus', label: '🏃 Focus', desc: '20 mins/day' },
                { id: 'sprint', label: '🔥 Sprint', desc: '35+ mins/day' }
              ].map((p) => (
                <div
                  key={p.id}
                  onClick={() => setPace(p.id)}
                  style={{
                    padding: '8px',
                    borderRadius: '10px',
                    textAlign: 'center',
                    border: pace === p.id ? '2px solid #4f46e5' : '1px solid var(--card-border)',
                    background: pace === p.id ? '#eef2ff' : '#f8fafc',
                    cursor: 'pointer'
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: '0.8rem' }}>{p.label}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{p.desc}</div>
                </div>
              ))}
            </div>

            <label style={{ display: 'block', fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-main)' }}>
              Preferred Learning Style
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '1.25rem' }}>
              {[
                { id: 'hands_on', title: '💻 Hands-on Exercises', sub: 'Interactive code & drills' },
                { id: 'case_study', title: '📖 Real Scenarios', sub: 'Applied case studies' },
                { id: 'socratic', title: '🧠 Conceptual Models', sub: 'First-principles intuition' },
                { id: 'fast_quiz', title: '🎯 Active Recall', sub: 'Rapid micro-quizzing' }
              ].map((m) => (
                <div
                  key={m.id}
                  onClick={() => setModality(m.id)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '10px',
                    border: modality === m.id ? '2px solid #4f46e5' : '1px solid var(--card-border)',
                    background: modality === m.id ? '#eef2ff' : '#f8fafc',
                    cursor: 'pointer'
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: '0.8rem' }}>{m.title}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{m.sub}</div>
                </div>
              ))}
            </div>

            <label style={{ display: 'block', fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-main)' }}>
              Choose Your AI Mentor Persona
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '1.25rem' }}>
              {[
                { id: 'encouraging', title: '🌱 Guide', sub: 'Warm & supportive' },
                { id: 'socratic', title: '🤔 Socratic', sub: 'Questions & intuition' },
                { id: 'drill_sergeant', title: '🪖 Sergeant', sub: 'Strict & demanding' }
              ].map((m) => (
                <div
                  key={m.id}
                  onClick={() => setMentorPersona(m.id)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '10px',
                    border: mentorPersona === m.id ? '2px solid #4f46e5' : '1px solid var(--card-border)',
                    background: mentorPersona === m.id ? '#eef2ff' : '#f8fafc',
                    cursor: 'pointer',
                    textAlign: 'center'
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: '0.8rem' }}>{m.title}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{m.sub}</div>
                </div>
              ))}
            </div>

            <label style={{ display: 'block', fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px', color: 'var(--text-main)' }}>
              Any specific friction or topics you find intimidating? (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. compounding math, barre chord transitions, neural backprop..."
              value={painPoints}
              onChange={(e) => setPainPoints(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '10px',
                border: '1px solid var(--card-border)',
                fontSize: '0.85rem',
                marginBottom: '1.5rem'
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                type="button"
                onClick={() => setStep(2)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontWeight: 600 }}
              >
                &larr; Back
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={handleRequestOptions}
                style={{
                  background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
                  color: '#fff',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontWeight: 800,
                  fontSize: '0.95rem',
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(79, 70, 229, 0.3)'
                }}
              >
                {loading ? 'Consulting AI Mentor...' : 'Analyze My Pathways &rarr;'}
              </button>
            </div>
          </div>
        )}

        {/* STEP 4: Compare & Inspect Curated Pathways */}
        {step === 4 && (
          <div>
            <div style={{ marginBottom: '1.25rem' }}>
              <p style={{ margin: 0, fontSize: '0.88rem', color: 'var(--text-main)', lineHeight: 1.5 }}>
                Your AI Mentor analyzed your diagnostic profile and synthesized <strong>3 tailored pathways</strong> for <em>{topic}</em>.
                Select a pathway below to inspect its philosophy, milestones, and rationale before launching your 3D Skill Tree.
              </p>
            </div>

            {/* Pathways Comparison Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px', marginBottom: '1.5rem' }}>
              {pathwayOptions.map((opt) => {
                const isSelected = selectedPathway === opt.id;
                return (
                  <div
                    key={opt.id}
                    onClick={() => setSelectedPathway(opt.id)}
                    style={{
                      border: isSelected ? '2px solid #4f46e5' : '1px solid var(--card-border)',
                      borderRadius: '14px',
                      padding: '14px',
                      background: isSelected ? '#f5f3ff' : 'var(--surface-card, #f8fafc)',
                      cursor: 'pointer',
                      position: 'relative',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      transition: 'all 0.2s ease',
                      boxShadow: isSelected ? '0 4px 14px rgba(79, 70, 229, 0.15)' : 'none'
                    }}
                  >
                    <div>
                      {opt.badge && (
                        <div
                          style={{
                            display: 'inline-block',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '12px',
                            background: opt.recommended ? '#ecfdf5' : '#e0e7ff',
                            color: opt.recommended ? '#059669' : '#4338ca',
                            marginBottom: '8px'
                          }}
                        >
                          {opt.badge}
                        </div>
                      )}
                      <h3 style={{ margin: '0 0 4px', fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        {opt.title}
                      </h3>
                      <p style={{ margin: '0 0 10px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        {opt.subtitle}
                      </p>
                    </div>

                    <div style={{ paddingTop: '8px', borderTop: '1px solid rgba(0,0,0,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      <span>⏱️ {opt.estimated_total_hours}</span>
                      <span>🎯 {opt.milestone_count} Milestones</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Milestone Preview & Mentor Rationale Drawer */}
            {(() => {
              const activeOpt = pathwayOptions.find(o => o.id === selectedPathway) || pathwayOptions[0];
              if (!activeOpt) return null;

              return (
                <div style={{ background: '#f8fafc', border: '1px solid var(--card-border)', borderRadius: '14px', padding: '1.25rem', marginBottom: '1.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
                    <div style={{ fontWeight: 800, fontSize: '0.92rem', color: 'var(--text-main)' }}>
                      Path Rationale &amp; Milestone Sequence
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {(activeOpt.skills_unlocked || []).map((sk, idx) => (
                        <span key={idx} style={{ fontSize: '0.7rem', background: '#eef2ff', color: '#4f46e5', fontWeight: 700, padding: '2px 8px', borderRadius: '12px' }}>
                          ✓ {sk}
                        </span>
                      ))}
                    </div>
                  </div>

                  <p style={{ fontSize: '0.82rem', color: '#475569', margin: '0 0 12px', fontStyle: 'italic' }}>
                    "{activeOpt.philosophy}"
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto', paddingRight: '4px' }}>
                    {(activeOpt.milestones || []).map((ms) => (
                      <div
                        key={ms.index}
                        style={{
                          background: '#fff',
                          border: '1px solid var(--card-border)',
                          borderRadius: '8px',
                          padding: '8px 12px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '12px'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ width: 22, height: 22, borderRadius: '50%', background: '#e0e7ff', color: '#4f46e5', fontSize: '0.75rem', fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                            {ms.index}
                          </span>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-main)' }}>
                              {ms.title}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                              {ms.description}
                            </div>
                          </div>
                        </div>
                        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b', whiteSpace: 'nowrap' }}>
                          ⏱️ {ms.duration}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            {/* Bottom Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                type="button"
                onClick={() => setStep(3)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' }}
              >
                &larr; Refine Diagnostic
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => handleFinalSubmit(selectedPathway)}
                style={{
                  background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
                  color: '#fff',
                  border: 'none',
                  padding: '12px 28px',
                  borderRadius: '10px',
                  fontWeight: 800,
                  fontSize: '0.95rem',
                  cursor: 'pointer',
                  boxShadow: '0 4px 14px rgba(79, 70, 229, 0.35)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                {loading ? 'Igniting 3D Skill Tree...' : 'Embark on This Path & Launch 3D Skill Tree 🚀'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
