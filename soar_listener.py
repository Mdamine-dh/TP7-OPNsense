import ipaddress
import logging
import os
import threading
from typing import Optional

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

load_dotenv()

OPNSENSE_HOST = (os.getenv("OPNSENSE_HOST") or "").rstrip("/")
API_KEY = os.getenv("OPNSENSE_KEY") or os.getenv("API_KEY") or ""
API_SECRET = os.getenv("OPNSENSE_SECRET") or os.getenv("API_SECRET") or ""
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() in {"1", "true", "yes"}
BLOCKLIST_ALIAS = os.getenv("SOAR_ALIAS", "soar_blocklist")
BLOCK_DURATION_SECONDS = int(os.getenv("SOAR_BLOCK_SECONDS", "3600"))
WHITELIST = {
    ipaddress.ip_address(value.strip())
    for value in os.getenv("SOAR_WHITELIST", "127.0.0.1,::1,192.168.50.1").split(",")
    if value.strip()
}

logging.basicConfig(
    filename="soar_actions.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("soar")
app = FastAPI(title="SOAR Listener")
_timers: dict[str, threading.Timer] = {}
_timers_lock = threading.Lock()


class Alert(BaseModel):
    source_ip: str = Field(description="Adresse IP source détectée")
    severity: str = "low"
    type: Optional[str] = None

    @field_validator("source_ip")
    @classmethod
    def validate_source_ip(cls, value: str) -> str:
        try:
            return str(ipaddress.ip_address(value))
        except ValueError as error:
            raise ValueError("source_ip doit être une adresse IPv4 ou IPv6 valide") from error

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        return value.strip().lower()


def _api_post(action: str, ip: str) -> None:
    if not OPNSENSE_HOST or not API_KEY or not API_SECRET:
        raise RuntimeError("OPNSENSE_HOST et les identifiants API doivent être définis dans .env")
    url = f"{OPNSENSE_HOST}/api/firewall/alias_util/{action}/{BLOCKLIST_ALIAS}"
    response = requests.post(
        url,
        json={"address": ip},
        auth=(API_KEY, API_SECRET),
        verify=VERIFY_SSL,
        timeout=15,
    )
    response.raise_for_status()


def _expire_block(ip: str) -> None:
    try:
        _api_post("delete", ip)
        logger.info("Décision=UNBLOCK ip=%s alias=%s motif=expiration durée_s=%d", ip, BLOCKLIST_ALIAS, BLOCK_DURATION_SECONDS)
    except (requests.RequestException, RuntimeError):
        logger.exception("Décision=UNBLOCK_FAILED ip=%s alias=%s", ip, BLOCKLIST_ALIAS)
    finally:
        with _timers_lock:
            _timers.pop(ip, None)


def block_ip(ip: str) -> str:
    """Ajoute l'IP à l'alias puis planifie sa suppression automatique."""
    parsed_ip = ipaddress.ip_address(ip)
    if parsed_ip in WHITELIST:
        logger.warning("Décision=WHITELIST ip=%s alias=%s", parsed_ip, BLOCKLIST_ALIAS)
        return "whitelisted"
    if BLOCK_DURATION_SECONDS <= 0:
        raise RuntimeError("SOAR_BLOCK_SECONDS doit être supérieur à zéro")

    _api_post("add", str(parsed_ip))
    with _timers_lock:
        previous = _timers.pop(str(parsed_ip), None)
        if previous:
            previous.cancel()
        timer = threading.Timer(BLOCK_DURATION_SECONDS, _expire_block, args=(str(parsed_ip),))
        timer.daemon = True
        _timers[str(parsed_ip)] = timer
        timer.start()
    logger.info(
        "Décision=BLOCK ip=%s alias=%s durée_s=%d",
        parsed_ip,
        BLOCKLIST_ALIAS,
        BLOCK_DURATION_SECONDS,
    )
    return "blocked"


@app.get("/health")
def health():
    return {"status": "ok", "service": "soar_listener"}


@app.post("/webhook/alert")
def receive_alert(alert: Alert):
    logger.info("Alerte reçue ip=%s severity=%s type=%s", alert.source_ip, alert.severity, alert.type or "unknown")
    if alert.severity not in {"high", "critical"}:
        logger.info("Décision=IGNORE ip=%s severity=%s", alert.source_ip, alert.severity)
        return {"status": "ignored", "ip": alert.source_ip}

    try:
        result = block_ip(alert.source_ip)
    except (requests.RequestException, RuntimeError) as error:
        logger.exception("Décision=BLOCK_FAILED ip=%s severity=%s", alert.source_ip, alert.severity)
        raise HTTPException(status_code=502, detail="Échec de l'action OPNsense ; consulter soar_actions.log") from error

    if result == "whitelisted":
        return {"status": "whitelisted", "ip": alert.source_ip}
    return {"status": "blocked", "ip": alert.source_ip, "duration_seconds": BLOCK_DURATION_SECONDS}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
