import React from 'react';

export default function LevelBadge({ levelName = 'Novice', currentLevel = 1 }) {
  return (
    <div className="level-badge-container">
      <div className="level-icon-wrapper">
        🏆
      </div>
      <div className="level-title-block">
        <h3>Level {currentLevel}: {levelName}</h3>
        <span className="level-subtitle">Adaptive Rank</span>
      </div>
    </div>
  );
}
