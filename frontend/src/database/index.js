import SQLiteAdapter from '@nozbe/watermelondb/adapters/sqlite'
import { Database } from '@nozbe/watermelondb'
import { schema } from './schema'
import { models } from './models'

// Local-first SQLite database for the PWA (mk-002 lineage).
// Pathway tables added in LL-09a (learning_pathways, pathway_curriculum,
// level_metadata, user_transcript).

let database = null

export function getDatabase() {
  if (!database) {
    const adapter = new SQLiteAdapter({
      schema,
      dbName: 'makesense',
      jsi: true,
      onSetUpError: (error) => {
        console.error('WatermelonDB setup failed', error)
      },
    })
    database = new Database({
      adapter,
      modelClasses: Object.values(models),
    })
  }
  return database
}

export { schema, models }
