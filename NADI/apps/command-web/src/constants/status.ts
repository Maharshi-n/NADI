/**
 * Status thresholds — shared constants.
 * CRITICAL < 15 days, WARNING < 30 days, else healthy.
 * Per CONTEXT.md: "Status thresholds are shared constants, never repeated per component."
 */

export const CRITICAL_DAYS = 15;
export const WARNING_DAYS = 30;

export type Status = 'critical' | 'warning' | 'healthy';

export function getStatus(daysOfCover: number | null | undefined): Status {
  if (daysOfCover == null || daysOfCover < CRITICAL_DAYS) return 'critical';
  if (daysOfCover < WARNING_DAYS) return 'warning';
  return 'healthy';
}

export function getStatusColor(status: Status): string {
  switch (status) {
    case 'critical': return '#ef4444';
    case 'warning': return '#f59e0b';
    case 'healthy': return '#22c55e';
  }
}
