// LL-04 delivery widgets: the concrete passive vs active presentation forms.
// Active: predict-before-reveal, retrieval prompt, mini-task, teach-it-back,
// project step. Passive: plain read/watch/explain. Each widget reports its
// retrieval outcome upward so the session telemetry can store it.

import React, { useState } from 'react';

export function PredictBeforeReveal({ question, answer, onOutcome }) {
  const [guess, setGuess] = useState('');
  const [revealed, setRevealed] = useState(false);
  return (
    <div className="delivery-active" style={{ border: '1px solid #a5b4fc', borderRadius: 12, padding: '0.9rem', margin: '0.75rem 0', background: '#eef2ff' }}>
      <p style={{ fontWeight: 700, margin: 0 }}>🔮 Predict first — {question}</p>
      {!revealed ? (
        <div style={{ display: 'flex', gap: '.5rem', marginTop: '.5rem' }}>
          <input value={guess} onChange={(e) => setGuess(e.target.value)}
            placeholder="Your prediction…" style={{ flex: 1, padding: '.4rem' }} />
          <button className="btn-secondary" onClick={() => setRevealed(true)}>Reveal</button>
        </div>
      ) : (
        <>
          <p style={{ marginTop: '.5rem' }}><strong>Answer:</strong> {answer}</p>
          <div style={{ display: 'flex', gap: '.5rem' }}>
            <button onClick={() => onOutcome?.('correct')}>I predicted that ✓</button>
            <button onClick={() => onOutcome?.('partial')}>Partly</button>
            <button onClick={() => onOutcome?.('incorrect')}>Missed it ✗</button>
          </div>
        </>
      )}
    </div>
  );
}

export function RetrievalPrompt({ prompt, answer, onOutcome }) {
  const [answered, setAnswered] = useState(false);
  const [selfGrade, setSelfGrade] = useState(null);
  return (
    <div className="delivery-active" style={{ border: '1px solid #86efac', borderRadius: 12, padding: '0.9rem', margin: '0.75rem 0', background: '#f0fdf4' }}>
      <p style={{ fontWeight: 700, margin: 0 }}>🧠 Retrieve before reading — {prompt}</p>
      {!answered ? (
        <button className="btn-secondary" onClick={() => setAnswered(true)}>Think, then reveal</button>
      ) : !selfGrade ? (
        <>
          <p><strong>It was:</strong> {answer}</p>
          <div style={{ display: 'flex', gap: '.5rem' }}>
            {['correct', 'partial', 'incorrect'].map((g) => (
              <button key={g} onClick={() => { setSelfGrade(g); onOutcome?.(g); }}>
                {g === 'correct' ? 'Got it' : g === 'partial' ? 'Close' : 'Missed'}
              </button>
            ))}
          </div>
        </>
      ) : <p style={{ color: '#166534' }}>Logged. That attempt is what moves the needle.</p>}
    </div>
  );
}

export function TeachItBack({ topic, onOutcome }) {
  const [text, setText] = useState('');
  return (
    <div className="delivery-active" style={{ border: '1px solid #fcd34d', borderRadius: 12, padding: '0.9rem', margin: '0.75rem 0', background: '#fffbeb' }}>
      <p style={{ fontWeight: 700, margin: 0 }}>🗣 Teach it back — explain {topic} in your own words, two sentences.</p>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3}
        style={{ width: '100%', marginTop: '.5rem', padding: '.4rem' }} />
      <button className="btn-secondary" disabled={text.trim().length < 10}
        onClick={() => onOutcome?.(text.trim().length > 60 ? 'correct' : 'partial')}>Submit</button>
    </div>
  );
}

export function ModeBadge({ modeClass, decidedBy }) {
  const labels = { passive: '📖 Passive', active: '⚡ Active' };
  const why = { escalation: 'flipped by the loop', energy_override: 'low-energy scaffold',
                classifier: 'classified', track_default: 'track default' };
  return (
    <span title={why[decidedBy] || decidedBy} style={{
      fontSize: '.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: 999,
      background: modeClass === 'active' ? '#dcfce7' : '#e0e7ff',
      color: modeClass === 'active' ? '#166534' : '#3730a3',
    }}>{labels[modeClass]}</span>
  );
}

export function CompanionBridge({ bridge }) {
  if (!bridge) return null;
  return (
    <div role="note" style={{
      borderLeft: '4px solid #4f46e5', background: '#f5f3ff', padding: '.7rem .9rem',
      borderRadius: '0 10px 10px 0', margin: '1rem 0', fontStyle: 'italic',
    }}>
      {bridge.text}
    </div>
  );
}
