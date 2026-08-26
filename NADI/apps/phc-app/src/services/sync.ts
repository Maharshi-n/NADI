import { db, type PendingMutation } from '../db/db';

export async function syncMutations() {
  const pending = await db.mutations.where('synced').equals('false').toArray();
  if (pending.length === 0) return { success: true, count: 0 };

  try {
    const response = await fetch('/api/sync', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ mutations: pending })
    });

    if (response.ok) {
      // Mark as synced
      await db.transaction('rw', db.mutations, async () => {
        for (const m of pending) {
          if (m.id) {
            await db.mutations.update(m.id, { synced: true });
          }
        }
      });
      return { success: true, count: pending.length };
    } else {
      console.error('Failed to sync mutations:', await response.text());
      return { success: false, error: 'API Error' };
    }
  } catch (err) {
    console.error('Network error during sync:', err);
    return { success: false, error: 'Network Error' };
  }
}

export async function queueMutation(mutation: Omit<PendingMutation, 'synced'>) {
  await db.mutations.add({ ...mutation, synced: false });
  // Attempt sync immediately, but don't block
  syncMutations().catch(console.error);
}
