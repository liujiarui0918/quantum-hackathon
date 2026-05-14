import type { PlaygroundScenarioId, PlaygroundScript } from '@/lib/playground-types';
import { SAMPLE_ASSIGNMENT_SCRIPT } from '@/lib/playground-mock/sample';
import { SMALL_KNAPSACK_SCRIPT } from '@/lib/playground-mock/small-knapsack';
import { EXACTLY_ONE_SCRIPT } from '@/lib/playground-mock/exactly-one';

const SCRIPTS: Record<PlaygroundScenarioId, PlaygroundScript> = {
  sample_assignment: SAMPLE_ASSIGNMENT_SCRIPT,
  small_knapsack: SMALL_KNAPSACK_SCRIPT,
  exactly_one: EXACTLY_ONE_SCRIPT,
};

export function selectPlaygroundScript(prompt: string): PlaygroundScript {
  const lower = prompt.toLowerCase();
  if (/knapsack|背包/.test(lower)) return SCRIPTS.small_knapsack;
  if (/exactly|互斥|二选一/.test(lower)) return SCRIPTS.exactly_one;
  return SCRIPTS.sample_assignment;
}

export function listPlaygroundScenarios(): readonly PlaygroundScenarioId[] {
  return Object.keys(SCRIPTS) as readonly PlaygroundScenarioId[];
}
