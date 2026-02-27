import { useState, useEffect, useMemo } from "react";
import type { HookEntry, FlagName, PropertyName } from "../types";

export interface Filters {
  search: string;
  chains: string[];
  flags: FlagName[];
  properties: PropertyName[];
}

function parseFiltersFromUrl(): Filters {
  const params = new URLSearchParams(window.location.search);
  return {
    search: params.get("search") ?? "",
    chains: params.get("chains")?.split(",").filter(Boolean) ?? [],
    flags: (params.get("flags")?.split(",").filter(Boolean) ?? []) as FlagName[],
    properties: (params.get("properties")?.split(",").filter(Boolean) ?? []) as PropertyName[],
  };
}

function writeFiltersToUrl(filters: Filters) {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.chains.length) params.set("chains", filters.chains.join(","));
  if (filters.flags.length) params.set("flags", filters.flags.join(","));
  if (filters.properties.length) params.set("properties", filters.properties.join(","));
  const qs = params.toString();
  const url = qs ? `?${qs}` : window.location.pathname;
  window.history.replaceState(null, "", url);
}

function matchesFilters(hook: HookEntry, filters: Filters): boolean {
  if (filters.search) {
    const q = filters.search.toLowerCase();
    const name = hook.hook.name.toLowerCase();
    const desc = (hook.hook.description ?? "").toLowerCase();
    if (!name.includes(q) && !desc.includes(q)) return false;
  }

  if (filters.chains.length > 0) {
    if (!filters.chains.includes(hook.hook.chain)) return false;
  }

  if (filters.flags.length > 0) {
    for (const flag of filters.flags) {
      if (!hook.flags[flag]) return false;
    }
  }

  if (filters.properties.length > 0) {
    for (const prop of filters.properties) {
      if (!hook.properties[prop]) return false;
    }
  }

  return true;
}

export function useHooks() {
  const [hooks, setHooks] = useState<HookEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(parseFiltersFromUrl);

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + "hooklist.json")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: HookEntry[]) => {
        setHooks(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    writeFiltersToUrl(filters);
  }, [filters]);

  const availableChains = useMemo(() => {
    const chainSet = new Set(hooks.map((h) => h.hook.chain));
    return [...chainSet].sort();
  }, [hooks]);

  const filtered = useMemo(
    () => hooks.filter((h) => matchesFilters(h, filters)),
    [hooks, filters]
  );

  return {
    hooks: filtered,
    totalCount: hooks.length,
    loading,
    error,
    filters,
    setFilters,
    availableChains,
  };
}
