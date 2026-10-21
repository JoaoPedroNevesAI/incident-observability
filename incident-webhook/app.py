from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any
from datetime import datetime


app = FastAPI(title="Incident Webhook")


class WebhookPayload(BaseModel):
    status: str
    alerts: list[dict[str, Any]]


incidents = []
incident_counter = 0


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "incident-webhook"
    }


@app.post("/webhook")
def receive_alert(payload: WebhookPayload):

    global incident_counter

    for alert in payload.alerts:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        alert_status = alert.get("status")

        # Incidente sendo aberto
        if alert_status == "firing":

            incident_counter += 1

            incident = {
                "id": f"INC-{incident_counter:03d}",
                "alert": labels.get("alertname"),
                "service": labels.get("service"),
                "severity": labels.get("severity"),
                "status": "OPEN",
                "started_at": datetime.now().isoformat(),
                "resolved_at": None,
                "summary": annotations.get("summary"),
                "description": annotations.get("description")
            }

            incidents.append(incident)

            print("\n" + "=" * 60)
            print("🚨 INCIDENTE ABERTO")
            print("=" * 60)
            print(f"ID: {incident['id']}")
            print(f"Alerta: {incident['alert']}")
            print(f"Serviço: {incident['service']}")
            print(f"Severidade: {incident['severity']}")
            print(f"Início: {incident['started_at']}")
            print("=" * 60 + "\n")

        # Incidente sendo resolvido
        elif alert_status == "resolved":

            for incident in reversed(incidents):

                if (
                    incident["alert"] == labels.get("alertname")
                    and incident["status"] == "OPEN"
                ):
                    incident["status"] = "RESOLVED"
                    incident["resolved_at"] = datetime.now().isoformat()

                    print("\n" + "=" * 60)
                    print("✅ INCIDENTE RESOLVIDO")
                    print("=" * 60)
                    print(f"ID: {incident['id']}")
                    print(f"Alerta: {incident['alert']}")
                    print(f"Serviço: {incident['service']}")
                    print(f"Início: {incident['started_at']}")
                    print(f"Fim: {incident['resolved_at']}")
                    print("=" * 60 + "\n")

                    break

    return {
        "status": "received",
        "alerts": len(payload.alerts)
    }


@app.get("/incidents")
def get_incidents():
    return incidents


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):

    for incident in incidents:

        if incident["id"] == incident_id:
            return incident

    return {
        "error": "Incident not found"
    }