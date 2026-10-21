import logging

from fastapi import FastAPI, HTTPException

from logger import configure_logger

from prometheus_client import Counter, generate_latest
from starlette.responses import Response


app = FastAPI(title="Service B")

logger = configure_logger()

REQUESTS_TOTAL = Counter(
    "service_b_requests_total",
    "Total de requisições recebidas pelo Service B"
)

ERRORS_TOTAL = Counter(
    "service_b_errors_total",
    "Total de erros ocorridos no Service B"
)

failure_mode = False


@app.get("/process/{item_id}")
def process(item_id: int):

    REQUESTS_TOTAL.inc()

    logger.info(
        f"Processamento iniciado para item {item_id}",
        extra={
            "service": "service-b",
            "event": "processing_started"
        }
    )

    if failure_mode:

        ERRORS_TOTAL.inc()
    
        logger.error(
            f"Falha simulada no processamento do item {item_id}",
            extra={
                "service": "service-b",
                "event": "processing_failed"
            }
        )

        raise HTTPException(
            status_code=500,
            detail="Falha simulada no Service B"
        )

    logger.info(
        f"Item {item_id} processado com sucesso",
        extra={
            "service": "service-b",
            "event": "processing_success"
        }
    )

    return {
        "service": "B",
        "item_id": item_id,
        "status": "processed"
    }


@app.post("/admin/failure/on")
def enable_failure():

    global failure_mode

    failure_mode = True

    logger.warning(
        "Modo de falha ativado",
        extra={
            "service": "service-b",
            "event": "failure_mode_enabled"
        }
    )

    return {
        "failure_mode": True,
        "message": "Falha simulada ativada"
    }


@app.post("/admin/failure/off")
def disable_failure():

    global failure_mode

    failure_mode = False

    logger.info(
        "Modo de falha desativado",
        extra={
            "service": "service-b",
            "event": "failure_mode_disabled"
        }
    )

    return {
        "failure_mode": False,
        "message": "Falha simulada desativada"
    }


@app.get("/health")
def health():

    logger.info(
        "Health check realizado",
        extra={
            "service": "service-b",
            "event": "health_check"
        }
    )

    return {
        "service": "B",
        "status": "healthy"
    }

@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain"
    )