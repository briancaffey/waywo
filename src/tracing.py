"""
OpenTelemetry tracing setup for LlamaIndex observability with Arize Phoenix.

This module configures automatic instrumentation of LlamaIndex operations
(LLM calls, embeddings, workflows) and exports traces to Phoenix via OTLP HTTP.
"""

import logging

from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

# Track initialization state
_initialized = False


def init_tracing(service_name: str = "waywo") -> None:
    """
    Initialize OpenTelemetry tracing with Phoenix as the backend.

    This function:
    1. Creates a TracerProvider with the service name
    2. Configures OTLP HTTP exporter pointing to Phoenix
    3. Instruments LlamaIndex for automatic trace capture

    Args:
        service_name: Name to identify this service in traces (e.g., "waywo-backend", "waywo-worker")
    """
    global _initialized

    if _initialized:
        logger.debug("Tracing already initialized, skipping")
        return

    from src.settings import PHOENIX_HOST, PHOENIX_PORT

    # Get Phoenix endpoint from settings
    phoenix_host = PHOENIX_HOST
    phoenix_port = PHOENIX_PORT
    endpoint = f"http://{phoenix_host}:{phoenix_port}/v1/traces"

    logger.info(f"🔭 Initializing OpenTelemetry tracing for '{service_name}'")
    logger.info(f"📡 Phoenix endpoint: {endpoint}")

    try:
        # Create a resource identifying this service
        resource = Resource.create({"service.name": service_name})

        # Create tracer provider
        tracer_provider = trace_sdk.TracerProvider(resource=resource)

        # Configure OTLP HTTP exporter to send traces to Phoenix
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint)

        # Use BatchSpanProcessor for better performance (batches spans before export)
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Set as the global tracer provider - this is critical for context propagation
        trace.set_tracer_provider(tracer_provider)

        # Instrument LlamaIndex - this auto-captures LLM calls, embeddings, etc.
        LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

        _initialized = True
        logger.info("✅ Tracing initialized successfully")
        logger.info(f"🌐 View traces at http://{phoenix_host}:{phoenix_port}")
        print(
            f"🔭 Tracing initialized - sending traces to http://{phoenix_host}:{phoenix_port}"
        )

    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize tracing: {e}")
        logger.warning(
            "Continuing without tracing - LlamaIndex will still work normally"
        )
