"""Internationalization (i18n) table and helper for CLI UI strings."""

UI_STRINGS = {
    'err_no_scenarios': {
        'English': 'Error: No scenarios with tasks found!',
        'Japanese': 'エラー: タスクを含むシナリオが見つかりません！',
    },
    'random_scenario': {
        'English': 'Randomly selected scenario: {name}',
        'Japanese': 'ランダムに選択されたシナリオ: {name}',
    },
    'prompt_play_scenario': {
        'English': 'Do you want to play this scenario? (y/n): ',
        'Japanese': 'このシナリオをプレイしますか？ (y/n): ',
    },
    'available_scenarios': {
        'English': 'Available Scenarios:',
        'Japanese': '利用可能なシナリオ:',
    },
    'scenario_item': {
        'English': '{i}. {name} ({n} tasks available)',
        'Japanese': '{i}. {name} ({n} 個のタスクが利用可能)',
    },
    'prompt_select_scenario': {
        'English': "Enter the number of the scenario you want (or 'quit'): ",
        'Japanese': "ご希望のシナリオの番号を入力してください（または 'quit'）: ",
    },
    'exiting': {
        'English': 'Exiting...',
        'Japanese': '終了中...',
    },
    'invalid_number': {
        'English': 'Invalid number. Try again.',
        'Japanese': '無効な番号です。やり直してください。',
    },
    'enter_valid_number': {
        'English': 'Please enter a valid number.',
        'Japanese': '有効な番号を入力してください。',
    },
    'cli_title': {
        'English': '   Language Conversation Coach CLI',
        'Japanese': '   言語会話コーチ CLI',
    },
    'err_model_init': {
        'English': 'Error: Could not initialize MLX model {model}. Exiting.',
        'Japanese': 'エラー: MLXモデル {model} を初期化できませんでした。終了します。',
    },
    'preparing_session': {
        'English': '[Preparing session...]',
        'Japanese': '[セッションを準備中...]',
    },
    'spinner_connecting_model': {
        'English': 'Connecting to MLX model',
        'Japanese': 'MLXモデルに接続中',
    },
    'err_check_mlx': {
        'English': 'Please check your local MLX setup or model files.',
        'Japanese': 'ローカルのMLXセットアップまたはモデルファイルを確認してください。',
    },
    'task_header': {
        'English': '--- Task {n}/{total} ---',
        'Japanese': '--- タスク {n}/{total} ---',
    },
    'objective': {
        'English': '🎯 Objective:',
        'Japanese': '🎯 目標:',
    },
    'objective_line': {
        'English': "🎯 Objective: {hint} (type 'skip' to move on)",
        'Japanese': "🎯 目標: {hint} (次へ進むには 'skip' と入力)",
    },
    'you_prompt': {
        'English': '\nYou: ',
        'Japanese': '\nあなた: ',
    },
    'skipped_task': {
        'English': '⏭️  Skipped: {goal}',
        'Japanese': '⏭️  スキップしました: {goal}',
    },
    'spinner_setting_scene': {
        'English': '{speaker} is setting the scene',
        'Japanese': '{speaker}が場面を設定中',
    },
    'empty_input_warning': {
        'English': "[You didn't type anything — say something to the {speaker}, or type 'skip'/'quit'.]",
        'Japanese': "[何も入力されていません — {speaker}に何か話しかけるか、'skip'/'quit'と入力してください。]",
    },
    'spinner_analyzing': {
        'English': 'Analyzing feedback & goal progress',
        'Japanese': 'フィードバックと進捗を分析中',
    },
    'task_completed': {
        'English': '✅ TASK COMPLETED! Moving to next...',
        'Japanese': '✅ タスク完了！ 次へ進みます...',
    },
    'moving_on_failed': {
        'English': '➡️  Moving on after {n} tries. Goal was: {goal}',
        'Japanese': '➡️  {n} 回試行後に次へ進みます。目標: {goal}',
    },
    'task_not_completed': {
        'English': '❌ Task not yet completed. Keep trying! ({n}/{max} attempts)',
        'Japanese': '❌ タスクはまだ完了していません。引き続き挑戦してください！ ({n}/{max} 回目の試行)',
    },
    'strategy_hint': {
        'English': '💡 Strategy Hint: {hint}',
        'Japanese': '💡 ヒント: {hint}',
    },
    'judge_note': {
        'English': '🎯 Judge Note: {hint}',
        'Japanese': '🎯 判定ノート: {hint}',
    },
    'spinner_thinking': {
        'English': '{speaker} is thinking',
        'Japanese': '{speaker}が考え中',
    },
    'msg_not_processed': {
        'English': "[Your last message wasn't processed — please try again.]",
        'Japanese': "[最後のメッセージが処理されませんでした。もう一度お試しください。]",
    },
    'session_summary_header': {
        'English': '       🏁 SESSION SUMMARY & PERFORMANCE REVIEW',
        'Japanese': '       🏁 セッションのまとめとパフォーマンスレビュー',
    },
    'summary_scenario': {
        'English': '• Scenario: {name} ({place})',
        'Japanese': '• シナリオ: {name} ({place})',
    },
    'summary_target_language': {
        'English': '• Target Language: {language}',
        'Japanese': '• 対象言語: {language}',
    },
    'summary_total_tasks': {
        'English': '• Total Tasks: {n}',
        'Japanese': '• 全タスク数: {n}',
    },
    'summary_tasks_completed': {
        'English': '• Tasks Completed: ✅ {n}',
        'Japanese': '• 完了したタスク: ✅ {n}',
    },
    'summary_tasks_failed': {
        'English': '• Tasks Skipped/Failed: ⏭️ {n}',
        'Japanese': '• スキップ/失敗したタスク: ⏭️ {n}',
    },
    'summary_completion_score': {
        'English': '• Completion Score: {pct}%',
        'Japanese': '• 達成スコア: {pct}%',
    },
    'summary_db_saved': {
        'English': '\nData saved to local SQLite database (`{path}`).',
        'Japanese': '\nローカルSQLiteデータベース（`{path}`）にデータを保存しました。',
    },
    'vocab_tip_box': {
        'English': '\n📖 Vocab Tip:\n• Word: {word}\n• Meaning: {exp}\n• Try it: {enc}\n',
        'Japanese': '\n📖 単語のヒント:\n• 単語: {word}\n• 意味: {exp}\n• 使ってみよう: {enc}\n',
    },
}


class _SafeDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"


def t(key: str, language: str, **fmt) -> str:
    """UI string in `language`, falling back to English for anything unknown."""
    if not isinstance(language, str):
        language = 'English'
    entry = UI_STRINGS.get(key, {})
    pattern = entry.get(language)
    if not pattern:
        pattern = entry.get('English')
    if not pattern:
        pattern = key.replace('_', ' ').capitalize()
    if fmt:
        try:
            return pattern.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return pattern.format_map(_SafeDict(fmt))
    return pattern


def scenario_name(scenario, language: str) -> str:
    """Return translated scenario name for language, falling back to English scenario.name."""
    if isinstance(language, str) and hasattr(scenario, 'name_translations') and scenario.name_translations:
        val = scenario.name_translations.get(language)
        if val:
            return val
    return scenario.name


def scenario_place(scenario, language: str) -> str:
    """Return translated scenario place for language, falling back to English scenario.place."""
    if isinstance(language, str) and hasattr(scenario, 'place_translations') and scenario.place_translations:
        val = scenario.place_translations.get(language)
        if val:
            return val
    return scenario.place
