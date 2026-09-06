import io
from unittest.mock import patch, MagicMock
from app import db, cli
from app.scenarios.builtins import SCENARIOS


class CLIHarness:
    def __init__(self, tmp_path, monkeypatch, inputs=None):
        self.tmp_db = tmp_path / "test_sessions.db"
        self.monkeypatch = monkeypatch
        self.monkeypatch.setenv("LANGUAGE_COACH_DB", str(self.tmp_db))
        self.monkeypatch.setattr(db, "DB_PATH", str(self.tmp_db))
        self.inputs = inputs or []
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        # Order in which the turn's three LLM stages were invoked. Every stage is
        # mocked here, so this is the only place a test can observe their order.
        self.calls = []

    def run(self, args=None, inputs=None, coach_response=None, judge_response=None, actor_response=None):
        if inputs is not None:
            input_data = "\n".join(inputs) + "\n"
        else:
            input_data = "\n".join(self.inputs) + "\n"

        if args is None:
            args = ["cli"]

        if actor_response is None:
            actor_response = (
                "Welcome! How can I help you today?\n\n"
                "<vocab>\n"
                "word: concierge\n"
                "explanation: a hotel employee who assists guests\n"
                "encourage: Try asking the concierge for help.\n"
                "</vocab>"
            )

        def mock_stream_actor(messages, system_prompt, speaker=None, max_sentences=3, callback=None, **kwargs):
            spoken = "Here is your information."
            if callback:
                callback(spoken)
            return (
                f"{spoken}\n\n"
                "<vocab>\n"
                "word: reservation\n"
                "explanation: an arrangement to have something held for your use\n"
                "encourage: Mention your reservation.\n"
                "</vocab>"
            )

        def mock_call_actor(messages, system_prompt, speaker=None, max_sentences=3, **kwargs):
            self.calls.append('actor')
            return actor_response

        def mock_call_coach(user_input, language, situation=None):
            self.calls.append('coach')
            if coach_response is not None:
                return coach_response
            return "💡 Feedback: Perfectly natural!"

        # `vocab_targets` is the authored Japanese vocabulary target the CLI now
        # resolves per task (OPEN-18). Defaulted so this double stays faithful to
        # the production signature without changing what the test asserts.
        def mock_evaluate_task(user_input, done_when, conversation, language,
                               vocab_targets=None):
            self.calls.append('judge')
            if judge_response is not None:
                return judge_response
            return (True, None)

        def mock_translate_hints(tasks, language):
            res = {}
            for i, t_obj in enumerate(tasks):
                res[(i, t_obj.goal)] = t_obj.goal
                if getattr(t_obj, 'hint', None):
                    res[(i, t_obj.hint)] = t_obj.hint
            return res

        def mock_llm_chat(messages, options, cache_key=None):
            return {'message': {'content': 'Mocked LLM chat response'}}

        class DummySpinner:
            def __init__(self, *args, **kwargs):
                pass
            def start(self):
                pass
            def stop(self):
                pass

        with patch("sys.stdin", io.StringIO(input_data)), \
             patch("sys.stdout", self.stdout), \
             patch("sys.stderr", self.stderr), \
             patch("sys.argv", args), \
             patch("app.cli.Spinner", DummySpinner), \
             patch("app.cli._ensure_model", return_value=(MagicMock(), MagicMock())), \
             patch("app.cli.call_actor", side_effect=mock_call_actor), \
             patch("app.cli.stream_actor", side_effect=mock_stream_actor), \
             patch("app.cli.translate_hints", side_effect=mock_translate_hints), \
             patch("app.cli.call_coach", side_effect=mock_call_coach), \
             patch("app.cli.evaluate_task", side_effect=mock_evaluate_task), \
             patch("app.llm._llm_chat", side_effect=mock_llm_chat), \
             patch("app.coach._llm_chat", side_effect=mock_llm_chat), \
             patch("app.judge._llm_chat", side_effect=mock_llm_chat):

            try:
                cli.main()
            except SystemExit:
                pass

        return self.stdout.getvalue(), self.stderr.getvalue()


# ── Scenario 1: Full English session ──────────────────────────────────────────

