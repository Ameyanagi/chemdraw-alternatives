import { getCollection, type CollectionEntry } from 'astro:content';
import catalog from '../data/features.json';
import { href } from './paths';

export type Tool = CollectionEntry<'tools'>['data'];
export type Fixture = 'simple' | 'complex' | 'threed';
export type Feature = Tool['features'][string];

export const { groups, features } = catalog;

import { molecules as details } from './molecules';

export const molecules: { id: Fixture; label: string; detail: string }[] = [
  { id: 'simple', label: 'Caffeine', detail: details.simple },
  { id: 'complex', label: 'Paclitaxel', detail: details.complex },
  { id: 'threed', label: 'Cholesterol in 3D', detail: details.threed },
];

export async function loadTools(): Promise<Tool[]> {
  const entries = await getCollection('tools');
  return entries.map((entry) => entry.data).sort((a, b) => a.rank - b.rank);
}

export const emptyFeature: Feature = { status: 'unknown', evidence: 'none', source: null, note: null };
export const featureOf = (tool: Tool, id: string): Feature => tool.features[id] ?? emptyFeature;

export const markLabels = {
  tested: 'Yes, tested by running it',
  seen: 'Yes, seen in the app',
  docs: 'Yes, according to the manual',
  partial: 'Partly',
  no: 'No',
  unknown: 'Not established',
};

export const markKey = (feature: Feature): keyof typeof markLabels =>
  feature.status === 'yes' ? (feature.evidence === 'tested' ? 'tested' : feature.evidence === 'ui' ? 'seen' : 'docs') : feature.status;

/** The manual page behind a claim, or the tool's general manual when no page was cited. */
export function manualFor(tool: Tool, id: string) {
  const { source } = featureOf(tool, id);
  if (source?.startsWith('http')) return { url: source, exact: true };
  return tool.docs ? { url: tool.docs, exact: false } : null;
}

const zoomData = (image: string, title: string, caption: string, manual?: string | null) => ({
  'data-zoom': href(image), 'data-zoom-title': title, 'data-zoom-caption': caption, ...(manual ? { 'data-zoom-manual': manual } : {}),
});

/** Enlarges a feature screenshot in place. */
export function shotZoom(tool: Tool, id: string) {
  const { shot, status, note } = featureOf(tool, id);
  const name = features.find((feature) => feature.id === id)?.name;
  const caption = `${status === 'partial' ? `Partly: ${note} ` : ''}${shot?.caption} Tested on ${testedVersion(tool)}.`;
  return shot && zoomData(shot.image, `${name} in ${tool.name}`, caption, manualFor(tool, id)?.url);
}

/** A MOL or SDF file carries our coordinates, so the layout shown is not the tool's own. */
export const inputNote = (input: string) => (input === 'smiles' ? 'from SMILES' : `from ${input.toUpperCase()}, so the layout is not its own`);

/** Enlarges a default drawing in place. */
export function drawingZoom(tool: Tool, fixture: Fixture) {
  const capture = captureOf(tool, fixture);
  if (!capture?.image) return undefined;
  const details = [
    testedVersion(tool),
    tool.drawingStyle && `${tool.drawingStyle} style`,
    capture.input && inputNote(capture.input),
    capture.structure && structureNotes[capture.structure],
    capture.result === 'failed' && capture.note,
  ];
  const label = molecules.find((molecule) => molecule.id === fixture)?.label;
  return zoomData(capture.image, `${label} in ${tool.name}`, details.filter(Boolean).join(', '), tool.docs);
}

/** The main canvas in one appearance. Before themes were checked, the plain capture stands in for light. */
export function canvasImage(tool: Tool, mode: 'light' | 'dark') {
  const { canvas, canvasLight, canvasDark, themes } = tool.hands ?? {};
  if (mode === 'dark') return canvasDark ?? null;
  return canvasLight ?? (themes ? null : canvas ?? null);
}

/** Enlarges a main canvas screenshot in place. */
export function canvasZoom(tool: Tool, mode: 'light' | 'dark' = 'light') {
  const image = canvasImage(tool, mode);
  return image ? zoomData(image, `${tool.name} main canvas, ${mode} mode`, `${testedVersion(tool)}, on ${tool.hands?.platform}.`, tool.docs) : undefined;
}

/** Why a tool has no result of ours to show. */
export function notRunReason(tool: Tool) {
  if (tool.hands?.failure && /sign|log.?in|account|regist|purchase/i.test(tool.hands.failure)) return 'Needs an account or a purchase';
  if (tool.hands) return tool.hands.route === 'hosted' ? 'Would not load for us' : 'Would not run on our Mac';
  if (tool.license.kind === 'commercial') return 'Paid, checked from the manual';
  return !tool.platforms.macos && !tool.platforms.web ? `Needs ${platformNames(tool).join(' or ') || 'another system'}` : 'Not run yet';
}

/** Where a mark leads: a hands-on claim opens its screenshot, anything else its manual. */
export function proofOf(tool: Tool, id: string) {
  const { status, evidence, shot } = featureOf(tool, id);
  if (status === 'unknown') return undefined;
  if (shot && ['tested', 'ui'].includes(evidence)) return { href: href(`shots/${tool.slug}/${id}/`), zoom: shotZoom(tool, id) };
  const url = manualFor(tool, id)?.url;
  return url ? { href: url } : undefined;
}

