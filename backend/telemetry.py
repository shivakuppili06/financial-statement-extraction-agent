"""
telemetry.py
Azure Application Insights & OpenTelemetry integration.
Configures structured logging and metrics tracking for guardrail audits and AI extractions.
"""

import os
import logging

def setup_telemetry():
    logger = logging.getLogger("fin_extract_agent")
    logger.setLevel(logging.INFO)

    # Standard console handler
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s')
    ch.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(ch)

    # Azure Application Insights connection string
    app_insights_key = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING") or os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")

    if app_insights_key:
        try:
            from opencensus.ext.azure.log_exporter import AzureLogHandler
            azure_handler = AzureLogHandler(connection_string=f"InstrumentationKey={app_insights_key}")
            logger.addHandler(azure_handler)
            logger.info("Successfully initialized Azure Application Insights telemetry logging handler.")
        except Exception as e:
            logger.warning(f"Could not initialize Azure Application Insights log handler: {e}")
    else:
        logger.info("Azure Application Insights connection string not found. Operating with standard structured logger.")

    return logger

app_logger = setup_telemetry()
