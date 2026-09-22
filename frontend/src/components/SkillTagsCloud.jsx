import React from 'react';

export default function SkillTagsCloud({ skills = [] }) {
  if (!skills || skills.length === 0) {
    return <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Complete quizzes to start tracking your skill ratings.</p>;
  }

  return (
    <div className="skills-grid-wrapper">
      {skills.map((skill, index) => {
        const score = typeof skill.score === 'number' ? Math.round(skill.score) : 0;
        const tag = skill.tag || skill.skill_tag || 'Skill';
        
        let tierLabel = 'Novice';
        if (score > 1800) tierLabel = 'Master';
        else if (score > 1500) tierLabel = 'Adept';
        else if (score > 1200) tierLabel = 'Practitioner';

        return (
          <div key={index} className="skill-pill">
            <span>{tag}</span>
            <span className="skill-score-badge">{score} &bull; {tierLabel}</span>
          </div>
        );
      })}
    </div>
  );
}
