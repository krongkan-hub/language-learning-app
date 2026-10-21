"""Tracing: a turn is one trace, each stage a child span, and the spans land
in PostgreSQL where app/db/analytics.py reads them."""
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app import db, telemetry
from app.db import analytics

# That a turn is one trace with a span per stage is tested where the turn
# lives: dev/tests/test_cli_session.py.


def test_the_postgres_exporter_writes_rows_the_dashboard_reads(tmp_path, monkeypatch):
    monkeypatch.setenv('LANGUAGE_COACH_DB', str(tmp_path / 'spans.db'))
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer('test')
    with tracer.start_as_current_span('turn'):
        with tracer.start_as_current_span('actor', attributes={'llm.model': 'x'}):
            pass

    assert telemetry.PostgresSpanExporter().export(exporter.get_finished_spans()).name == 'SUCCESS'
    with db.init_db() as conn:
        rows = {r['name']: r for r in conn.execute('SELECT * FROM spans')}
        assert rows['actor']['parent_id'] == rows['turn']['span_id']
        assert rows['actor']['attributes'] == {'llm.model': 'x'}
        assert {p['name'] for p in analytics.performance(conn)} == {'turn', 'actor'}


def test_a_failing_export_never_raises(monkeypatch):
    monkeypatch.setattr(db, 'init_db', lambda *a: (_ for _ in ()).throw(RuntimeError('db down')))
    assert telemetry.PostgresSpanExporter().export([]).name == 'FAILURE'
