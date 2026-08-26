import Dexie, { type Table } from 'dexie';

export interface LocalStock {
  drugId: number;
  name: string;
  quantity: number;
  unit: string;
  daysOfCover: number;
  expiryDate: string;
  status: string;
}

export interface PendingMutation {
  id?: number;
  clientId: string;
  type: 'dispense' | 'receive' | 'adjust';
  facilityId: number;
  drugId: number;
  quantity: number;
  occurredAt: string;
  batchNo?: string;
  synced: boolean;
}

export class PHCDatabase extends Dexie {
  stock!: Table<LocalStock, number>;
  mutations!: Table<PendingMutation, number>;

  constructor() {
    super('PHCDatabase');
    this.version(1).stores({
      stock: 'drugId, name',
      mutations: '++id, synced, type, drugId',
    });
  }
}

export const db = new PHCDatabase();
