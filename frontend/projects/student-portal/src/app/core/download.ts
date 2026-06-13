/**
 * Save a Blob to disk by clicking a transient object-URL anchor. Used for the
 * planner .ics and revision .csv exports — the bytes come back through
 * HttpClient (so the auth interceptor adds the JWT), then land as a file.
 */
export function saveBlob(blob: Blob, filename: string): void {
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