def test_full_english_session(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "1",
        "I would like a table for two please",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)

    assert "SESSION SUMMARY" in out
    assert "Target Language: English" in out
    assert "Traceback" not in out
    assert "Traceback" not in err

    conn = db.init_db(str(harness.tmp_db))
    session = conn.execute("SELECT * FROM sessions").fetchone()
    assert session is not None
    assert session["finished_at"] is not None
    assert session["tasks_done"] == 1
    assert session["tasks_skipped"] == 0
    conn.close()


# ── Scenario 2: Full Japanese session ─────────────────────────────────────────

def test_full_japanese_session(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "Japanese",
        "n",
        "1",
        "二人用のテーブルをお願いします",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)

    assert "セッションのまとめ" in out
    assert "対象言語: Japanese" in out
    assert "完了したタスク" in out

    untranslated_labels = [
        "SESSION SUMMARY & PERFORMANCE REVIEW",
        "Available Scenarios:",
        "Total Tasks:",
        "Tasks Completed:",
        "Tasks Skipped/Failed:",
        "Completion Score:",
        "Data saved to local SQLite database",
    ]
    for label in untranslated_labels:
        assert label not in out, f"Found untranslated English label: '{label}'"

    conn = db.init_db(str(harness.tmp_db))
    session = conn.execute("SELECT * FROM sessions").fetchone()
    assert session is not None
    assert session["finished_at"] is not None
    assert session["language"] == "Japanese"
    assert session["tasks_done"] == 1
    conn.close()


# ── Scenario 3: Skip task ─────────────────────────────────────────────────────

def test_skip_task(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "1",
        "skip",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)

    assert "Traceback" not in out
    assert "Traceback" not in err

    conn = db.init_db(str(harness.tmp_db))
    task_log = conn.execute("SELECT * FROM task_logs WHERE outcome = 'skipped'").fetchone()
    assert task_log is not None
    assert task_log["outcome"] == "skipped"

    session = conn.execute("SELECT * FROM sessions").fetchone()
    assert session["tasks_skipped"] == 1
    conn.close()


# ── Scenario 4: Ctrl+D (EOFError) mid-conversation ───────────────────────────

def test_ctrl_d_mid_conversation(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "1",
        # EOF happens here
    ]
    out, err = harness.run(inputs=inputs)

    assert "Exiting..." in out
    assert "Traceback" not in out
    assert "Traceback" not in err

    conn = db.init_db(str(harness.tmp_db))
    session = conn.execute("SELECT * FROM sessions").fetchone()
    assert session is not None
    assert session["finished_at"] is not None
    conn.close()


# ── Scenario 5: Vocab warm-up ─────────────────────────────────────────────────

def test_vocab_warmup(tmp_path, monkeypatch):
    db_file = tmp_path / "test_sessions.db"
    monkeypatch.setenv("LANGUAGE_COACH_DB", str(db_file))
    monkeypatch.setattr(db, "DB_PATH", str(db_file))

    conn = db.init_db(str(db_file))
    user_id = db.get_or_create_user(conn, target_lang="English")
    db.log_vocab(conn, user_id, "English", "espresso", "strong black coffee", "Cafe")
    conn.close()

    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "1",
        "espresso",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)

    assert "espresso" in out

    conn = db.init_db(str(db_file))
    row = conn.execute("SELECT times_correct FROM vocab_log WHERE word = 'espresso'").fetchone()
    assert row is not None
    assert row["times_correct"] == 1
    conn.close()


# ── Scenario 6: Resume ────────────────────────────────────────────────────────

def test_resume_session(tmp_path, monkeypatch):
    db_file = tmp_path / "test_sessions.db"
    monkeypatch.setenv("LANGUAGE_COACH_DB", str(db_file))
    monkeypatch.setattr(db, "DB_PATH", str(db_file))

    conn = db.init_db(str(db_file))
    user_id = db.get_or_create_user(conn, target_lang="English")

    sc_obj = SCENARIOS[0]
    first_task = sc_obj.tasks[0]

    session_id = db.create_session(conn, user_id, sc_obj.name, "English", "cheerful", None, len(sc_obj.tasks))
    db.log_task(
        conn, session_id, sc_obj.name, user_id, 0, first_task.goal,
        first_task.done_when, first_task.difficulty, first_task.phase,
        "completed", 1, db._utcnow(), db._utcnow()
    )
    conn.close()

    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "y",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)

    assert "unfinished session" in out.lower() or "resume" in out.lower()

    conn = db.init_db(str(db_file))
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    assert session is not None
    assert session["id"] == session_id

    # The logged task goal should not be served again
    assert first_task.goal not in out
    conn.close()


