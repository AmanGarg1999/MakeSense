import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { getUserId } from '../hooks/useApi';

export default function QuizPage() {
  const { lessonId } = useParams();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const pathId = location.state?.pathId || searchParams.get('pathId');
  const nodeId = location.state?.nodeId || searchParams.get('nodeId');

  const [quiz, setQuiz] = useState(null);
  const [loading, setLoading] = useState(true);
  const [answers, setAnswers] = useState({});
  const [results, setResults] = useState(null);
  const [pathEvolution, setPathEvolution] = useState(null);
  const [streakResult, setStreakResult] = useState(null);
  const [newAchievements, setNewAchievements] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [currentQ, setCurrentQ] = useState(0);

  useEffect(() => {
    async function loadQuiz() {
      try {
        const res = await fetch(`/api/lessons/${lessonId}/quiz`);
        if (!res.ok) throw new Error('Quiz not found');
        const data = await res.json();
        setQuiz(data);
      } catch (err) {
        console.error('Quiz load error:', err);
      } finally {
        setLoading(false);
      }
    }
    loadQuiz();
  }, [lessonId]);

  const handleAnswer = (questionIndex, answer) => {
    setAnswers(prev => ({ ...prev, [questionIndex]: answer }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const answerList = Object.entries(answers).map(([qi, answer]) => ({
        question_index: parseInt(qi),
        answer: answer
      }));

      const res = await fetch('/api/quiz/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lesson_id: lessonId,
          user_id: parseInt(getUserId()),
          answers: answerList
        })
      });

      if (!res.ok) throw new Error('Failed to submit quiz');
      const data = await res.json();
      setResults(data);
      if (data.streak_result) setStreakResult(data.streak_result);
      if (data.new_achievements) setNewAchievements(data.new_achievements);

      // If associated with a learning path node, evaluate and evolve path
      if (pathId && nodeId) {
        try {
          const scorePercent = Math.round((data.score || 0) * 100);
          const evolveRes = await fetch(`/api/paths/${pathId}/nodes/${nodeId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quiz_score: scorePercent })
          });
          if (evolveRes.ok) {
            const evolveData = await evolveRes.json();
            setPathEvolution(evolveData);
          }
        } catch (evolveErr) {
          console.error('Failed to evolve learning path:', evolveErr);
        }
      }
    } catch (err) {
      console.error('Submit error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
        <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>Loading interactive knowledge check...</p>
      </div>
    );
  }

  if (!quiz || !quiz.questions || quiz.questions.length === 0) {
    return (
      <div className="quiz-card" style={{ textAlign: 'center', padding: '3rem' }}>
        <h2>No quiz registered for this lesson</h2>
        <p style={{ color: 'var(--text-muted)', margin: '1rem 0' }}>The instructor or AI model did not generate question items for this unit.</p>
        <Link to="/" className="btn-secondary">Return to Dashboard</Link>
      </div>
    );
  }

  if (results) {
    const scorePercent = Math.round(results.score * 100);
    return (
      <div className="quiz-results">
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <div className="xp-badge-earned">
            <span>✨</span>
            <span>+{results.xp_earned || 50} XP Awarded!</span>
          </div>
          {streakResult && streakResult.current_streak > 0 && (
            <div className="xp-badge-earned" style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#d97706', border: '1px solid #fcd34d' }}>
              <span>🔥</span>
              <span>{streakResult.current_streak} Day Streak!</span>
            </div>
          )}
        </div>

        {newAchievements && newAchievements.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '1.5rem', alignItems: 'center' }}>
            {newAchievements.map(ach => (
              <div key={ach.id} style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'linear-gradient(135deg, #fef3c7, #fef08a)', padding: '10px 16px', borderRadius: '12px', color: '#854d0e', border: '1px solid #fde047', boxShadow: '0 2px 8px rgba(250,204,21,0.2)' }}>
                <span style={{ fontSize: '1.5rem' }}>{ach.icon}</span>
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontWeight: 800, fontSize: '0.9rem' }}>Achievement Unlocked: {ach.name}</div>
                  <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>{ach.description} (+{ach.xp_reward} XP)</div>
                </div>
              </div>
            ))}
          </div>
        )}

        <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '0.5rem' }}>Quiz Results</h1>
        <p style={{ color: 'var(--text-muted)' }}>Great job testing your active recall!</p>

        <div className="score-circle">
          <span className="score-number">{results.correct} / {results.total}</span>
          <span className="score-percent">{scorePercent}%</span>
        </div>

        <div style={{ textAlign: 'left', margin: '2rem 0' }}>
          {(results.results || []).map((r, i) => (
            <div key={i} className={`result-item ${r.is_correct ? 'correct' : 'incorrect'}`}>
              <div style={{ fontSize: '1.25rem' }}>{r.is_correct ? '✅' : '❌'}</div>
              <div>
                <p style={{ fontWeight: 700, marginBottom: '0.25rem' }}>{r.question}</p>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  Your answer: <strong>{r.user_answer || 'Skipped'}</strong>
                </p>
                {!r.is_correct && (
                  <p style={{ fontSize: '0.9rem', color: 'var(--error)', marginTop: '0.2rem' }}>
                    Correct answer: <strong>{r.correct_answer}</strong>
                  </p>
                )}
                {r.explanation && (
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', marginTop: '0.5rem', background: 'rgba(255,255,255,0.6)', padding: '0.5rem', borderRadius: '4px' }}>
                    💡 {r.explanation}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

        {pathEvolution && (
          <div style={{ background: '#f0fdf4', border: '1.5px solid #86efac', borderRadius: '12px', padding: '1.25rem', margin: '1.5rem 0', textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ fontSize: '1.4rem' }}>🌱</span>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#166534' }}>
                AI Mentor Path Adaptation
              </h3>
            </div>
            <p style={{ margin: '0 0 8px', fontSize: '0.95rem', color: '#14532d', lineHeight: 1.5 }}>
              {pathEvolution.feedback}
            </p>
            {pathEvolution.new_nodes_created && pathEvolution.new_nodes_created.length > 0 && (
              <div style={{ background: '#fff', borderRadius: '8px', padding: '8px 12px', border: '1px solid #bbf7d0', fontSize: '0.85rem', color: '#166534', marginTop: '8px' }}>
                <strong>Adaptive Milestone Added:</strong> {pathEvolution.new_nodes_created.map(n => n.title).join(', ')}
              </div>
            )}
          </div>
        )}

        <div className="results-actions" style={{ flexWrap: 'wrap', gap: '10px' }}>
          {pathId ? (
            <Link
              to={`/path/${pathId}`}
              className="submit-btn"
              style={{
                width: 'auto',
                background: 'linear-gradient(135deg, #10b981, #059669)',
                textDecoration: 'none',
                boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
              }}
            >
              🚀 Return to 3D Skill Tree & See Evolved Path →
            </Link>
          ) : (
            <Link to="/" className="btn-secondary">← Back to Dashboard</Link>
          )}
          <Link to={`/lesson/${lessonId}${pathId ? `?pathId=${pathId}&nodeId=${nodeId || ''}` : ''}`} className="btn-secondary" style={{ width: 'auto' }}>
            Review Lesson Material
          </Link>
          {pathId && <Link to="/" className="btn-secondary">Dashboard</Link>}
        </div>
      </div>
    );
  }

  const questions = quiz.questions;
  const question = questions[currentQ];
  const progressPercent = Math.round(((currentQ + 1) / questions.length) * 100);
  const totalAnswered = Object.keys(answers).length;

  return (
    <div className="quiz-page">
      <div className="quiz-card">
        <div className="quiz-header">
          <div className="quiz-progress">
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)' }}>
              <span>Question {currentQ + 1} of {questions.length}</span>
              <span>{progressPercent}% Complete</span>
            </div>
            <div className="xp-bar-track" style={{ height: 8, marginTop: 4 }}>
              <div className="xp-bar-fill" style={{ width: `${progressPercent}%` }} />
            </div>
          </div>
          <h1 style={{ marginTop: '1.25rem' }}>{question.question}</h1>
        </div>

        {question.type === 'mcq' && question.options ? (
          <div className="mcq-options">
            {question.options.map((option, i) => (
              <button
                key={i}
                type="button"
                className={`option-btn ${answers[currentQ] === option ? 'selected' : ''}`}
                onClick={() => handleAnswer(currentQ, option)}
              >
                <span className="option-letter">{String.fromCharCode(65 + i)}</span>
                <span className="option-text">{option}</span>
              </button>
            ))}
          </div>
        ) : (
          <div style={{ margin: '1.5rem 0' }}>
            <textarea
              className="form-group textarea"
              style={{ width: '100%', padding: '1rem', borderRadius: 8, border: '1.5px solid var(--card-border)', fontFamily: 'inherit', fontSize: '1rem' }}
              placeholder="Type your response..."
              value={answers[currentQ] || ''}
              onChange={(e) => handleAnswer(currentQ, e.target.value)}
              rows={4}
            />
          </div>
        )}

        <div className="quiz-nav">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setCurrentQ(Math.max(0, currentQ - 1))}
            disabled={currentQ === 0}
          >
            ← Previous
          </button>

          {currentQ < questions.length - 1 ? (
            <button
              type="button"
              className="submit-btn"
              style={{ width: 'auto' }}
              onClick={() => setCurrentQ(currentQ + 1)}
            >
              Next Question →
            </button>
          ) : (
            <button
              type="button"
              className="submit-btn btn-submit"
              style={{ width: 'auto' }}
              onClick={handleSubmit}
              disabled={submitting || totalAnswered === 0}
            >
              {submitting ? 'Scoring Answers...' : `Submit Answers (${totalAnswered}/${questions.length})`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
