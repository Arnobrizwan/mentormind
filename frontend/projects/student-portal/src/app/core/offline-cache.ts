const CATALOG_KEY = 'mm_catalog_v1';
const ENROLLMENTS_KEY = 'mm_enrollments_v1';

/** Lightweight offline persistence for read-mostly learning data. */
export function readCatalogCache<T>(): T | null {
  return readJson<T>(CATALOG_KEY);
}

export function writeCatalogCache<T>(data: T): void {
  writeJson(CATALOG_KEY, data);
}

export function readEnrollmentsCache<T>(): T | null {
  return readJson<T>(ENROLLMENTS_KEY);
}

export function writeEnrollmentsCache<T>(data: T): void {
  writeJson(ENROLLMENTS_KEY, data);
}

function readJson<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function writeJson(key: string, data: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch {
    // Storage full or private mode — ignore.
  }
}
