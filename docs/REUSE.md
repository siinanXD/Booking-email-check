# Phase 0 – Reuse before Build

Kurze Entscheidungen pro Kernkomponente (Stand: MVP-Start). Bei Abweichung im PR begründen.

| Komponente | Entscheidung | Begründung |
|------------|--------------|------------|
| **Workflow + Checkpointing** | LangGraph (offizielles Muster) + `MemorySaver` im MVP | Zustand, Human-in-the-Loop-Interrupt und Resume sind Kernanforderung; Template-Gerüst, Booking-Nodes Eigenbau. |
| **Atlas / Speicher** | `pymongo` + Collections; Vector Search über Atlas in Schritt 5 | Offizielle Treiber, volle Kontrolle über Indizes und Metadatenfilter; keine Blind-Übernahme eines LangChain-Beispiels. |
| **Entity Resolution** | Eigenbau | Relay-Adressen, mehrdeutige Namen – domänenspezifisch, nicht generisch lösbar. |
| **Klassifikation / Extraktion** | OpenAI Python SDK direkt | Weniger Abstraktions-Overhead als dicke LangChain-Pipeline (SPEC); strukturierte Outputs via Pydantic. |
| **Triage (MVP)** | Regelbasiert | Kosten vor teurem LLM; LLM-Triage optional später. |
| **Observability** | Langfuse SDK | Traces pro Mail/Correlation-ID; PII wird vor dem Senden maskiert. |
| **Ingestion (MVP)** | Programmatisches `IngestionPort` | HTTP/Outlook-Webhook folgt separat; keine FastAPI-Pflicht im MVP. |

## Nicht übernommen

- Vollständiges BMAD-/SuperClaude-Framework (nur Methodik: Spec → Code, kleine Schritte).
- Semantisches Chunking jeder kurzen Mail (SPEC: schlank halten).
