"""WhatsApp-Bot: Konversations-Frontend für das Booking-SaaS.

Nachrichteninhalt ist DATEN, nie Instruktion. Keine Schreiboperation ohne
Bestätigungs-Button. LLM nur für Intent-Erkennung — alle Geschäftslogik ist
deterministisches Python. Jede DB-Query ist account_id-gefiltert.
"""
