"""Internationalization (i18n) table and helper for CLI UI strings."""

UI_STRINGS = {
    'err_no_scenarios': {
        'English': 'Error: No scenarios with tasks found!',
        'Japanese': 'エラー: タスクを含むシナリオが見つかりません！',
        'Thai': 'ข้อผิดพลาด: ไม่พบสถานการณ์ที่มีภารกิจ!',
    },
    'random_scenario': {
        'English': 'Randomly selected scenario: {name}',
        'Japanese': 'ランダムに選択されたシナリオ: {name}',
        'Thai': 'สุ่มเลือกสถานการณ์: {name}',
    },
    'prompt_play_scenario': {
        'English': 'Do you want to play this scenario? (y/n): ',
        'Japanese': 'このシナリオをプレイしますか？ (y/n): ',
        'Thai': 'คุณต้องการเล่นสถานการณ์นี้หรือไม่? (y/n): ',
    },
    'available_scenarios': {
        'English': 'Available Scenarios:',
        'Japanese': '利用可能なシナリオ:',
        'Thai': 'สถานการณ์ที่มีอยู่:',
    },
    'scenario_item': {
        'English': '{i}. {name} ({n} tasks available)',
        'Japanese': '{i}. {name} ({n} 個のタスクが利用可能)',
        'Thai': '{i}. {name} (มี {n} ภารกิจ)',
    },
    'prompt_select_scenario': {
        'English': "Enter the number of the scenario you want (or 'quit'): ",
        'Japanese': "ご希望のシナリオの番号を入力してください（または 'quit'）: ",
        'Thai': "ป้อนหมายเลขสถานการณ์ที่ต้องการ (หรือ 'quit'): ",
    },
    'exiting': {
        'English': 'Exiting...',
        'Japanese': '終了中...',
        'Thai': 'กำลังออกจากระบบ...',
    },
    'invalid_number': {
        'English': 'Invalid number. Try again.',
        'Japanese': '無効な番号です。やり直してください。',
        'Thai': 'หมายเลขไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง',
    },
    'enter_valid_number': {
        'English': 'Please enter a valid number.',
        'Japanese': '有効な番号を入力してください。',
        'Thai': 'กรุณาป้อนหมายเลขที่ถูกต้อง',
    },
    'cli_title': {
        'English': '   Language Conversation Coach CLI',
        'Japanese': '   言語会話コーチ CLI',
        'Thai': '   CLI โค้ชการสนทนาภาษา',
    },
    'err_model_init': {
        'English': 'Error: Could not initialize MLX model {model}. Exiting.',
        'Japanese': 'エラー: MLXモデル {model} を初期化できませんでした。終了します。',
        'Thai': 'ข้อผิดพลาด: ไม่สามารถเริ่มต้นโมเดล MLX {model} ได้ กำลังออกจากระบบ',
    },
    'preparing_session': {
        'English': '[Preparing session...]',
        'Japanese': '[セッションを準備中...]',
        'Thai': '[กำลังเตรียมเซスชัน...]',
    },
    'spinner_connecting_model': {
        'English': 'Connecting to MLX model',
        'Japanese': 'MLXモデルに接続中',
        'Thai': 'กำลังเชื่อมต่อกับโมเดล MLX',
    },
    'err_check_mlx': {
        'English': 'Please check your local MLX setup or model files.',
        'Japanese': 'ローカルのMLXセットアップまたはモデルファイルを確認してください。',
        'Thai': 'โปรดตรวจสอบการตั้งค่า MLX หรือไฟล์โมเดลในเครื่องของคุณ',
    },
    'task_header': {
        'English': '--- Task {n}/{total} ---',
        'Japanese': '--- タスク {n}/{total} ---',
        'Thai': '--- ภารกิจ {n}/{total} ---',
    },
    'objective': {
        'English': '🎯 Objective:',
        'Japanese': '🎯 目標:',
        'Thai': '🎯 เป้าหมาย:',
    },
    'objective_line': {
        'English': "🎯 Objective: {hint} (type 'skip' to move on)",
        'Japanese': "🎯 目標: {hint} (次へ進むには 'skip' と入力)",
        'Thai': "🎯 เป้าหมาย: {hint} (พิมพ์ 'skip' เพื่อข้าม)",
    },
    'you_prompt': {
        'English': '\nYou: ',
        'Japanese': '\nあなた: ',
        'Thai': '\nคุณ: ',
    },
    'skipped_task': {
        'English': '⏭️  Skipped: {goal}',
        'Japanese': '⏭️  スキップしました: {goal}',
        'Thai': '⏭️  ข้ามแล้ว: {goal}',
    },
    'spinner_setting_scene': {
        'English': '{speaker} is setting the scene',
        'Japanese': '{speaker}が場面を設定中',
        'Thai': '{speaker} กำลังจัดฉาก',
    },
    'empty_input_warning': {
        'English': "[You didn't type anything — say something to the {speaker}, or type 'skip'/'quit'.]",
        'Japanese': "[何も入力されていません — {speaker}に何か話しかけるか、'skip'/'quit'と入力してください。]",
        'Thai': "[คุณไม่ได้พิมพ์อะไรเลย — พูดบางอย่างกับ {speaker} หรือพิมพ์ 'skip'/'quit']",
    },
    'spinner_analyzing': {
        'English': 'Analyzing feedback & goal progress',
        'Japanese': 'フィードバックと進捗を分析中',
        'Thai': 'กำลังวิเคราะห์ข้อเสนอแนะและความคืบหน้า',
    },
    'task_completed': {
        'English': '✅ TASK COMPLETED! Moving to next...',
        'Japanese': '✅ タスク完了！ 次へ進みます...',
        'Thai': '✅ ภารกิจสำเร็จ! กำลังไปยังภารกิจถัดไป...',
    },
    'moving_on_failed': {
        'English': '➡️  Moving on after {n} tries. Goal was: {goal}',
        'Japanese': '➡️  {n} 回試行後に次へ進みます。目標: {goal}',
        'Thai': '➡️  ข้ามหลังจากพยายาม {n} ครั้ง เป้าหมายคือ: {goal}',
    },
    'task_not_completed': {
        'English': '❌ Task not yet completed. Keep trying! ({n}/{max} attempts)',
        'Japanese': '❌ タスクはまだ完了していません。引き続き挑戦してください！ ({n}/{max} 回目の試行)',
        'Thai': '❌ ภารกิจยังไม่สำเร็จ พยายามต่อไป! (พยายามครั้งที่ {n}/{max})',
    },
    'strategy_hint': {
        'English': '💡 Strategy Hint: {hint}',
        'Japanese': '💡 ヒント: {hint}',
        'Thai': '💡 คำแนะนำกลยุทธ์: {hint}',
    },
    'judge_note': {
        'English': '🎯 Judge Note: {hint}',
        'Japanese': '🎯 判定ノート: {hint}',
        'Thai': '🎯 หมายเหตุผู้ประเมิน: {hint}',
    },
    'spinner_thinking': {
        'English': '{speaker} is thinking',
        'Japanese': '{speaker}が考え中',
        'Thai': '{speaker} กำลังคิด',
    },
    'msg_not_processed': {
        'English': "[Your last message wasn't processed — please try again.]",
        'Japanese': "[最後のメッセージが処理されませんでした。もう一度お試しください。]",
        'Thai': "[ข้อความล่าสุดของคุณไม่ได้รับการประมวลผล — กรุณาลองใหม่อีกครั้ง]",
    },
    'session_summary_header': {
        'English': '       🏁 SESSION SUMMARY & PERFORMANCE REVIEW',
        'Japanese': '       🏁 セッションのまとめとパフォーマンスレビュー',
        'Thai': '       🏁 สรุปเซสชันและการประเมินผล',
    },
    'summary_scenario': {
        'English': '• Scenario: {name} ({place})',
        'Japanese': '• シナリオ: {name} ({place})',
        'Thai': '• สถานการณ์: {name} ({place})',
    },
    'summary_target_language': {
        'English': '• Target Language: {language}',
        'Japanese': '• 対象言語: {language}',
        'Thai': '• ภาษาเป้าหมาย: {language}',
    },
    'summary_total_tasks': {
        'English': '• Total Tasks: {n}',
        'Japanese': '• 全タスク数: {n}',
        'Thai': '• ภารกิจทั้งหมด: {n}',
    },
    'summary_tasks_completed': {
        'English': '• Tasks Completed: ✅ {n}',
        'Japanese': '• 完了したタスク: ✅ {n}',
        'Thai': '• ภารกิจที่สำเร็จ: ✅ {n}',
    },
    'summary_tasks_failed': {
        'English': '• Tasks Skipped/Failed: ⏭️ {n}',
        'Japanese': '• スキップ/失敗したタスク: ⏭️ {n}',
        'Thai': '• ภารกิจที่ข้าม/ล้มเหลว: ⏭️ {n}',
    },
    'summary_completion_score': {
        'English': '• Completion Score: {pct}%',
        'Japanese': '• 達成スコア: {pct}%',
        'Thai': '• คะแนนความสำเร็จ: {pct}%',
    },
    'summary_db_saved': {
        'English': '\nData saved to local SQLite database (`{path}`).',
        'Japanese': '\nローカルSQLiteデータベース（`{path}`）にデータを保存しました。',
        'Thai': '\nบันทึกข้อมูลลงในฐานข้อมูล SQLite ท้องถิ่น (`{path}`) แล้ว',
    },
    'vocab_tip_box': {
        'English': '\n📖 Vocab Tip:\n• Word: {word}\n• Meaning: {exp}\n• Try it: {enc}\n',
        'Japanese': '\n📖 単語のヒント:\n• 単語: {word}\n• 意味: {exp}\n• 使ってみよう: {enc}\n',
        'Thai': '\n📖 เคล็ดลับคำศัพท์:\n• คำศัพท์: {word}\n• ความหมาย: {exp}\n• ลองใช้ดู: {enc}\n',
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
