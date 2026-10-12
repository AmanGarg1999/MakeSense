import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  PATHWAY_LEVELS,
  LEVEL_LABELS,
  DEGREE_LEVELS,
  RADAR_GRANULARITY,
  HEATMAP_TIMESCALE,
  LEVEL_DASHBOARDS,
} from '../database/levels';
import { buildTranscriptDocument, downloadTranscriptJson } from '../lib/transcriptExport';
import { seedForLevel } from '../lib/coachInsightsSeed';

// LL-09d: Coach Insights (mk-027) — level-appropriate dashboards.
//
// Live mode reads the user's active pathway (GET /api/pathways/active,
// LL-09a) and the pedagogy summary (GET /api/coach/levels, LL-09b). A
// ?level=<canonical> query param renders the route-level demo from seed
// data with no server (acceptance: micro + undergrad variants).
//
// Conventions follow TrackDashboard.jsx (LL-02): inline style objects,
// fetch + X-User-ID header, no global state.

const HEADERS = { 'X-User-ID': '1' };

const levelAccent = {
  micro: '#4CAF50', certificate: '#2196F3', undergrad: '#7C3AED',
  masters: '#F59E0B', phd: '#DC2626', mba: '#0D9488',
};

export default function CoachInsights() {
  const [params] = useSearchParams();
  const demoLevel = params.get('level');

  const [live, setLive] = useState(null);      // {pathway, radarLevels}
  const [loading, setLoading] = useState(!demoLevel);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (demoLevel) { setLoading(false); return; }
    let cancelled = false;
    (async () => {
      try {
        const [active, levels] = await Promise.all([
          fetch('/api/pathways/active', { headers: HEADERS }).then(r => r.ok ? r.json() : null),
          fetch('/api/coach/levels', { headers: HEADERS }).then(r => r.ok ? r.json() : []),
        ]);
        if (!cancelled) setLive({ pathway: active, radarLevels: levels || [] });
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [demoLevel]);

  // Effective view: demo param wins, else live pathway, else micro seed.
  const level = useMemo(() => {
    if (demoLevel && PATHWAY_LEVELS.includes(demoLevel)) return demoLevel;
    return live?.pathway?.level || 'micro';
  }, [demoLevel, live]);

  const seed = useMemo(() => seedForLevel(level), [level]);
  const pathway = (!demoLevel && live?.pathway) ? live.pathway : seed.pathway;
  const pedagogy = (live?.radarLevels || []).find(r => r.level === level) || null;

  if (loading) {
    return <div style={styles.container}><div style={styles.loading}>Loading coach insights...</div></div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Coach Insights</h1>
          <div style={styles.subtitle}>
            {(LEVEL_LABELS[level] || level)} · radar: {RADAR_GRANULARITY[level]} · heatmap: {HEATMAP_TIMESCALE[level]}
            {demoLevel ? ' · demo (seed data)' : ''}
          </div>
        </div>
        <LevelSwitcher value={level} onChange={(lvl) => {
          window.location.hash = `#/coach-insights?level=${lvl}`;
        }} />
      </div>

      {error && !demoLevel && (
        <div style={styles.errorBanner}>
          API unavailable ({error}) — showing {LEVEL_LABELS[level]} demo from seed data.
        </div>
      )}
      {pedagogy && !demoLevel && (
        <div style={styles.pedagogyBar}>
          Coach cycle: {pedagogy.cycle.join(' → ')} · feedback: {pedagogy.feedback.replace('_', ' ')} ·
          recap ×{pedagogy.recap_multiplier}
        </div>
      )}

      {/* Widgets for this level (LEVEL_DASHBOARDS contract in levels.js) */}
      <div style={styles.widgetGrid}>
        {LEVEL_DASHBOARDS[level].map(widget => (
          <Widget
            key={widget}
            widget={widget}
            level={level}
            pathway={pathway}
            seed={seed}
          />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// widget dispatcher
// ---------------------------------------------------------------------------

function Widget({ widget, level, pathway, seed }) {
  const common = { pathway, seed, level };
  switch (widget) {
    case 'progress_ring':      return <ProgressRing {...common} />;
    case 'streak_counter':     return <StreakCounter {...common} />;
    case 'next_micro_task':    return <NextMicroTask {...common} />;
    case 'skill_radar':        return <SkillRadar {...common} />;
    case 'mastery_heatmap':    return <MasteryHeatmap {...common} />;
    case 'transcript_export':  return <TranscriptExport {...common} />;
    case 'project_timeline':   return <ProjectTimeline {...common} />;
    case 'portfolio_gallery':  return <PortfolioGallery {...common} />;
    case 'peer_feedback_wall': return <PeerFeedbackWall {...common} />;
    case 'completion_pct':     return <CompletionPct {...common} />;
    case 'gpa_trend':          return <GpaTrend {...common} />;
    case 'credit_progress':    return <CreditProgress {...common} />;
    case 'degree_audit':       return <DegreeAudit {...common} />;
    case 'exam_calendar':      return <ExamCalendar {...common} />;
    case 'milestone_tracker':  return <MilestoneTracker {...common} />;
    case 'literature_map':     return <LiteratureMap {...common} />;
    case 'thesis_chapters':    return <ThesisChapters {...common} title="Thesis chapters" />;
    case 'publication_count':  return <PublicationCount {...common} />;
    case 'dissertation_chapters': return <DissertationChapters {...common} />;
    case 'citation_network':   return <CitationNetwork {...common} />;
    case 'conference_timeline': return <ConferenceTimeline {...common} />;
    case 'advisor_meeting_log': return <AdvisorMeetingLog {...common} />;
    case 'case_matrix':        return <CaseMatrix {...common} />;
    case 'cohort_ranking':     return <CohortRanking {...common} />;
    case 'leadership_radar':   return <LeadershipRadar {...common} />;
    case 'capstone_integrator': return <CapstoneIntegrator {...common} />;
    default:                   return null;
  }
}

// ---------------------------------------------------------------------------
// shared primitives
// ---------------------------------------------------------------------------

function LevelSwitcher({ value, onChange }) {
  return (
    <div style={styles.levelPills}>
      {PATHWAY_LEVELS.map(lvl => (
        <button
          key={lvl}
          style={{
            ...styles.levelPill,
            ...(lvl === value ? { background: levelAccent[lvl], color: '#fff' } : {}),
          }}
          onClick={() => onChange(lvl)}
        >
          {LEVEL_LABELS[lvl]}
        </button>
      ))}
    </div>
  );
}

function Card({ title, children, wide = false }) {
  return (
    <div style={{ ...styles.card, ...(wide ? styles.cardWide : {}) }}>
      <h3 style={styles.cardTitle}>{title}</h3>
      {children}
    </div>
  );
}

function Ring({ pct, size = 110, color = '#4CAF50', label = 'Complete' }) {
  const r = 45;
  const circ = 2 * Math.PI * r;
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg viewBox="0 0 100 100" style={{ width: size, height: size, transform: 'rotate(-90deg)' }}>
        <circle cx="50" cy="50" r={r} stroke="#E0E0E0" strokeWidth="8" fill="none" />
        <circle
          cx="50" cy="50" r={r} stroke={color} strokeWidth="8" fill="none"
          strokeDasharray={`${(pct / 100) * circ} ${circ}`} strokeLinecap="round"
        />
      </svg>
      <div style={styles.ringText}>
        <span style={styles.ringValue}>{Math.round(pct)}%</span>
        <span style={styles.ringLabel}>{label}</span>
      </div>
    </div>
  );
}

// SVG radar polygon; nodes carry {label, mastery 0..1}
function RadarPoly({ nodes, color, size = 190 }) {
  const cx = size / 2, cy = size / 2, R = size / 2 - 26;
  const n = Math.max(nodes.length, 3);
  const pt = (i, radius) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + radius * Math.cos(a), cy + radius * Math.sin(a)];
  };
  const poly = nodes.map((node, i) => pt(i, R * (0.15 + 0.85 * (node.mastery ?? (node.mastered ? 1 : 0.2)))).join(',')).join(' ');
  const rings = [0.33, 0.66, 1].map(k =>
    Array.from({ length: n }, (_, i) => pt(i, R * k).join(',')).join(' '));
  return (
    <svg width={size} height={size}>
      {rings.map((pts, i) => (
        <polygon key={i} points={pts} fill="none" stroke="#E0E0E0" strokeWidth="1" />
      ))}
      {nodes.map((node, i) => {
        const [x, y] = pt(i, R + 14);
        return (
          <text key={i} x={x} y={y} fontSize="9" fill="#666" textAnchor="middle" dominantBaseline="middle">
            {String(node.label).length > 12 ? String(node.label).slice(0, 11) + '…' : node.label}
          </text>
        );
      })}
      <polygon points={poly} fill={color} fillOpacity="0.25" stroke={color} strokeWidth="2" />
      {nodes.map((node, i) => {
        const [x, y] = pt(i, R * (0.15 + 0.85 * (node.mastery ?? (node.mastered ? 1 : 0.2))));
        return <circle key={i} cx={x} cy={y} r="3.5" fill={color} />;
      })}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// MICRO widgets
// ---------------------------------------------------------------------------

function ProgressRing({ seed, level }) {
  return (
    <Card title="Single-skill progress">
      <div style={styles.centerBlock}>
        <Ring pct={seed.insights.progress_pct} color={levelAccent[level]} />
        <div style={styles.meta}>Current skill: {seed.radar.nodes[0]?.id || '—'}</div>
      </div>
    </Card>
  );
}

function StreakCounter({ seed }) {
  return (
    <Card title="Streak">
      <div style={styles.bigStat}>
        <span style={{ fontSize: 34 }}>🔥</span>
        <span style={styles.bigNumber}>{seed.insights.streak}</span>
        <span style={styles.meta}>day micro streak</span>
      </div>
    </Card>
  );
}

function NextMicroTask({ seed }) {
  const t = seed.insights.next_task;
  return (
    <Card title="Next micro-task">
      <div style={styles.taskBox}>
        <div style={styles.taskSkill}>{t.skill}</div>
        <div style={styles.taskConcept}>{t.concept}</div>
        <div style={styles.meta}>~{t.est_minutes} min · single concept</div>
        <button style={styles.primaryBtn}>Start now</button>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// SHARED: skill radar + mastery heatmap (granularity/timescale from levels.js)
// ---------------------------------------------------------------------------

function SkillRadar({ seed, level }) {
  const radar = seed.radar;
  const granularity = RADAR_GRANULARITY[level];
  return (
    <Card title={`Skill radar — ${granularity === 'atomic_skills' ? 'atomic skills' : 'competency clusters'}`} wide>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <RadarPoly nodes={radar.nodes} color={levelAccent[level]} />
        <div style={{ flex: 1, minWidth: 200 }}>
          {radar.nodes.map(node => (
            <div key={node.id} style={styles.legendRow}>
              <span style={styles.legendLabel}>{node.label}</span>
              {node.members && <span style={styles.meta}> ({node.members.length} skills)</span>}
              <span style={{ ...styles.legendState, color: node.mastered ? '#4CAF50' : '#FF9800' }}>
                {node.mastered ? 'mastered' : 'in progress'}
              </span>
            </div>
          ))}
          <div style={styles.meta}>threshold {radar.threshold} · from LL-09b radar_update</div>
        </div>
      </div>
    </Card>
  );
}

function MasteryHeatmap({ seed, level }) {
  const { scale, labels, values } = seed.heatmap;
  const accent = levelAccent[level];
  return (
    <Card title={`Mastery heatmap — by ${scale.replace(/s$/, '') === 'day' ? 'day' : scale.replace(/s$/, '') === 'week' ? 'week' : 'semester'}`} wide>
      <div style={styles.heatGrid}>
        {values.map((v, i) => (
          <div
            key={i}
            title={`${labels[i]}: ${(v * 100).toFixed(0)}%`}
            style={{
              ...styles.heatCell,
              background: hexMix('#EEEEEE', accent, v),
            }}
          >
            <span style={styles.heatLabel}>{labels[i]}</span>
          </div>
        ))}
      </div>
      <div style={styles.heatLegend}>
        <span>low</span>
        {[0.15, 0.35, 0.55, 0.75, 0.95].map(v => (
          <span key={v} style={{ ...styles.heatSwatch, background: hexMix('#EEEEEE', accent, v) }} />
        ))}
        <span>high · time-scale per level: days (micro) → weeks (certificate) → semesters (degree)</span>
      </div>
    </Card>
  );
}

function hexMix(a, b, t) {
  const p = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const [r1, g1, b1] = p(a), [r2, g2, b2] = p(b);
  const m = (x, y) => Math.round(x + (y - x) * t).toString(16).padStart(2, '0');
  return `#${m(r1, r2)}${m(g1, g2)}${m(b1, b2)}`;
}

// ---------------------------------------------------------------------------
// TRANSCRIPT EXPORT (degree pathways)
// ---------------------------------------------------------------------------

function TranscriptExport({ pathway }) {
  const [busy, setBusy] = useState(null);
  const [msg, setMsg] = useState(null);
  const id = String(pathway.id || '');
  const isReal = id && !id.startsWith('seed-');

  const exportJson = () => {
    setBusy('json');
    try {
      const doc = buildTranscriptDocument({
        pathway,
        transcript: pathway.transcript || null,
        levelRows: pathway.level_metadata ? [pathway.level_metadata] : null,
      });
      downloadTranscriptJson(doc);
      setMsg('JSON transcript downloaded.');
    } catch (err) {
      setMsg(`Export failed: ${err.message}`);
    } finally {
      setBusy(null);
    }
  };

  const exportPdf = async () => {
    if (!isReal) {
      setMsg('PDF export needs the server (seed demo — use JSON).');
      return;
    }
    setBusy('pdf');
    try {
      const res = await fetch(`/api/export/transcript/${id}.pdf`, { headers: HEADERS });
      if (!res.ok) throw new Error(`server error ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `transcript-${pathway.level}-${id}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMsg('PDF transcript downloaded.');
    } catch (err) {
      setMsg(`PDF export failed: ${err.message}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card title="Transcript export" wide>
      <div style={styles.exportRow}>
        <button style={styles.primaryBtn} onClick={exportJson} disabled={busy === 'json'}>
          {busy === 'json' ? 'Building…' : 'Download JSON'}
        </button>
        <button style={styles.secondaryBtn} onClick={exportPdf} disabled={busy === 'pdf'}>
          {busy === 'pdf' ? 'Rendering…' : 'Download PDF'}
        </button>
        <span style={styles.meta}>
          {DEGREE_LEVELS.includes(pathway.level)
            ? 'Degree pathway — full credit/GPA transcript from user_transcript'
            : 'Badge pathway — records only, no credits'}
        </span>
      </div>
      {msg && <div style={styles.exportMsg}>{msg}</div>}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// CERTIFICATE widgets
// ---------------------------------------------------------------------------

function ProjectTimeline({ seed }) {
  return (
    <Card title="Project timeline" wide>
      <div style={styles.timeline}>
        {seed.insights.timeline.map(item => (
          <div key={item.id} style={styles.timelineItem}>
            <div style={{
              ...styles.timelineDot,
              background: item.state === 'done' ? '#4CAF50' : item.state === 'active' ? '#FF9800' : '#BDBDBD',
            }} />
            <div>
              <div style={styles.timelineLabel}>{item.label}</div>
              <div style={styles.meta}>week {item.week} · {item.state}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function PortfolioGallery({ seed }) {
  return (
    <Card title="Portfolio gallery">
      <div style={styles.gallery}>
        {seed.insights.portfolio.map(item => (
          <div key={item.id} style={styles.galleryTile}>
            <span style={{ fontSize: 26 }}>{item.thumb}</span>
            <span style={styles.galleryTitle}>{item.title}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function PeerFeedbackWall({ seed }) {
  return (
    <Card title="Peer feedback wall">
      {seed.insights.peer_feedback.map(f => (
        <div key={f.id} style={styles.feedbackItem}>
          <div style={styles.feedbackAuthor}>{f.author}</div>
          <div style={styles.feedbackText}>“{f.text}”</div>
        </div>
      ))}
    </Card>
  );
}

function CompletionPct({ seed }) {
  return (
    <Card title="Completion">
      <div style={styles.centerBlock}>
        <Ring pct={seed.insights.completion_pct} color={levelAccent.certificate} />
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// UNDERGRAD widgets
// ---------------------------------------------------------------------------

function GpaTrend({ seed }) {
  const pts = seed.insights.gpa_trend;
  const w = 260, h = 110, pad = 18;
  const lo = 3.0, hi = 4.0;
  const X = i => pad + (i * (w - pad * 2)) / (pts.length - 1);
  const Y = g => h - pad - ((g - lo) / (hi - lo)) * (h - pad * 2);
  return (
    <Card title="Semester GPA trend" wide>
      <svg width={w} height={h} style={{ maxWidth: '100%' }}>
        <line x1={pad} y1={Y(3.5)} x2={w - pad} y2={Y(3.5)} stroke="#E0E0E0" strokeDasharray="4 4" />
        <polyline points={pts.map((p, i) => `${X(i)},${Y(p.gpa)}`).join(' ')}
          fill="none" stroke={levelAccent.undergrad} strokeWidth="2.5" />
        {pts.map((p, i) => (
          <g key={p.term}>
            <circle cx={X(i)} cy={Y(p.gpa)} r="4" fill={levelAccent.undergrad} />
            <text x={X(i)} y={h - 3} fontSize="9" fill="#666" textAnchor="middle">{p.term}</text>
            <text x={X(i)} y={Y(p.gpa) - 8} fontSize="9" fill="#333" textAnchor="middle">{p.gpa.toFixed(2)}</text>
          </g>
        ))}
      </svg>
    </Card>
  );
}

function CreditProgress({ seed }) {
  const { earned, required } = seed.insights.credits;
  return (
    <Card title="Credit progress">
      <div style={styles.barTrack}>
        <div style={{ ...styles.barFill, width: `${(earned / required) * 100}%`, background: levelAccent.undergrad }} />
      </div>
      <div style={styles.meta}>{earned} / {required} credit hours ({Math.round((earned / required) * 100)}%)</div>
    </Card>
  );
}

function DegreeAudit({ seed }) {
  return (
    <Card title="Degree audit checklist">
      {seed.insights.audit.map(req => (
        <div key={req.req} style={styles.auditRow}>
          <span style={{ color: req.done ? '#4CAF50' : req.progress ? '#FF9800' : '#BDBDBD' }}>
            {req.done ? '☑' : req.progress ? '◐' : '☐'}
          </span>
          <span style={styles.auditLabel}>{req.req}</span>
          {req.progress != null && !req.done && (
            <span style={{ ...styles.miniBar }}>
              <span style={{ ...styles.miniFill, width: `${req.progress * 100}%` }} />
            </span>
          )}
        </div>
      ))}
    </Card>
  );
}

function ExamCalendar({ seed }) {
  return (
    <Card title="Exam calendar">
      {seed.insights.exams.map(e => (
        <div key={e.course} style={styles.examRow}>
          <div style={styles.examDate}>
            {new Date(e.when).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
          </div>
          <div style={{ flex: 1 }}>
            <div style={styles.examCourse}>{e.course}</div>
            <div style={styles.meta}>readiness {Math.round(e.conf * 100)}%</div>
          </div>
        </div>
      ))}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// MASTERS widgets
// ---------------------------------------------------------------------------

function MilestoneTracker({ seed }) {
  return (
    <Card title="Research milestone tracker" wide>
      {seed.insights.milestones.map(m => (
        <div key={m.label} style={styles.milestoneRow}>
          <span style={{
            ...styles.stateChip,
            background: m.state === 'done' ? '#E8F5E9' : m.state === 'active' ? '#FFF3E0' : '#F5F5F5',
            color: m.state === 'done' ? '#2E7D32' : m.state === 'active' ? '#E65100' : '#757575',
          }}>{m.state}</span>
          <span style={{ flex: 1 }}>{m.label}</span>
          <span style={styles.meta}>{new Date(m.date).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}</span>
        </div>
      ))}
    </Card>
  );
}

function LiteratureMap({ seed }) {
  return (
    <Card title="Literature coverage map">
      {seed.insights.literature.map(area => (
        <div key={area.area} style={{ marginBottom: 10 }}>
          <div style={styles.legendRow}>
            <span style={styles.legendLabel}>{area.area}</span>
            <span style={styles.meta}>{Math.round(area.coverage * 100)}%</span>
          </div>
          <div style={styles.barTrack}>
            <div style={{ ...styles.barFill, width: `${area.coverage * 100}%`, background: levelAccent.masters }} />
          </div>
        </div>
      ))}
    </Card>
  );
}

function ThesisChapters({ seed }) {
  const statusColor = { final: '#4CAF50', review: '#FF9800', draft: '#2196F3', outline: '#9E9E9E' };
  return (
    <Card title="Thesis chapter status">
      {seed.insights.thesis_chapters.map(ch => (
        <div key={ch.n} style={styles.chapterRow}>
          <span style={styles.chapterNum}>Ch {ch.n}</span>
          <span style={{ flex: 1 }}>{ch.title}</span>
          <span style={{ ...styles.stateChip, background: statusColor[ch.status], color: '#fff' }}>{ch.status}</span>
        </div>
      ))}
    </Card>
  );
}

function PublicationCount({ seed }) {
  const p = seed.insights.publications;
  return (
    <Card title="Publications">
      <div style={styles.statRow}>
        {[['Submitted', p.submitted], ['Accepted', p.accepted], ['Workshops', p.workshops]].map(([label, n]) => (
          <div key={label} style={styles.statBox}>
            <div style={styles.bigNumber}>{n}</div>
            <div style={styles.meta}>{label}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// PHD widgets
// ---------------------------------------------------------------------------

function DissertationChapters({ seed }) {
  return (
    <Card title="Dissertation progress by chapter" wide>
      {seed.insights.chapters.map(ch => (
        <div key={ch.n} style={{ marginBottom: 10 }}>
          <div style={styles.legendRow}>
            <span style={styles.legendLabel}>Ch {ch.n} · {ch.title}</span>
            <span style={styles.meta}>{ch.pct}%</span>
          </div>
          <div style={styles.barTrack}>
            <div style={{ ...styles.barFill, width: `${ch.pct}%`, background: levelAccent.phd }} />
          </div>
        </div>
      ))}
    </Card>
  );
}

function CitationNetwork({ seed }) {
  // decorative force-graph summary; live data comes from the citation service
  const { nodes, edges, orphans } = seed.insights.citations;
  return (
    <Card title="Citation network">
      <div style={styles.statRow}>
        {[['Nodes', nodes], ['Edges', edges], ['Orphans', orphans]].map(([label, n]) => (
          <div key={label} style={styles.statBox}>
            <div style={styles.bigNumber}>{n}</div>
            <div style={styles.meta}>{label}</div>
          </div>
        ))}
      </div>
      <div style={styles.meta}>clusters by competency family — click a node in the full graph view</div>
    </Card>
  );
}

function ConferenceTimeline({ seed }) {
  return (
    <Card title="Conference timeline">
      {seed.insights.conferences.map(c => (
        <div key={c.name} style={styles.examRow}>
          <div style={styles.examDate}>
            {new Date(c.deadline).toLocaleDateString(undefined, { month: 'short', year: '2-digit' })}
          </div>
          <div style={{ flex: 1 }}>
            <div style={styles.examCourse}>{c.name}</div>
            <div style={styles.meta}>{c.status}</div>
          </div>
        </div>
      ))}
    </Card>
  );
}

function AdvisorMeetingLog({ seed }) {
  return (
    <Card title="Advisor meeting log">
      {seed.insights.advisor_meetings.map(m => (
        <div key={m.when} style={styles.feedbackItem}>
          <div style={styles.feedbackAuthor}>
            {new Date(m.when).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
          </div>
          <div style={styles.feedbackText}>{m.notes}</div>
        </div>
      ))}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// MBA widgets
// ---------------------------------------------------------------------------

function CaseMatrix({ seed }) {
  const { domains, scores } = seed.insights.cases;
  return (
    <Card title="Case study performance matrix" wide>
      <div style={styles.matrix}>
        <div style={styles.matrixRow}>
          <span style={styles.matrixHead} />
          {domains.map(d => <span key={d} style={styles.matrixHead}>{d}</span>)}
        </div>
        {scores.map(row => (
          <div key={row.student} style={styles.matrixRow}>
            <span style={styles.matrixRowLabel}>{row.student}</span>
            {row.row.map((v, i) => (
              <span key={i} style={{ ...styles.matrixCell, background: hexMix('#EEEEEE', levelAccent.mba, (v - 3) / 1.2) }}>
                {v.toFixed(1)}
              </span>
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}

function CohortRanking({ seed }) {
  const { percentile, size } = seed.insights.cohort_ranking;
  return (
    <Card title="Cohort ranking">
      <div style={styles.centerBlock}>
        <Ring pct={percentile} color={levelAccent.mba} label="percentile" />
        <div style={styles.meta}>of {size} cohort members</div>
      </div>
    </Card>
  );
}

function LeadershipRadar({ seed }) {
  return (
    <Card title="Leadership competency radar">
      <div style={styles.centerBlock}>
        <RadarPoly nodes={seed.insights.competencies.map(c => ({ label: c.label.split(' ')[0], mastery: c.score }))}
          color={levelAccent.mba} size={200} />
      </div>
    </Card>
  );
}

function CapstoneIntegrator({ seed }) {
  const c = seed.insights.capstone;
  return (
    <Card title="Capstone integrator">
      <div style={styles.meta}>{c.phase}</div>
      <div style={{ marginTop: 8 }}>
        {Array.from({ length: c.gates_total }, (_, i) => (
          <span key={i} style={{
            display: 'inline-block', width: 12, height: 12, marginRight: 6, borderRadius: 6,
            background: i < c.gates_passed ? levelAccent.mba : '#E0E0E0',
          }} />
        ))}
      </div>
      <div style={styles.meta}>{c.stakeholders} stakeholders · {c.gates_passed}/{c.gates_total} integration gates passed</div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// styles (TrackDashboard.jsx convention: plain object styles)
// ---------------------------------------------------------------------------

const styles = {
  container: { padding: 24, maxWidth: 1200, margin: '0 auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' },
  loading: { textAlign: 'center', padding: 60, fontSize: 18, color: '#666' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap', marginBottom: 16 },
  title: { margin: 0, fontSize: 28, fontWeight: 600, color: '#1a1a1a' },
  subtitle: { fontSize: 13, color: '#777', marginTop: 4 },
  levelPills: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  levelPill: { border: '1px solid #DDD', background: '#fff', borderRadius: 16, padding: '6px 12px', fontSize: 12, cursor: 'pointer' },
  errorBanner: { background: '#FFF3E0', color: '#E65100', padding: '10px 14px', borderRadius: 8, fontSize: 13, marginBottom: 16 },
  pedagogyBar: { background: '#F5F3FF', color: '#5B21B6', padding: '8px 14px', borderRadius: 8, fontSize: 12, marginBottom: 16 },
  widgetGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 },
  card: { background: '#fff', border: '1px solid #E0E0E0', borderRadius: 14, padding: 16, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  cardWide: { gridColumn: '1 / -1' },
  cardTitle: { margin: '0 0 12px 0', fontSize: 14, fontWeight: 600, color: '#333' },
  centerBlock: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 },
  ringText: { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' },
  ringValue: { display: 'block', fontSize: 22, fontWeight: 700, color: '#1a1a1a' },
  ringLabel: { display: 'block', fontSize: 10, color: '#999', textTransform: 'uppercase' },
  meta: { fontSize: 11, color: '#888' },
  bigStat: { display: 'flex', alignItems: 'center', gap: 10 },
  bigNumber: { fontSize: 30, fontWeight: 700, color: '#1a1a1a' },
  taskBox: { display: 'flex', flexDirection: 'column', gap: 4 },
  taskSkill: { fontSize: 12, color: '#666' },
  taskConcept: { fontSize: 16, fontWeight: 600, color: '#1a1a1a' },
  primaryBtn: { background: '#1976D2', color: '#fff', border: 'none', padding: '9px 16px', borderRadius: 8, fontSize: 13, cursor: 'pointer', marginTop: 8, alignSelf: 'flex-start' },
  secondaryBtn: { background: '#E0E0E0', color: '#333', border: 'none', padding: '9px 16px', borderRadius: 8, fontSize: 13, cursor: 'pointer', marginTop: 8 },
  legendRow: { display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '3px 0' },
  legendLabel: { color: '#333', fontWeight: 500 },
  legendState: { fontSize: 11, fontWeight: 600 },
  heatGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(58px, 1fr))', gap: 4 },
  heatCell: { height: 44, borderRadius: 6, display: 'flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: 3 },
  heatLabel: { fontSize: 8, color: 'rgba(0,0,0,0.55)' },
  heatLegend: { display: 'flex', alignItems: 'center', gap: 5, marginTop: 10, fontSize: 11, color: '#888' },
  heatSwatch: { width: 14, height: 14, borderRadius: 3, display: 'inline-block' },
  exportRow: { display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' },
  exportMsg: { marginTop: 8, fontSize: 12, color: '#555', background: '#F5F5F5', padding: '6px 10px', borderRadius: 6 },
  timeline: { display: 'flex', gap: 18, overflowX: 'auto', paddingBottom: 4 },
  timelineItem: { display: 'flex', gap: 8, alignItems: 'flex-start', minWidth: 140 },
  timelineDot: { width: 14, height: 14, borderRadius: 7, marginTop: 3 },
  timelineLabel: { fontSize: 13, fontWeight: 500 },
  gallery: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(90px, 1fr))', gap: 8 },
  galleryTile: { background: '#FAFAFA', border: '1px solid #EEE', borderRadius: 8, padding: 10, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 },
  galleryTitle: { fontSize: 10, color: '#555', textAlign: 'center' },
  feedbackItem: { padding: '8px 10px', background: '#FAFAFA', borderRadius: 8, marginBottom: 8 },
  feedbackAuthor: { fontSize: 11, fontWeight: 600, color: '#1976D2' },
  feedbackText: { fontSize: 12.5, color: '#444', fontStyle: 'italic' },
  barTrack: { height: 10, background: '#EEE', borderRadius: 5, overflow: 'hidden', margin: '8px 0' },
  barFill: { height: '100%', borderRadius: 5 },
  auditRow: { display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', fontSize: 13 },
  auditLabel: { flex: 1 },
  miniBar: { width: 60, height: 6, background: '#EEE', borderRadius: 3, display: 'inline-block', overflow: 'hidden' },
  miniFill: { height: '100%', background: '#FF9800', display: 'block' },
  examRow: { display: 'flex', gap: 10, alignItems: 'center', padding: '6px 0' },
  examDate: { width: 46, textAlign: 'center', fontSize: 11, fontWeight: 700, color: '#DC2626', background: '#FEF2F2', borderRadius: 8, padding: '6px 4px' },
  examCourse: { fontSize: 13, fontWeight: 500 },
  milestoneRow: { display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', fontSize: 13 },
  stateChip: { fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 10, textTransform: 'uppercase', letterSpacing: 0.4 },
  chapterRow: { display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', fontSize: 13 },
  chapterNum: { fontSize: 11, color: '#888', width: 38 },
  statRow: { display: 'flex', gap: 16, justifyContent: 'space-around' },
  statBox: { textAlign: 'center' },
  matrix: { display: 'grid', gap: 4 },
  matrixRow: { display: 'grid', gridTemplateColumns: '90px repeat(5, 1fr)', gap: 4, alignItems: 'center' },
  matrixHead: { fontSize: 10, color: '#666', textAlign: 'center' },
  matrixRowLabel: { fontSize: 12, fontWeight: 600 },
  matrixCell: { textAlign: 'center', fontSize: 12, padding: '7px 0', borderRadius: 6 },
};
