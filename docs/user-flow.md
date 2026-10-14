# 🗺️ MakeSense User Flows & Architectural Lifecycles

This document details the user journeys, decision matrices, and system interactions within MakeSense, highlighting the **AI Mentor Intake Wizard**, **Multi-Pathway Comparison Engine**, **3D Evolving Skill Galaxy (Three.js)**, and **Adaptive Quiz Reinforcement Loop**.

---

## 1. Diagnostic Intake & Multi-Pathway Selection Flow

Rather than dumping monolithic content upfront, MakeSense begins with a 4-step diagnostic conversation. The AI Mentor profiles the learner and generates 2–3 distinct educational strategies with trade-offs.

```mermaid
sequenceDiagram
    autonumber
    actor Learner
    participant UI as MakeSense Frontend (React 19)
    participant API as FastAPI Gateway (/api/paths)
    participant Mentor as AI Mentor & Path Generator
    participant DB as PostgreSQL 16

    Learner->>UI: Clicks "Curate 3D Path"
    UI->>Learner: Step 1: Target Skill & Learner Name
    Learner->>UI: Submits Topic (e.g., "System Design")
    UI->>Learner: Step 2: Desired Outcome & Baseline Experience
    Learner->>UI: Selects Goal (Career) & Level (Intermediate)
    UI->>Learner: Step 3: Commitment, Modality & Friction Points
    Learner->>UI: Selects 20m Focus, Hands-on, flags "Concurrency Deadlocks"
    Learner->>UI: Clicks "Analyze My Pathways"
    
    UI->>API: POST /api/paths/preview-options (Diagnostic Payload)
    API->>Mentor: generate_pathway_options(topic, category, profile)
    Mentor-->>API: Returns 3 Tailored Tracks (Fast-Track, Architect, Project Builder)
    API-->>UI: 200 OK with Pathway Array & Milestone Breakdowns

    UI->>Learner: Step 4: Presents 3 Comparison Cards
    Note over UI,Learner: Learner toggles between pathways to inspect philosophy, duration & milestones
    Learner->>UI: Chooses "🏛️ Deep Systems Architect" & clicks "Embark on This Path"
    
    UI->>API: POST /api/paths/curate (track_type: "deep_foundation")
    API->>Mentor: curate_learning_path(..., track_type="deep_foundation")
    API->>DB: Persists Learning Path Record & 3D Node DAG
    API->>Mentor: Just-in-Time generates Root Node 0 Lesson
    API->>DB: Stores Lesson & Quiz
    API-->>UI: 201 Created with Graph Data & Root Lesson ID
    UI->>Learner: Smooth transition into 3D Galaxy View (/path/:pathId)
```

---

## 2. 3D Constellation Navigation & Just-in-Time Generation

Learners explore their personalized curriculum as an interactive Three.js 3D constellation. Subsequent lessons are not pre-baked; they are compiled **just-in-time** when the learner enters the node.

```mermaid
flowchart TD
    A[Learner Lands on 3D Orbit View] --> B[Three.js Renders Starfield & Node Graph]
    B --> C{Learner Interacts with Graph}
    
    C -->|Mouse Drag / Wheel| D[Smooth Orbit & Zoom Controls]
    C -->|Hover Node| E[Raycaster Highlights Node + Shows Floating Tooltip]
    C -->|Click Node| F[Camera Fly-to + Opens Mentor Guidance Drawer]
    
    F --> G{Is Node Unlocked?}
    G -->|🔒 Locked| H[Drawer displays required prerequisite nodes]
    G -->|✓ Completed| I[Button: Review Lesson & Quiz]
    G -->|⚡ Ready to Study| J[Button: Start Milestone Lesson]
    
    J --> K{Has Lesson Been Generated?}
    K -->|Yes| L[Navigate to /lesson/:lessonId]
    K -->|No| M[Call POST /api/paths/:id/nodes/:nodeId/unlock]
    M --> N[AI Content Engine Synthesizes Lesson, Examples & Quiz]
    N --> O[Persist in PostgreSQL]
    O --> L
```

---

## 3. Quiz Evaluation & Adaptive Path Evolution Loop

