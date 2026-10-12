import React, { useState, useEffect } from 'react';
import { getUserId } from '../hooks/useApi';

/**
 * LL-06 recap surface: the due queue (retrieval-first, one card at a time,
 * question BEFORE answer) plus the on-demand rewind ("take me back through X").
 */
export default function RecapSession() {
  const userId = getUserId();
  const [due, setDue] = useState(null);
  const [idx, setIdx] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(0);
  const [rewindTopic, setRewindTopic] = useState('');
  const [digest, setDigest] = useState(null);

  async function load() {
    const res = await fetch(`/api/recap/${userId}/due`);
    if (res.ok) {
      const data = await res.json();
      setDue(data.due || []);
    } else setDue([]);
  }
  useEffect(() => { load(); }, []);

  async function submit(quality) {
    setBusy(true);
    const item = due[idx];
    const res = await fetch(`/api/recap/${userId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skill_tag: item.skill_tag, track_id: item.track_id, quality }),
    });
    if (res.ok) setDone((d) => d + 1);
    setRevealed(false);
    setIdx((i) => i + 1);
    setBusy(false);
  }

  async function doRewind(e) {
    e.preventDefault();
    if (!rewindTopic.trim()) return;
    setBusy(true);
    const res = await fetch(`/api/recap/${userId}/rewind?topic=${encodeURIComponent(rewindTopic)}`);
    if (res.ok) setDigest(await res.json());
    setBusy(false);
  }

  const item = due && due[idx];

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '2rem 1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <h1 style={{ margin: 0 }}>Recap</h1>

      {/* On-demand rewind */}
      <form onSubmit={doRewind} style={{ display: 'flex', gap: 8 }}>
        <input
          value={rewindTopic}
          onChange={(e) => setRewindTopic(e.target.value)}
          placeholder="Take me back through…"
          style={{ flex: 1, padding: '10px 12px', borderRadius: 10, border: '1px solid #d1d5db' }}
        />
        <button type="submit" disabled={busy} style={{ padding: '10px 16px', borderRadius: 10, border: 'none', background: '#9333ea', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>
          Rewind
        </button>
      </form>

      {digest && (
        <div style={{ background: '#faf5ff', border: '1px solid #e9d5ff', borderRadius: 16, padding: '1.25rem' }}>
          <h3 style={{ marginTop: 0 }}>{digest.summary}</h3>
          {digest.sections.map((s) => (
            <div key={s.skill_tag} style={{ marginBottom: '1rem' }}>
              <div style={{ fontWeight: 700, color: '#581c87' }}>{s.skill_tag} — {s.can_do}</div>
              <p style={{ margin: '6px 0' }}><em>Q:</em> {s.prompt.question}</p>
              {s.gaps && s.gaps.map((g, i) => (
                <p key={i} style={{ margin: '6px 0', color: '#b45309' }}><em>Gap re-ask:</em> {g.question}</p>
              ))}
              <details>
                <summary style={{ cursor: 'pointer', color: '#7e22ce' }}>Reveal (after you try)</summary>
                <ul style={{ fontSize: '0.85rem' }}>
                  {(s.reveal.citations || []).map((c, i) => <li key={i}>Source {i + 1}: {c}</li>)}
                </ul>
              </details>
            </div>
          ))}
        </div>
      )}

      {/* Due queue */}
      {!due ? <p>Loading your recaps…</p>
        : idx >= due.length ? (
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 16, padding: '1.5rem', textAlign: 'center' }}>
            <h3 style={{ margin: 0 }}>Session done — {done} recap{done === 1 ? '' : 's'} cleared</h3>
            <p style={{ color: '#16a34a' }}>Mastery ledger and verification currency updated.</p>
          </div>
        ) : (
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 16, padding: '1.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: 8 }}>
              {idx + 1} of {due.length} · ~{item.minutes} min · box {item.bucket}{item.overdue_days > 0 ? ` · waiting ${item.overdue_days}d` : ''}
            </div>
            <h3 style={{ marginTop: 0 }}>Recall: <code>{item.skill_tag}</code></h3>
            <p>Without looking — what's the one move you learned here, and where did you apply it?</p>
            {revealed ? (
              <p style={{ background: '#f3f4f6', borderRadius: 10, padding: 10, fontSize: '0.9rem' }}>
                Check yourself against your own history, then rate honestly. A lapse is information, not failure.
              </p>
            ) : (
              <button onClick={() => setRevealed(true)} style={{ padding: '8px 14px', borderRadius: 10, border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer' }}>
                I've recalled it — show rating
              </button>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 12, opacity: revealed ? 1 : 0.35, pointerEvents: revealed ? 'auto' : 'none' }}>
              {[['Forgot', 1, '#fee2e2'], ['Hard', 3, '#fef3c7'], ['Good', 4, '#e0e7ff'], ['Perfect', 5, '#dcfce7']].map(([label, q, bg]) => (
                <button key={q} disabled={busy} onClick={() => submit(q)} style={{ padding: 10, background: bg, border: 'none', borderRadius: 10, fontWeight: 700, cursor: 'pointer' }}>
                  {label} ({q})
                </button>
              ))}
            </div>
          </div>
        )}
    </div>
  );
}
