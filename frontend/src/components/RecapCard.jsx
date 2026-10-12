import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getUserId, useApi } from '../hooks/useApi';

/**
 * LL-06 recap card for the home/coach surface.
 * Due recaps styled as low-effort wins: 2-3 min each, streak-friendly.
 * Backed by /api/recap/{userId}/due (LL-07 stores + Leitner scheduler).
 */
export default function RecapCard() {
  const userId = getUserId();
  const { data } = useApi(`/api/recap/${userId}/due`);
  const due = data?.due || [];
  const upcoming = data?.upcoming_count || 0;

  if (!data) return null;

  const xp = due.length * 10;

  return (
    <div style={{ background: 'linear-gradient(135deg, #faf5ff, #f3e8ff)', border: '1px solid #e9d5ff', borderRadius: 16, padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#7e22ce', textTransform: 'uppercase', marginBottom: 4 }}>Recap</div>
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#581c87', fontWeight: 800 }}>
            {due.length > 0 ? `${due.length} quick review${due.length === 1 ? '' : 's'} due` : 'Nothing due — nicely spaced'}
          </h3>
        </div>
        {due.length > 0 && (
          <div style={{ background: '#a855f7', color: '#fff', fontWeight: 800, padding: '4px 10px', borderRadius: 12, fontSize: '0.9rem' }}>
            +{xp} XP
          </div>
        )}
      </div>

      {due.length > 0 ? (
        <>
          <ul style={{ margin: 0, paddingLeft: '1.2rem', color: '#6b21a8', fontSize: '0.9rem' }}>
            {due.slice(0, 4).map((d) => (
              <li key={`${d.track_id}:${d.skill_tag}`} style={{ marginBottom: 4 }}>
                <strong>{d.skill_tag}</strong> — ~{d.minutes} min
                {d.overdue_days > 0 ? ` · ${d.overdue_days}d waiting` : ''}
              </li>
            ))}
          </ul>
          <p style={{ margin: 0, fontSize: '0.85rem', color: '#7e22ce', opacity: 0.85 }}>
            Short recall, not a re-read. Keeps your streak and your skill currency fresh.
          </p>
          <Link to="/recap" style={{ display: 'block', textAlign: 'center', background: '#9333ea', color: '#fff', textDecoration: 'none', padding: '10px', borderRadius: 10, fontWeight: 700 }}>
            Do my recaps &rarr;
          </Link>
        </>
      ) : (
        <p style={{ margin: 0, fontSize: '0.9rem', color: '#7e22ce', opacity: 0.9 }}>
          {upcoming > 0 ? `${upcoming} item${upcoming === 1 ? '' : 's'} scheduled ahead — ` : ''}
          need a rewind of something? <Link to="/recap" style={{ color: '#7e22ce', fontWeight: 700 }}>Take me back through…</Link>
        </p>
      )}
    </div>
  );
}