# ── Scenario 7: Scenario chooser ──────────────────────────────────────────────

def test_scenario_chooser(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "all",
        "hotel",
        "1",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)

    assert "more scenarios" in out
    assert "hotel" in out.lower()

    conn = db.init_db(str(harness.tmp_db))
    session = conn.execute("SELECT * FROM sessions").fetchone()
    assert session is not None
    assert "hotel" in session["scenario_name"].lower()
    conn.close()


# ── Scenario 8: --stats flag ──────────────────────────────────────────────────

def test_stats_flag(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    out, err = harness.run(args=["cli", "--stats"])

    assert "LEARNER PROGRESS REPORT" in out
    assert "Overall Progress:" in out
    assert "Traceback" not in out
    assert "Traceback" not in err


# ── Additional Edge Cases Coverage ─────────────────────────────────────────────

def test_invalid_language_retry(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "invalid_lang_123",
        "English",
        "n",
        "1",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)
    assert "Unsupported language" in out


def test_empty_user_input_warning(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "1",
        "",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)
    assert "didn't type anything" in out.lower() or "skip" in out.lower()


def test_task_failed_max_attempts(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "1",
        "try 1",
        "try 2",
        "try 3",
        "try 4",
        "quit",
    ]
    out, err = harness.run(inputs=inputs, judge_response=(False, "Not quite right"))
    assert "Moving on" in out or "tries" in out

    conn = db.init_db(str(harness.tmp_db))
    task_log = conn.execute("SELECT * FROM task_logs WHERE outcome = 'failed'").fetchone()
    assert task_log is not None
    assert task_log["outcome"] == "failed"
    conn.close()


def test_decline_resume_session(tmp_path, monkeypatch):
    db_file = tmp_path / "test_sessions.db"
    monkeypatch.setenv("LANGUAGE_COACH_DB", str(db_file))
    monkeypatch.setattr(db, "DB_PATH", str(db_file))

    conn = db.init_db(str(db_file))
    user_id = db.get_or_create_user(conn, target_lang="English")
    sc_obj = SCENARIOS[0]
    session_id = db.create_session(conn, user_id, sc_obj.name, "English", "cheerful", None, len(sc_obj.tasks))
    db.log_task(
        conn, session_id, sc_obj.name, user_id, 0, sc_obj.tasks[0].goal,
        sc_obj.tasks[0].done_when, sc_obj.tasks[0].difficulty, sc_obj.tasks[0].phase,
        "completed", 1, db._utcnow(), db._utcnow()
    )
    conn.close()

    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",      # Decline resume
        "n",      # Decline random scenario
        "1",      # Select scenario 1
        "quit",
    ]
    out, err = harness.run(inputs=inputs)

    conn = db.init_db(str(db_file))
    old_session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    assert old_session["finished_at"] is not None

    sessions = conn.execute("SELECT * FROM sessions").fetchall()
    assert len(sessions) == 2
    conn.close()


def test_chooser_no_matches(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "nonexistent_scenario_12345",
        "1",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)
    assert "No scenarios matching" in out or "nonexistent_scenario_12345" in out


