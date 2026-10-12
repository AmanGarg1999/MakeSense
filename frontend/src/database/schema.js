import { appSchema, tableSchema } from '@nozbe/watermelondb'

// Local SQLite schema for multi-level learning pathways (LL-09a).
// Server-of-record tables live in server/migrations/009_learning_pathways.sql;
// column names match so the sync bridge can pass rows through unchanged.
// `updated` is WatermelonDB's sync timestamp column (seconds).
export const schema = appSchema({
  version: 2,
  tables: [
    tableSchema({
      name: 'learning_pathways',
      columns: [
        { name: 'userId', type: 'string', isIndexed: true },
        // micro | certificate | undergrad | masters | phd | mba (see levels.js)
        { name: 'level', type: 'string', isIndexed: true },
        { name: 'title', type: 'string', isOptional: true },
        { name: 'status', type: 'string', isIndexed: true }, // active|paused|completed|archived
        { name: 'startedAt', type: 'number' },
        { name: 'targetCompletion', type: 'number', isOptional: true },
        { name: 'completedAt', type: 'number', isOptional: true },
        { name: 'updatedAt', type: 'number' },
      ],
    }),
    tableSchema({
      name: 'pathway_curriculum',
      columns: [
        { name: 'pathwayId', type: 'string', isIndexed: true },
        { name: 'contentPackId', type: 'string', isIndexed: true },
        { name: 'sequence', type: 'number' },
        { name: 'isRequired', type: 'boolean' },
        { name: 'credits', type: 'number' },
        { name: 'updatedAt', type: 'number' },
      ],
    }),
    tableSchema({
      name: 'level_metadata',
      columns: [
        // primary key is the level string itself (6 seeded rows)
        { name: 'typicalDurationWeeks', type: 'number' },
        { name: 'creditSystem', type: 'string' },
        { name: 'assessmentType', type: 'string' },
        { name: 'mentorModel', type: 'string' },
        { name: 'recapIntervalDays', type: 'number' },
      ],
    }),
    tableSchema({
      name: 'user_transcript',
      columns: [
        { name: 'userId', type: 'string', isIndexed: true },
        { name: 'pathwayId', type: 'string', isIndexed: true },
        { name: 'contentPackId', type: 'string', isIndexed: true },
        { name: 'masteryScore', type: 'number' },
        { name: 'completedAt', type: 'number', isOptional: true },
        { name: 'credentialIssued', type: 'boolean' },
        { name: 'credentialType', type: 'string', isOptional: true },
        { name: 'updatedAt', type: 'number' },
      ],
    }),
  ],
})
