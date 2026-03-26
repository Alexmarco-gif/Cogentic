/**
 * Document export API service.
 *
 * Maps to: backend/api/v1/exports.py
 *
 * Handles generating and downloading DOCX, PPTX, and PDF (via print HTML)
 * documents from brief/signal content.
 */

import { getAccessToken } from './client';

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? '') || '';
const API_PREFIX = '/api/v1';

export interface ExportSection {
  heading: string;
  content: string;
}

export interface BriefExportPayload {
  title: string;
  subtitle?: string;
  domain?: string;
  author?: string;
  confidence?: number;
  sections: ExportSection[];
  format: 'docx' | 'pptx' | 'pdf-html';
}

/**
 * Exports a brief document by posting to the backend and triggering a
 * browser download (for docx/pptx) or opening a print window (for pdf-html).
 */
export async function exportBrief(payload: BriefExportPayload): Promise<void> {
  let token: string | null = null;
  try {
    token = await getAccessToken();
  } catch {
    // Allow unauthenticated in dev
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${API_PREFIX}/exports/brief`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Export failed: ${res.status} ${res.statusText}`);
  }

  if (payload.format === 'pdf-html') {
    // Open the printable HTML in a new window — browser handles print‑to‑PDF
    const html = await res.text();
    const printWindow = window.open('', '_blank', 'width=900,height=700');
    if (printWindow) {
      printWindow.document.write(html);
      printWindow.document.close();
    }
    return;
  }

  // For docx/pptx — trigger a real file download
  const blob = await res.blob();
  const ext = payload.format === 'docx' ? 'docx' : 'pptx';
  const filename =
    payload.title
      .toLowerCase()
      .replace(/[\s/]+/g, '-')
      .replace(/[^a-z0-9-]/g, '')
      .slice(0, 60) + `.${ext}`;

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
