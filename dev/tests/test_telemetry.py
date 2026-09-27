"""Tracing: a turn is one trace, each stage a child span, and the spans land
in PostgreSQL where the dashboard's performance panel reads them."""
import time

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app import db, telemetry, web
from app.db import analytics
from app.web import turns as web_turns

from .test_web import _start, _stop


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('LANGUAGE_COACH_DB', str(tmp_path / 'web.db'))
    web.SESSIONS.clear()
    with TestClient(web.app) as c:
        yield c


@pytest.fixture
def spans(monkeypatch):
    """A private provider — the global one can only be set once per process."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(web_turns, 'tracer', provider.get_tracer('test'))
    yield exporter
    provider.shutdown()


def _finished(exporter, name, n=1):
    for _ in range(300):
        found = [s for s in exporter.get_finished_spans() if s.name == name]
        if len(found) >= n:
            return found
        time.sleep(0.01)
    raise AssertionError(f'no {name!r} span; got {[s.name for s in exporter.get_finished_spans()]}')


def test_a_turn_is_one_trace_with_a_span_per_stage(client, spans):
    sid, sess, patches = _start(client)
    try:
        assert _finished(spans, 'greeting')[0].attributes['coach.language'] == 'English'
        client.post(f'/api/turn/{sid}', json={'text': 'A table for two, please.'})
        turn = _finished(spans, 'turn')[0]
        assert turn.attributes['coach.kind'] == 'scenario'
        assert turn.attributes['coach.scenario'] == sess.scenario.name
        children = {s.name for s in spans.get_finished_spans()
                    if s.parent and s.parent.span_id == turn.context.span_id}
        assert {'judge', 'actor', 'coach'} <= children
    finally:
        _stop(patches)


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
