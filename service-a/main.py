import logging
import os

import httpx
from fastapi import FastAPI, HTTPException

from logger import configure_logger

from prometheus_client import Counter, generate_latest
from starlette.responses import Response


app = FastAPI(title="Service A")

logger = configure_logger()

REQUESTS_TOTAL = Counter(
    "service_a_requests_total",
    "Total de requisições recebidas pelo Service A"
)

ERRORS_TOTAL = Counter(
    "service_a_errors_total",
    "Total de erros ocorridos no Service A"
)

SERVICE_B_URL = os.getenv(
    "SERVICE_B_URL",
    "http://localhost:8001"
)


@app.get("/request/{item_id}")
async def make_request(item_id: int):

    REQUESTS_TOTAL.inc()

    logger.info(
        f"Request iniciado para item {item_id}",
        extra={
            "service": "service-a",
            "event": "request_started"
        }
    )

    try:
        async with httpx.AsyncClient() as client:

            logger.info(
                f"Chamando Service B para item {item_id}",
                extra={
                    "service": "service-a",
                    "event": "service_b_request"
                }
            )

            response = await client.get(
                f"{SERVICE_B_URL}/process/{item_id}",
                timeout=5.0
            )

        if response.status_code != 200:

            ERRORS_TOTAL.inc()

            logger.error(
                f"Service B respondeu com status {response.status_code}",
                extra={
                    "service": "service-a",
                    "event": "service_b_error"
                }
            )

            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Service B apresentou uma falha",
                    "service_b_status": response.status_code
                }
            )

        logger.info(
            f"Request finalizado com sucesso para item {item_id}",
            extra={
                "service": "service-a",
                "event": "request_success"
            }
        )

        return {
            "service": "A",
            "status": "success",
            "service_b_response": response.json()
        }

    except httpx.RequestError:

        ERRORS_TOTAL.inc()

        logger.error(
            "Não foi possível comunicar com o Service B",
            extra={
                "service": "service-a",
                "event": "service_b_unavailable"
            }
        )

        raise HTTPException(
            status_code=503,
            detail="Não foi possível comunicar com o Service B"
        )


@app.get("/health")
def health():

    logger.info(
        "Health check realizado",
        extra={
            "service": "service-a",
            "event": "health_check"
        }
    )

    return {
        "service": "A",
        "status": "healthy"
    }

@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain"
    )