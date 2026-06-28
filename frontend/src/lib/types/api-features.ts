// Typen für die neuen Features (Sammel-Freigabe, DSGVO-Gast).
// Re-exportiert über `api.ts`, damit Importe aus "@/lib/types/api" weiter gehen.

export interface BulkApproveItem {
  correlation_id: string;
  status: string;
  error?: string;
}

export interface BulkApproveResponse {
  approved: number;
  failed: number;
  items: BulkApproveItem[];
}

export interface GuestConsent {
  whatsapp_consent: boolean;
  consent_at: string | null;
}

export interface GuestExportMail {
  correlation_id: string;
  subject: string;
  received_at: string | null;
  intent: string | null;
}

export interface GuestExportResponse {
  guest_id: string;
  email: string;
  consent: GuestConsent;
  mails: GuestExportMail[];
  mail_count: number;
  generated_at: string;
}

export interface GuestDeleteResponse {
  guest_id: string;
  deleted: {
    emails: number;
    extractions: number;
    reviews: number;
    embeddings: number;
    consent: number;
  };
}
