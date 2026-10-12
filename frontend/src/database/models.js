import { Model } from '@nozbe/watermelondb'

// WatermelonDB models for the LL-09a pathway tables. Table + column names
// mirror frontend/src/database/schema.js; keep the `level` field values within
// PATHWAY_LEVELS from ./levels.js.

export class LearningPathwayModel extends Model {
  static table = 'learning_pathways'
  static associations = {
    pathway_curriculum: { type: 'has_many', foreignKey: 'pathwayId' },
    user_transcript: { type: 'has_many', foreignKey: 'pathwayId' },
  }
}

export class PathwayCurriculumModel extends Model {
  static table = 'pathway_curriculum'
}

export class LevelMetadataModel extends Model {
  static table = 'level_metadata'
}

export class UserTranscriptModel extends Model {
  static table = 'user_transcript'
}

export const models = {
  learning_pathways: LearningPathwayModel,
  pathway_curriculum: PathwayCurriculumModel,
  level_metadata: LevelMetadataModel,
  user_transcript: UserTranscriptModel,
}
