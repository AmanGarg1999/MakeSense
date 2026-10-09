import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { getUserId } from '../hooks/useApi';
import { useDeliveryTelemetry, trackEngagement } from '../hooks/useDeliveryTelemetry';
import { generateBridge } from '../delivery/deliveryEngine';
import { ModeBadge, RetrievalPrompt, PredictBeforeReveal, CompanionBridge } from '../delivery/DeliveryWidgets';

const EVENT_TRACKER = import.meta.env?.VITE_EVENT_TRACKER_URL || 'http://localhost:8000';

export default function LessonViewer() {
  const { lessonId } = useParams();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const pathId = location.state?.pathId || searchParams.get('pathId');
  const nodeId = location.state?.nodeId || searchParams.get('nodeId');
  const pathTitle = location.state?.pathTitle || '';
  const track = location.state?.track || null; // LL-02 track object when launched from a track

  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [bridge, setBridge] = useState(null);

  const sessionId = useRef(`lsn-${lessonId}-${Date.now()}`).current;
  const skillTag = (track?.skill_tag) || (lesson?.skill_tags?.[0]) || `lesson:${lessonId}`;
  const telemetry = useDeliveryTelemetry({
    track, trackId: track?.id, skillTag,
    sessionId, energy: location.state?.energy ?? null,
  });

  // Pull the LL-04 escalation state for this skill so mode resolution honors
  // the adaptive flip rule (escalated skills get active delivery next N sessions).
  useEffect(() => {
    let cancelled = false;
    fetch(`${EVENT_TRACKER}/api/delivery/escalations/${getUserId()}/${encodeURIComponent(skillTag)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (!cancelled && d?.escalation) telemetry.setEscalation(d.escalation); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [skillTag]);

  // Companion bridge from LL-02 ladder/mastery state when available.
  useEffect(() => {
    if (!track?.ladder || !track?.mastery_vector) return;
    setBridge(generateBridge(
      { skillTag, currentLadderRung: track.current_ladder_rung ?? 0 },
      track.mastery_vector, track.ladder));
  }, [track, skillTag]);

  const decision = useMemo(() => (
    lesson ? telemetry.decide(
      { title: lesson.title, contentType: lesson.content_type || 'read',
        tags: lesson.skill_tags || [], kind: lesson.segment_kind },
      lesson.prior_visits || 0) : null
  ), [lesson, telemetry.decide]);

  useEffect(() => {
    async function loadLesson() {
      try {
        const res = await fetch(`/api/lessons/${lessonId}`);
        if (!res.ok) throw new Error('Lesson not found');
        const data = await res.json();
        setLesson(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadLesson();
  }, [lessonId]);

  const sendFeedback = async (type) => {
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lesson_id: lessonId,
          feedback_type: type,
          user_identifier: getUserId()
        })
      });
      setFeedbackSent(true);
    } catch (err) {
      console.error('Feedback error:', err);
    }
  };

  // LL-04: engagement + telemetry for the played lesson segment.
  const segRef = useRef(null);
  const engagementRef = useRef(null);
  const retrievalRef = useRef('none');
  useEffect(() => {
    if (!lesson || !decision) return;
    engagementRef.current = trackEngagement(segRef.current, {
      onSignal: (sig) => {
        telemetry.recordSegment({
          segment_index: 0,
          title: lesson.title,
          content_type: lesson.content_type || 'read',
          tags: lesson.skill_tags || [],
          kind_hint: decision.segment_kind,
          delivery_mode: decision.mode,
          mode_class: decision.modeClass,
          decided_by: decision.decidedBy,
          dwell_seconds: sig.dwell_seconds,
          paused_seconds: sig.paused_seconds,
          abandoned: sig.abandoned,
          retrieval_outcome: retrievalRef.current,
          ladder_level: track?.current_ladder_rung ?? null,
        });
      },
    });
    return () => engagementRef.current?.stop();
  }, [lesson, decision]);

  const onRetrieval = (outcome) => {
    retrievalRef.current = outcome;
    if (engagementRef.current) { engagementRef.current.stop(); engagementRef.current = null; }
    telemetry.recordSegment({
      segment_index: 1, kind_hint: 'consolidation',
      title: `${lesson?.title} — retrieval`, delivery_mode: decision?.mode || 'retrieval_prompt',
      mode_class: 'active', decided_by: decision?.decidedBy || 'classifier',
      retrieval_outcome: outcome, dwell_seconds: 0,
    });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
        <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>Synthesizing lesson view...</p>
      </div>
    );
  }

  if (error || !lesson) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--error)' }}>
        <h2>Unable to load lesson</h2>
        <p>{error || 'Lesson not found'}</p>
        <Link to="/" className="btn-secondary" style={{ marginTop: '1rem', display: 'inline-flex' }}>← Return to Dashboard</Link>
      </div>
    );
  }

  const content = lesson.content || {};
  const sections = content.sections || [];
  const examples = content.examples || [];

  return (
    <div className="lesson-viewer">
      <CompanionBridge bridge={bridge} />
      {pathId && (
        <div style={{ marginBottom: '1rem' }}>
          <Link
            to={`/path/${pathId}`}
            style={{
              color: '#4f46e5',
              textDecoration: 'none',
              fontWeight: 600,
              fontSize: '0.875rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: '#eef2ff',
              padding: '6px 12px',
              borderRadius: '8px'
            }}
          >
            &larr; Return to 3D Skill Tree {pathTitle ? `(${pathTitle})` : ''}
          </Link>
        </div>
      )}
      <div className="lesson-header">
        <div className="lesson-meta">
          <span className="badge badge-difficulty">{lesson.difficulty || 'Intermediate'}</span>
          <span className="badge badge-time">⏱ {lesson.estimated_time_minutes || 15} min read</span>
          {decision && <ModeBadge modeClass={decision.modeClass} decidedBy={decision.decidedBy} />}
          {(lesson.skill_tags || []).map(tag => (
            <span key={tag} className="badge badge-skill">{tag}</span>
          ))}
        </div>
        <h1>{lesson.title}</h1>
        {lesson.summary && <p className="lesson-summary">{lesson.summary}</p>}
      </div>

      <div className="lesson-sections-wrapper" ref={segRef}
        data-expected-seconds={(lesson.estimated_time_minutes || 15) * 60}
        data-completed="false">
        {decision?.mode === 'predict_before_reveal' && (
          <PredictBeforeReveal
            question={content.predict_question || `Before the details: what do you think ${lesson.title} comes down to?`}
            answer={content.predict_answer || lesson.summary || sections[0]?.content || ''}
            onOutcome={onRetrieval} />
        )}
        {sections.map((section, i) => (
          <section key={i} className="lesson-section">
            <h2>{section.heading}</h2>
            <div className="section-content">
              {(section.content || '').split('\n').map((para, j) => {
                if (para.startsWith('```')) return null;
                if (para.startsWith('- ') || para.startsWith('* ')) {
                  return <li key={j}>{para.substring(2)}</li>;
                }
                if (para.startsWith('**') && para.endsWith('**')) {
                  return <p key={j}><strong>{para.slice(2, -2)}</strong></p>;
                }
                return para.trim() ? <p key={j}>{para}</p> : null;
              })}
            </div>
            {section.key_points && section.key_points.length > 0 && (
              <div className="key-points">
                <h4>📌 Essential Takeaways</h4>
                <ul>
                  {section.key_points.map((point, k) => (
                    <li key={k}>{point}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        ))}

        {decision?.segment_kind === 'consolidation'
          && decision?.modeClass === 'active' && decision.mode !== 'predict_before_reveal' && (
          <RetrievalPrompt
            prompt={content.retrieval_prompt || `From memory: what were the key points of ${lesson.title}?`}
            answer={(sections[0]?.key_points || []).join('; ') || lesson.summary || ''}
            onOutcome={onRetrieval} />
        )}

        {examples.length > 0 && (
          <div className="lesson-section" style={{ background: '#0f172a', color: '#f8fafc', borderColor: 'rgba(255,255,255,0.1)' }}>
            <h2 style={{ color: '#f8fafc' }}>💡 Practical Implementations</h2>
            {examples.map((example, i) => (
              <div key={i} className="example-block" style={{ marginTop: i === 0 ? 0 : '1.5rem', background: 'transparent', padding: 0 }}>
                <h3 style={{ color: '#a5b4fc', fontSize: '1.05rem', marginBottom: '0.5rem' }}>{example.title}</h3>
                <pre className="code-block">
                  <code>{example.code_or_text}</code>
                </pre>
                {example.explanation && (
                  <p className="example-explanation">{example.explanation}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="lesson-footer">
        <div className="feedback-section">
          <span>Was this lesson clear and helpful?</span>
          {feedbackSent ? (
            <span style={{ color: 'var(--success)', fontWeight: 700 }}>Thank you for helping us improve! 🙏</span>
          ) : (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={() => sendFeedback('up')} className="btn-feedback" title="Helpful">👍</button>
              <button onClick={() => sendFeedback('down')} className="btn-feedback" title="Needs improvement">👎</button>
            </div>
          )}
        </div>
        <Link
          to={`/quiz/${lessonId}${pathId ? `?pathId=${pathId}&nodeId=${nodeId || ''}` : ''}`}
          state={{ pathId, nodeId, pathTitle }}
          className="submit-btn"
          style={{ width: 'auto', padding: '0.75rem 1.5rem' }}
        >
          Test Knowledge in Quiz →
        </Link>
      </div>
    </div>
  );
}
