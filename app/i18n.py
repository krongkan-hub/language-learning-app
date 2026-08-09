import re
from typing import Optional

UI_STRINGS = {
    'err_unsupported_language': {
        'English': 'Unsupported language. Supported languages are English and Japanese.',
        'Japanese': 'サポートされていない言語です。対応している言語は English (英語) と Japanese (日本語) です。',
    },
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
    'retried_tasks_included': {
        'English': "{n} tasks you didn't finish last time are included.",
        'Japanese': '前回完了しなかったタスクが {n} 件含まれています。',
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
    'review_header': {
        'English': '\n--- Vocab Warm-Up ---',
        'Japanese': '\n--- 語彙のウォームアップ ---',
    },
    'review_prompt': {
        'English': 'What word means: "{exp}"? ',
        'Japanese': '「{exp}」を意味する単語は何ですか？ ',
    },
    'review_correct': {
        'English': '✅ Correct! The word was "{word}".',
        'Japanese': '✅ 正解！ 単語は「{word}」でした。',
    },
    'review_incorrect': {
        'English': '❌ Incorrect. The word was "{word}".',
        'Japanese': '❌ 不正解。正解の単語は「{word}」でした。',
    },
    'newbie': {
        'English': '⭐ Newbie (Unplayed)',
        'Japanese': '⭐ 初心者 (未プレイ)',
    },
    'apprentice': {
        'English': '🥉 Apprentice (Level 1)',
        'Japanese': '🥉 見習い (レベル 1)',
    },
    'experienced': {
        'English': '🥇 Experienced (Level 2)',
        'Japanese': '🥇 経験者 (レベル 2)',
    },
    'mastered': {
        'English': '🏆 Mastered (Level 3)',
        'Japanese': '🏆 マスター (レベル 3)',
    },
    'scenario_item_with_mastery': {
        'English': '{i}. {name} ({n} tasks available) — {mastery}',
        'Japanese': '{i}. {name} ({n} 個のタスクが利用可能) — {mastery}',
    },
    'stats_header': {
        'English': '📊 LEARNER PROGRESS REPORT',
        'Japanese': '📊 学習者の進捗レポート',
    },
    'stats_overall_header': {
        'English': 'Overall Progress:',
        'Japanese': '全体進捗:',
    },
    'stats_sessions_played': {
        'English': '• Sessions Played: {n}',
        'Japanese': '• プレイしたセッション数: {n}',
    },
    'stats_tasks_attempted': {
        'English': '• Tasks Attempted: {n}',
        'Japanese': '• 挑戦したタスク数: {n}',
    },
    'stats_tasks_completed': {
        'English': '• Tasks Completed: {n}',
        'Japanese': '• 完了したタスク数: {n}',
    },
    'stats_overall_rate': {
        'English': '• Overall Completion Rate: {pct}%',
        'Japanese': '• 全体達成率: {pct}%',
    },
    'stats_scenarios_header': {
        'English': 'Played Scenarios:',
        'Japanese': 'プレイ済みシナリオ:',
    },
    'stats_scenario_item': {
        'English': '• {name}: {plays} play(s), best {best_pct}%, {mastery}',
        'Japanese': '• {name}: {plays} 回プレイ, 最高 {best_pct}%, {mastery}',
    },
    'stats_no_scenarios_played': {
        'English': '• No scenarios played yet.',
        'Japanese': '• プレイ済みのシナリオはまだありません。',
    },
    'stats_vocab_header': {
        'English': 'Vocabulary:',
        'Japanese': '語彙:',
    },
    'stats_vocab_total': {
        'English': '• Total Words Taught: {n}',
        'Japanese': '• 学習した単語総数: {n}',
    },
    'stats_vocab_learned': {
        'English': '• Learned (3+ correct): {n}',
        'Japanese': '• 習得済み (正解3回以上): {n}',
    },
    'stats_vocab_due': {
        'English': '• Due for Review: {n}',
        'Japanese': '• 復習が必要: {n}',
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


def normalize_language(raw: Optional[str]) -> Optional[str]:
    """Normalize language input to 'English', 'Japanese', or None for unsupported.

    Accepts case-insensitively and whitespace-trimmed:
    - English: english, en, eng, 英語
    - Japanese: japanese, ja, jp, japan, 日本語, にほんご
    """
    if raw is None:
        return None
    cleaned = str(raw).strip()
    if not cleaned:
        return None

    english_exact = {'english', 'en', 'eng', '英語'}
    japanese_exact = {'japanese', 'ja', 'jp', 'japan', '日本語', 'にほんご'}

    lower_cleaned = cleaned.lower()
    if lower_cleaned in english_exact:
        return 'English'
    if lower_cleaned in japanese_exact:
        return 'Japanese'

    stripped = re.sub(r'[^A-Za-z]', '', cleaned).lower()
    if stripped in {'english', 'en', 'eng'}:
        return 'English'
    if stripped in {'japanese', 'ja', 'jp', 'japan'}:
        return 'Japanese'

    return None

