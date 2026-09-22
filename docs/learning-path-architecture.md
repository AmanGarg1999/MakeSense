# 🧠 MakeSense Adaptive Learning Path & 3D Skill Tree Architecture

## 1. Architectural Philosophy

MakeSense eliminates the "content dump" paradigm. Rather than forcing the user into static, pre-packaged courses, the platform operates as an **Intelligent AI Mentor**:
1. **Diagnostic Intake**: Evaluates the learner's outcome goals, baseline fluency, daily time budget, preferred modality, and friction points.
2. **Multi-Pathway Synthesis**: Synthesizes 3 distinct curricular trajectories (Fast-Track Pragmatist, Deep Systems Architect, Applied Project-First) with explicit trade-offs.
3. **Living 3D Constellation (Three.js)**: Renders the curriculum as an interactive spatial constellation, visualizing unlocked, active, completed, and remedial nodes.
4. **Just-in-Time (JIT) Generation**: Compiles educational content and quizzes dynamically when a node is unlocked.
5. **Dynamic Graph Evolution**: Re-routes and injects reinforcement nodes based on quiz scores.

---

## 2. 3D Coordinate Space & Graph Topologies

Nodes in MakeSense are mapped into a 3D coordinate space `(x, y, z)` where:
- `y`: Represents vertical progression (Depth / Tier Level from root `y=0` to capstone `y=7.0`).
- `x`: Represents lateral specialization or divergent parallel tracks (e.g. `x=-2.8` for Foundations/Debt vs `x=+2.8` for Compounding/Investing).
- `z`: Represents depth offset and visual curve inflection.

### Visual State Shaders
- **Completed Node**: Emissive emerald (`#10b981`, intensity 0.6) with orbiting gold halo torus (`#f59e0b`).
- **Active / Unlocked Node**: Pulsing cyan beacon (`#06b6d4`, intensity 0.9) with an orthogonal rotating beacon ring.
- **Locked Node**: Semi-transparent slate (`#64748b`, opacity 0.35).
- **Remedial Node**: Amber star (`#f59e0b`, intensity 0.8) dynamically spawned adjacent to the friction milestone.

### Prerequisite Edges
- Edges are rendered using `THREE.QuadraticBezierCurve3` curving gently in the Z-dimension, with line opacity and color reflecting whether the downstream node is unlocked.

---

## 3. Database Schema

The database persistence layer utilizes PostgreSQL 16:

### `learning_paths`
```sql
CREATE TABLE learning_paths (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    user_profile JSONB NOT NULL,
    mentor_notes TEXT,
    status VARCHAR(50) DEFAULT 'in_progress',
    completion_rate INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### `path_nodes`
```sql
CREATE TABLE path_nodes (
    id VARCHAR(64) PRIMARY KEY,
    path_id VARCHAR(64) REFERENCES learning_paths(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    mentor_rationale TEXT,
    status VARCHAR(30) DEFAULT 'locked', -- locked, unlocked, completed
    estimated_time_minutes INT DEFAULT 20,
    difficulty VARCHAR(50) DEFAULT 'beginner',
    prerequisites JSONB DEFAULT '[]'::jsonb,
    coordinates JSONB NOT NULL,          -- {"x": 0.0, "y": 0.0, "z": 0.0}
    order_index INT NOT NULL,
    lesson_id VARCHAR(64) REFERENCES lessons(id),
    quiz_score INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 4. API Specification

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/paths/preview-options` | Accepts diagnostic profile; returns 3 curated pathway options for comparison. |
| `POST` | `/api/paths/curate` | Instantiates chosen pathway, creates DB records, generates root lesson. |
| `GET` | `/api/paths` | Lists recent learning paths with completion rates. |
| `GET` | `/api/paths/{id}` | Fetches full learning path metadata and node list. |
| `POST` | `/api/paths/{id}/nodes/{nodeId}/unlock` | JIT compiles lesson content for an unlocked node if not yet cached. |
| `POST` | `/api/paths/{id}/nodes/{nodeId}/complete` | Submits quiz score, unlocks child nodes, and injects remedial nodes if score < 70%. |

---

## 5. Adaptive Reinforcement Logic

```python
if quiz_score < 70:
    remedial_node = {
        "id": f"node_hint_{uuid.uuid4().hex[:6]}",
        "title": f"💡 Reinforcement: Core Concepts of {target_node['title']}",
        "description": "A targeted coaching review addressing common misconceptions.",
        "mentor_rationale": "Targeted guided walkthrough to resolve conceptual friction.",
        "status": "unlocked",
        "estimated_time_minutes": 8,
        "difficulty": "beginner",
        "prerequisites": [completed_node_id],
        "coordinates": {
            "x": target_node["coordinates"]["x"] + 1.2,
            "y": target_node["coordinates"]["y"] + 0.8,
            "z": target_node["coordinates"]["z"] + 1.0
        }
    }
    nodes.append(remedial_node)
```
