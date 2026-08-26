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

export async function fetchStockFromServer() {
  try {
    const response = await fetch('/api/stock?facilityId=1');
    if (!response.ok) throw new Error('Failed to fetch stock');
    const data = await response.json();
    if (data && data.items) {
      await db.transaction('rw', db.stock, async () => {
        // We can either clear and repopulate or just bulkPut to update existing
        // For simplicity, let's clear and insert the truth from server
        await db.stock.clear();
        await db.stock.bulkPut(data.items.map((item: any) => ({
          drugId: item.drugId,
          name: item.name,
          quantity: item.quantity,
          unit: item.unit,
          daysOfCover: item.daysOfCover ?? 999,
          expiryDate: item.expiryDate ?? '2099-01-01',
          status: item.status ?? 'healthy'
        })));
      });
      return true;
    }
  } catch (err) {
    console.error('Failed to sync stock from server:', err);
    return false;
  }
}