When a learner finishes a lesson, they take an active-recall quiz. The system evaluates mastery and **dynamically mutates the 3D graph**.

```mermaid
sequenceDiagram
    autonumber
    actor Learner
    participant QuizUI as Quiz Interface (/quiz/:lessonId)
    participant API as FastAPI Server
    participant Skills as Bayesian Skill Rating Engine
    participant PathEng as Adaptive Path Evolution Engine
    participant DB as PostgreSQL 16

    Learner->>QuizUI: Submits Answers (MCQ + Short Answer)
    QuizUI->>API: POST /api/quiz/submit
    API->>API: Server-side grading & points calculation
    API->>Skills: Update User Skill Proficiency Rating
    API-->>QuizUI: Return Results (Score, Feedback, XP Awarded)

    QuizUI->>API: POST /api/paths/:pathId/nodes/:nodeId/complete (quiz_score)
    API->>PathEng: evaluate_and_evolve_path(nodes, nodeId, quiz_score)
    
    alt Quiz Score >= 70% (Mastery Demonstrated)
        PathEng->>PathEng: Mark Current Node as Completed
        PathEng->>PathEng: Evaluate Downstream Dependencies
        PathEng->>PathEng: Unlock Downstream Milestone Nodes
    else Quiz Score < 70% (Conceptual Friction Detected)
        PathEng->>PathEng: Mark Current Node Completed
        PathEng->>PathEng: Synthesize Targeted Reinforcement Node
        PathEng->>PathEng: Inject Reinforcement Node into 3D Coordinates near Current Node
        PathEng->>PathEng: Unlock Reinforcement Node for Guided Walkthrough
    end

    PathEng->>DB: Update Node States & Path Completion %
    PathEng-->>QuizUI: Return Evolved Graph (Unlocked & Remedial Nodes)
    QuizUI->>Learner: Displays Mastery Banner + Link to return to Evolved 3D Skill Tree
```

---

## 4. Complete System Architecture & Data Flow

```mermaid
graph TB
    subgraph Client["Frontend Client (React 19 + Three.js)"]
        WIZ["Mentor Profiling Wizard (4 Steps)"]
        T3D["Three.js 3D Constellation (OrbitControls, Raycaster)"]
        DRAWER["Mentor Guidance & Milestone Inspector"]
        LESSON["Interactive Lesson Viewer (Markdown + Code)"]
        QUIZ["Knowledge Check & Score Evaluator"]
        DASH["Gamification Dashboard (XP, Streaks, Skills)"]
    end

    subgraph Gateway["FastAPI Server (:8000)"]
        RP["/api/paths Router"]
        RC["/api/content Router"]
        RQ["/api/quiz Router"]
        RG["/api/users Gamification Router"]
    end

    subgraph CoreEngine["MakeSense Intelligent Core"]
        MP["Multi-Pathway Generator (Fast-Track, Architect, Project)"]
        AP["Adaptive Path Evolution Engine (Branching & Remedials)"]
        CG["RunAnywhere Local LLM / Gemini Fallback Content Generator"]
        BE["Bayesian Skill Rating & Points Engine"]
    end

    subgraph Storage["Persistence Layer (PostgreSQL 16)"]
        T_PATHS[("learning_paths")]
        T_NODES[("path_nodes")]
        T_LESSONS[("lessons")]
        T_USERS[("users & skill_ratings")]
    end

    WIZ -->|1. Diagnostic Profile| RP
    RP -->|2. Synthesize Options| MP
    MP -->|3. Return Pathways| RP
    RP -->|4. Curate Selected Track| T_PATHS
    RP -->|5. Store Nodes & Edges| T_NODES
    T3D <-->|Fetch Graph State| RP
    DRAWER -->|Unlock Node| RP
    RP -->|Generate Milestone| CG
    CG -->|Save Lesson| T_LESSONS
    LESSON <-->|Read Content| RC
    QUIZ -->|Submit Answers| RQ
    RQ -->|Update Ratings| BE
    BE --> T_USERS
    QUIZ -->|Evolve Path| RP
    RP -->|Mutate DAG| AP
    AP --> T_NODES
```
