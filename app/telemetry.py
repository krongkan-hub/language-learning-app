"""Tracing with OpenTelemetry: where a turn's 10-20 seconds actually go.

A learner turn is three model calls in a row — judge, actor, coach — and the
only numbers this project had about their cost were one-off hand timings in
comments. Now every turn is a trace:

    turn                    (app/web/turns.py, one per learner message)
      judge / actor / coach (each stage of the turn)
        llm.generate        (app/llm/client.py, every model call)

Spans go to a `spans` table in PostgreSQL (PostgresSpanExporter below), which
the dashboard reads for per-stage p50/p95 (app/db/analytics.py). Set
OTEL_EXPORTER_OTLP_ENDPOINT and install opentelemetry-exporter-otlp to ALSO
ship them to any OTLP backend (Jaeger, Grafana Tempo, Honeycomb...).

Tracing is switched on by setup() — the web server calls it at start-up.
Until then `tracer` is OpenTelemetry's no-op, so tests and scripts that
import the app record nothing and write nothing.
"""
import json
import logging
import os
from typing import Sequence

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor, SpanExporter,
                                            SpanExportResult)

SERVICE = 'language-coach'
tracer = trace.get_tracer(SERVICE)
_log = logging.getLogger(__name__)


class PostgresSpanExporter(SpanExporter):
    """Writes finished spans to the app database's `spans` table."""

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        from . import db
        try:
            with db.init_db() as conn:
                for s in spans:
                    ctx = s.get_span_context()
                    parent = s.parent.span_id if s.parent else None
                    conn.execute(
                        "INSERT INTO spans (trace_id, span_id, parent_id, name, started_at, "
                        " duration_ms, status, attributes) "
                        "VALUES (%s, %s, %s, %s, to_timestamp(%s), %s, %s, %s::jsonb)",
                        (format(ctx.trace_id, '032x'), format(ctx.span_id, '016x'),
                         format(parent, '016x') if parent else None, s.name,
                         s.start_time / 1e9, (s.end_time - s.start_time) / 1e6,
                         s.status.status_code.name,
                         json.dumps(dict(s.attributes or {}), default=str)))
                conn.commit()
            return SpanExportResult.SUCCESS
        except Exception as exc:          # observability must never break a turn
            _log.warning('span export failed: %s', exc)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        pass


def setup() -> None:
    """Install the tracer provider: Postgres always, OTLP when configured."""
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return                                           # already set up
    provider = TracerProvider(resource=Resource.create({'service.name': SERVICE}))
    provider.add_span_processor(BatchSpanProcessor(PostgresSpanExporter()))
    if os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT'):
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except ImportError:
            _log.warning('OTEL_EXPORTER_OTLP_ENDPOINT is set but opentelemetry-exporter-otlp '
                         'is not installed; spans go to PostgreSQL only')
    trace.set_tracer_provider(provider)