export const coverage = (tool: Tool) =>
  features.filter((feature) => ['yes', 'partial'].includes(featureOf(tool, feature.id).status)).length;

export const captureOf = (tool: Tool, fixture: Fixture) =>
  tool.hands?.captures.find((capture) => capture.fixture === fixture);

export const isTested = (tool: Tool) => tool.hands?.ran === true;

const seenOn = (date: string) =>
  new Date(date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

export const testedVersion = (tool: Tool) =>
  tool.hands?.testedVersion ?? (tool.hands?.ran && tool.hands.route === 'hosted' ? `Hosted, ${seenOn(tool.hands.testedOn)}` : tool.version.name);

export const structureNotes = { match: 'structure verified', stereo: 'stereochemistry changed', mismatch: 'structure changed' } as const;

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return 'Not measured';
  const megabytes = bytes / 1_000_000;
  return megabytes >= 1000 ? `${(megabytes / 1000).toFixed(1)} GB` : `${megabytes.toFixed(megabytes < 10 ? 1 : 0)} MB`;
}

export const downloadSize = (tool: Tool) =>
  tool.perf?.transferBytes ? `${formatBytes(tool.perf.transferBytes)} page` : formatBytes(tool.downloadBytes);

export const installedSize = (tool: Tool) =>
  !tool.hands?.installedBytes && tool.hands?.route === 'hosted' ? 'Runs in the browser' : formatBytes(tool.hands?.installedBytes);

const reliedNames = (tool: Tool) => {
  const { editor, libraries } = tool.builtOn ?? {};
  return [...new Set([editor, ...(libraries ?? [])].filter((name): name is string => Boolean(name)))];
};

/** The projects a tool relies on, stated as fact rather than as a category. */
export function reliesOn(tool: Tool) {
  const { libraries, ported } = tool.builtOn ?? {};
  if (!libraries && !tool.builtOn?.editor) return 'Not established';
  return reliedNames(tool).join(', ') || (ported?.length ? 'None linked' : 'No third-party engine found');
}

export function reliesShort(tool: Tool) {
  const names = reliedNames(tool);
  const ported = tool.builtOn?.ported ?? [];
  if (ported.length) return `Ported from ${ported.slice(0, 3).join(', ')}`;
  return names.length ? `Relies on ${names.slice(0, 3).join(', ')}` : reliesOn(tool);
}

export const relied = (tool: Tool, name: string) => reliedNames(tool).includes(name);

export const rendererFeatures = ['name-to-structure', 'structure-to-name', 'cleanup', 'model-3d', 'nmr-prediction', 'properties', 'formula-mass', 'stereo-perception', 'valence-check', 'image-to-structure', 'database-lookup', 'smiles', 'inchi', 'mol-sdf', 'cdxml', 'cdx'];

export function rendererLabel(tool: Tool) {
  const { origin, name } = tool.renderer ?? {};
  if (!name) return 'Not established';
  return origin ? `${origin === 'original' ? 'Original' : 'Borrowed'}: ${name}` : name;
}

export const mainLanguage = (tool: Tool) => tool.renderer?.language ?? tool.languages[0] ?? 'Not published';

export function otherLanguages(tool: Tool) {
  if (!tool.otherLanguages) return tool.languageNote ?? 'Not established';
  return tool.otherLanguages.map(({ language, role }) => `${language}: ${role}`).join('; ') || 'None';
}

/** Which library powers one feature. Only a feature the tool has can have an answer. */
export function featureEngine(tool: Tool, id: string) {
  const { status, engine } = featureOf(tool, id);
  if (engine) return engine.library;
  if (status === 'no') return 'No such feature';
  if (status === 'unknown') return 'Feature not confirmed';
  return tool.enginesChecked ? 'Library not confirmed' : 'Not checked yet';
}

export const thirdPartySummary = (tool: Tool) => tool.thirdParty.summary ?? 'Not established';

export const thirdPartyLibraries = (tool: Tool) =>
  tool.thirdParty.libraries.map(({ name, license }) => `${name} (${license ?? 'license not established'})`).join(', ') || null;

export const portedLabel = (tool: Tool) =>
  tool.builtOn?.ported?.length ? `Ported into its own code: ${tool.builtOn.ported.join(', ')}` : null;

export function memoryUse(tool: Tool, key: 'idleMb' | 'paclitaxelMb') {
  const memory = tool.hands?.memory;
  if (!memory) return 'Not measured';
  const value = memory[key];
  if (value === null) return memory.note ?? 'Not measured';
  return `${Math.round(value)} MB${memory.baselineMb ? `, of which ${Math.round(memory.baselineMb)} MB is the empty browser` : ''}`;
}

export const licenseShort = (tool: Tool) => tool.license.spdx?.replaceAll(' OR ', ' or ').replaceAll(' AND ', ' and ') ?? tool.license.text;

export const platformNames = (tool: Tool) =>
  ([['macos', 'macOS'], ['windows', 'Windows'], ['linux', 'Linux'], ['web', 'Browser'], ['ios', 'iOS'], ['android', 'Android']] as const)
    .filter(([key]) => tool.platforms[key])
    .map(([, name]) => name);

export const licenseNames: Record<Tool['license']['kind'], string> = {
  'open-source': 'Open source',
  free: 'Free',
  freemium: 'Free with paid plans',
  commercial: 'Paid',
  'source-available': 'Source available',
  unclear: 'License unclear',
};
