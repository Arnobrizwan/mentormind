/**
 * Save a Blob (or raw text) to disk via a transient object-URL anchor.
 * One place for the download mechanics — revoke timing, anchor lifecycle —
 * so OMR grades, gradebook CSVs, and future exports stay consistent.
 */
export function saveBlob(data: Blob | string, filename: string, type = 'text/csv'): void {
  const blob = typeof data === 'string' ? new Blob([data], { type }) : data;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  // Revoke after a tick so the download has started.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
