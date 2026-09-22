import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getUserId } from '../hooks/useApi';

export default function ReviewDeck() {
  const userId = getUserId();
  const navigate = useNavigate();
  const [deck, setDeck] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [sessionXP, setSessionXP] = useState(0);

  useEffect(() => {
    async function loadReviews() {
      try {
        const res = await fetch(`/api/reviews/${userId}/due`);
        if (res.ok) {
          const data = await res.json();
          setDeck(data);
        }
      } catch (err) {
        console.error('Failed to load review deck', err);
      } finally {
        setLoading(false);
      }
    }
    loadReviews();
  }, [userId]);

  const handleScore = async (quality) => {
    const currentItem = deck[currentIndex];
    setSubmitting(true);
    try {
      const res = await fetch(`/api/reviews/${currentItem.id}/submit?quality=${quality}`, {
        method: 'POST'
      });
      if (res.ok) {
        setSessionXP(prev => prev + 10);
      }
    } catch (err) {
      console.error('Failed to submit review score', err);
    } finally {
      setSubmitting(false);
      setFlipped(false);
      setCurrentIndex(prev => prev + 1);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem' }}>
        <h2>Loading your memory deck...</h2>
      </div>
    );
  }

  if (currentIndex >= deck.length) {
    return (
      <div style={{ maxWidth: '600px', margin: '3rem auto', textAlign: 'center', padding: '3rem', background: 'var(--card-bg)', borderRadius: '16px', border: '1px solid var(--card-border)', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎉</div>
        <h2 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: '0.5rem' }}>Review Session Complete!</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>You've reviewed all your due concepts for today. Your memory is solidifying.</p>
        
        {sessionXP > 0 && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(16, 185, 129, 0.1)', color: '#059669', padding: '8px 16px', borderRadius: '20px', fontWeight: 700, marginBottom: '2rem' }}>
            <span>✨</span>
            <span>+{sessionXP} XP Earned</span>
          </div>
        )}
        
        <div>
          <button onClick={() => navigate('/')} className="submit-btn" style={{ width: 'auto', background: '#3b82f6' }}>
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const currentItem = deck[currentIndex];

  return (
    <div style={{ maxWidth: '700px', margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>⚡</span> Active Recall
        </h1>
        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#3b82f6', background: 'rgba(59, 130, 246, 0.1)', padding: '4px 12px', borderRadius: '12px' }}>
          Card {currentIndex + 1} of {deck.length}
        </div>
      </div>

      <div style={{ minHeight: '300px', perspective: '1000px', marginBottom: '2rem' }}>
        <div 
          style={{ 
            width: '100%', height: '100%', minHeight: '300px',
            position: 'relative',
            transition: 'transform 0.6s',
            transformStyle: 'preserve-3d',
            transform: flipped ? 'rotateX(180deg)' : 'rotateX(0deg)'
          }}
        >
          {/* Front of card */}
          <div style={{
            position: 'absolute', width: '100%', height: '100%',
            backfaceVisibility: 'hidden',
            background: 'var(--card-bg)',
            border: '2px solid var(--card-border)',
            borderRadius: '16px',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            boxShadow: '0 10px 30px rgba(0,0,0,0.08)',
            cursor: 'pointer'
          }} onClick={() => setFlipped(true)}>
            <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '1rem', letterSpacing: '1px' }}>Question</div>
            <h2 style={{ margin: 0, fontSize: '1.4rem', textAlign: 'center', lineHeight: 1.5 }}>{currentItem.question}</h2>
            <div style={{ marginTop: '2rem', fontSize: '0.9rem', color: '#3b82f6', fontWeight: 600 }}>Click to reveal answer</div>
          </div>

          {/* Back of card */}
          <div style={{
            position: 'absolute', width: '100%', height: '100%',
            backfaceVisibility: 'hidden',
            background: 'linear-gradient(135deg, #f8fafc, #f1f5f9)',
            border: '2px solid #e2e8f0',
            borderRadius: '16px',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            transform: 'rotateX(180deg)',
            boxShadow: '0 10px 30px rgba(0,0,0,0.08)'
          }}>
            <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem', letterSpacing: '1px' }}>Answer</div>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', color: '#1e293b' }}>{currentItem.correct_answer}</h3>
            
            {currentItem.explanation && (
              <div style={{ marginTop: 'auto', background: '#fff', padding: '1rem', borderRadius: '8px', fontSize: '0.9rem', color: '#475569', borderLeft: '4px solid #3b82f6' }}>
                <strong>Explanation:</strong> {currentItem.explanation}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Scoring Controls */}
      <div style={{ opacity: flipped ? 1 : 0, transition: 'opacity 0.4s', pointerEvents: flipped ? 'auto' : 'none' }}>
        <h4 style={{ textAlign: 'center', marginBottom: '1rem', color: 'var(--text-muted)' }}>How well did you remember this?</h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
          <button 
            disabled={submitting}
            onClick={() => handleScore(1)}
            style={{ padding: '12px', background: '#fee2e2', color: '#b91c1c', border: '1px solid #fecaca', borderRadius: '10px', fontWeight: 700, cursor: 'pointer' }}>
            Forgot (1)
          </button>
          <button 
            disabled={submitting}
            onClick={() => handleScore(3)}
            style={{ padding: '12px', background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a', borderRadius: '10px', fontWeight: 700, cursor: 'pointer' }}>
            Hard (3)
          </button>
          <button 
            disabled={submitting}
            onClick={() => handleScore(4)}
            style={{ padding: '12px', background: '#e0e7ff', color: '#4338ca', border: '1px solid #c7d2fe', borderRadius: '10px', fontWeight: 700, cursor: 'pointer' }}>
            Good (4)
          </button>
          <button 
            disabled={submitting}
            onClick={() => handleScore(5)}
            style={{ padding: '12px', background: '#dcfce7', color: '#15803d', border: '1px solid #bbf7d0', borderRadius: '10px', fontWeight: 700, cursor: 'pointer' }}>
            Perfect (5)
          </button>
        </div>
      </div>
    </div>
  );
}
