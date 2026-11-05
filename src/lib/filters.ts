/**
 * Browser logic for the filter bar. Options in one menu widen the results, and different menus narrow them.
 * Has feature is the exception: a tool must have every feature that is ticked, and on a free plan if that is asked for.
 */
export interface FilterState { groups: string[][]; name: string; features: string[]; freeOnly: boolean }

export const isFiltering = ({ groups, name, features }: FilterState) => groups.length > 0 || Boolean(name) || features.length > 0;

export function matches({ groups, name, features, freeOnly }: FilterState, element: HTMLElement) {
  const { tags = '', has = '', free = '', name: toolName = '' } = element.dataset;
  const toolTags = tags.split(' ');
  const toolFeatures = (freeOnly ? free : has).split(' ');
  return groups.every((group) => group.some((tag) => toolTags.includes(tag)))
    && toolName.includes(name)
    && features.every((feature) => toolFeatures.includes(feature));
}

export function wireFilterBar(bar: HTMLElement, onChange: (state: FilterState) => void) {
  const menus = [...bar.querySelectorAll<HTMLDetailsElement>('details')];
  const groups = [...bar.querySelectorAll<HTMLDetailsElement>('[data-group]')];
  const search = bar.querySelector<HTMLInputElement>('[data-filter="name"]');
  const featureMenu = bar.querySelector<HTMLDetailsElement>('[data-features]');
  const tokens = document.querySelector<HTMLElement>('#filter-tokens');
  const clearAll = document.querySelector<HTMLElement>('#filter-clear');
  const freeOnly = bar.querySelector<HTMLInputElement>('[data-filter="free"]');
  const checked = (menu: Element) => [...menu.querySelectorAll<HTMLInputElement>('input[data-filter="option"]:checked')];

  function read(): FilterState {
    return {
      groups: groups.map((menu) => checked(menu).map((input) => input.value)).filter((group) => group.length > 0),
      name: search?.value.trim().toLowerCase() ?? '',
      features: featureMenu ? checked(featureMenu).map((input) => input.value) : [],
      freeOnly: freeOnly?.checked ?? false,
    };
  }

  function token(label: string, remove: () => void) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'token';
    button.textContent = label;
    button.setAttribute('aria-label', `Remove filter: ${label}`);
    button.addEventListener('click', () => { remove(); update(); });
    return button;
  }

  function render(state: FilterState) {
    const counted = featureMenu ? [...groups, featureMenu] : groups;
    for (const menu of counted) {
      const count = checked(menu).length;
      menu.classList.toggle('active', count > 0);
      const badge = menu.querySelector<HTMLElement>('.filter-count');
      if (badge) { badge.hidden = count === 0; badge.textContent = String(count); }
    }
    const chosen = counted.flatMap((menu) => checked(menu)).map((input) =>
      token(input.parentElement?.textContent?.trim() ?? input.value, () => { input.checked = false; }));
    if (state.freeOnly && state.features.length > 0) chosen.push(token('Without paying', () => { if (freeOnly) freeOnly.checked = false; }));
    if (state.name) chosen.push(token(`Name: ${state.name}`, () => { if (search) search.value = ''; }));
    tokens?.replaceChildren(...chosen);
    if (clearAll) clearAll.hidden = !isFiltering(state);
  }

  function update() {
    const state = read();
    render(state);
    onChange(state);
  }

  function clear() {
    bar.querySelectorAll<HTMLInputElement>('input[type="checkbox"][data-filter]').forEach((input) => { input.checked = false; });
    if (search) search.value = '';
    render(read());
  }

  bar.addEventListener('change', (event) => { if (event.target instanceof Element && event.target.matches('[data-filter]')) update(); });
  search?.addEventListener('input', update);
  clearAll?.addEventListener('click', () => { clear(); onChange(read()); });
  for (const menu of menus) {
    menu.addEventListener('toggle', () => { if (menu.open) menus.forEach((other) => { if (other !== menu) other.open = false; }); });
  }
  const closeMenus = () => menus.forEach((menu) => { menu.open = false; });
  document.addEventListener('click', (event) => { if (event.target instanceof Node && !bar.contains(event.target)) closeMenus(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeMenus(); });
  return { clear };
}