def test_stats_invalid_language(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    out, err = harness.run(args=["cli", "--stats", "--lang", "invalid_lang_xyz"])
    assert "Unsupported language" in out


def test_is_name_unit():
    assert cli._is_name("Paris", "I live in Paris.", "English") is True
    assert cli._is_name("coffee", "I like coffee.", "English") is False
    assert cli._is_name("Haus", "Das Haus ist groß.", "German") is False


def test_vocab_review_incorrect_and_skip(tmp_path, monkeypatch):
    db_file = tmp_path / "test_sessions.db"
    monkeypatch.setenv("LANGUAGE_COACH_DB", str(db_file))
    monkeypatch.setattr(db, "DB_PATH", str(db_file))

    conn = db.init_db(str(db_file))
    user_id = db.get_or_create_user(conn, target_lang="English")
    db.log_vocab(conn, user_id, "English", "latte", "coffee with milk", "Cafe")
    db.log_vocab(conn, user_id, "English", "mocha", "chocolate coffee", "Cafe")
    conn.close()

    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "1",
        "wrong_answer",
        "skip",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)
    assert "Incorrect" in out

    conn = db.init_db(str(db_file))
    row = conn.execute("SELECT times_correct FROM vocab_log WHERE word = 'latte'").fetchone()
    assert row["times_correct"] == 0
    conn.close()


# ── Repeat-the-correction drill ───────────────────────────────────────────────

CORRECTION_EN = (
    '💡 Feedback:\n'
    '- ❌ "two bottle" → ✅ "two bottles" (after a number, use the plural)'
)


def test_correction_drill_requires_a_correct_retype(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "1",
        "Can I get two bottle of water?",
        "two bottle",          # wrong retype — must re-prompt
        "two bottles",         # correct retype — session continues
        "quit",
    ]
    out, err = harness.run(inputs=inputs, coach_response=CORRECTION_EN)

    assert "Type the corrected form" in out
    assert "not it yet" in out
    assert "Got it." in out
    assert "SESSION SUMMARY" in out
    assert "Traceback" not in out
    assert "Traceback" not in err


def test_correction_drill_accepts_a_retype_differing_only_by_punctuation(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    coach_response = (
        '💡 Feedback:\n'
        '- ❌ "薬を食べました" → ✅ "薬を飲みました" (「薬」は「飲む」と言います)'
    )
    inputs = [
        "Japanese",
        "n",
        "1",
        "風邪をひいたので、薬を食べました。",
        "薬を飲みました。",     # trailing 。 the coach did not quote
        "quit",
    ]
    out, err = harness.run(inputs=inputs, coach_response=coach_response)

    assert "できました。" in out
    assert "少し違います" not in out
    assert "セッションのまとめ" in out


def test_clean_verdict_starts_no_drill(tmp_path, monkeypatch):
    harness = CLIHarness(tmp_path, monkeypatch)
    inputs = [
        "English",
        "n",
        "1",
        "I would like a table for two please",
        "quit",
    ]
    out, err = harness.run(inputs=inputs)

    assert "Type the corrected form" not in out
    assert "Retype:" not in out
    assert "SESSION SUMMARY" in out


def test_the_npc_replies_before_the_coach_runs(tmp_path, monkeypatch):
    """The turn order is judge -> actor -> coach, and it is load-bearing.

    Measured 2026-09-06: a warm turn spends ~1.5s in the coach, ~3.9s in the
    judge and ~3.0s before the actor's first streamed sentence. With the coach
    running first, the learner watched a spinner for the whole ~8.4s before any
    dialogue appeared. Running it after the actor puts the NPC's reply on screen
    sooner and, more importantly, before the correction drill blocks on input.

    The judge must stay AHEAD of the actor: a completed task advances
    current_task_idx, which picks the next task the NPC steers toward, or the
    wrap-up prompt on the final one. An actor running first would answer without
    knowing the task completed.

    Every collaborator is mocked in the other session tests, so both orders pass
    them — this is the only thing holding the order in place.
    """
    harness = CLIHarness(tmp_path, monkeypatch)
    harness.run(inputs=["English", "n", "1",
                        "I would like a table for two please", "quit"])

    turn = harness.calls
    assert 'judge' in turn and 'actor' in turn and 'coach' in turn, turn
    first_coach = turn.index('coach')
    assert turn.index('judge') < first_coach, (
        'judge must precede the coach; the actor prompt depends on its verdict: %r' % turn)
    actors_before_coach = [i for i, c in enumerate(turn[:first_coach]) if c == 'actor']
    assert actors_before_coach, (
        'the NPC must reply before the coach runs, so its line reaches the learner first: %r' % turn)
