import React from 'react';

export default function XPProgressBar({ currentXp = 0, xpToNextLevel = 100 }) {
  const safeNext = xpToNextLevel > 0 ? xpToNextLevel : 100;
  const progressPercent = Math.min(100, Math.max(0, Math.round((currentXp / safeNext) * 100)));

  return (
    <div className="xp-bar-wrapper">
      <div className="xp-bar-track">
        <div className="xp-bar-fill" style={{ width: `${progressPercent}%` }} />
      </div>
      <div className="xp-bar-labels">
        <span>{currentXp} XP Earned</span>
        <span>{safeNext} XP Goal ({progressPercent}%)</span>
      </div>
    </div>
  );
}
