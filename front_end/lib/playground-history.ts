import type { PlaygroundScenarioId } from '@/lib/playground-types';

export const PLAYGROUND_HISTORY_KEY = 'playground:history:v1';
export const PLAYGROUND_HISTORY_LIMIT = 20;

export type PlaygroundHistoryItem = {
  id: string;
  prompt: string;
  scenario: PlaygroundScenarioId;
  title: string;
  created_at: string;
};

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

export function listPlaygroundHistory(): PlaygroundHistoryItem[] {
  if (!isBrowser()) return [];
  try {
    const raw = window.localStorage.getItem(PLAYGROUND_HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item): item is PlaygroundHistoryItem =>
        item !== null &&
        typeof item === 'object' &&
        typeof item.id === 'string' &&
        typeof item.prompt === 'string' &&
        typeof item.title === 'string' &&
        typeof item.created_at === 'string' &&
        (item.scenario === 'sample_assignment' ||
          item.scenario === 'small_knapsack' ||
          item.scenario === 'exactly_one'),
    );
  } catch {
    return [];
  }
}

export function pushPlaygroundHistory(item: PlaygroundHistoryItem): PlaygroundHistoryItem[] {
  const current = listPlaygroundHistory();
  const next = [item, ...current.filter((existing) => existing.id !== item.id)].slice(
    0,
    PLAYGROUND_HISTORY_LIMIT,
  );
  if (!isBrowser()) return next;
  try {
    window.localStorage.setItem(PLAYGROUND_HISTORY_KEY, JSON.stringify(next));
  } catch {
    // ignore quota / privacy errors
  }
  return next;
}

export function clearPlaygroundHistory(): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.removeItem(PLAYGROUND_HISTORY_KEY);
  } catch {
    // ignore
  }
}
