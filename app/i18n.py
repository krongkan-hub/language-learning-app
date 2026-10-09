import re
from typing import Optional

UI_STRINGS = {
    # Explain mode's opening line. Authored per language for the same reason
    # the listener prompt is: this text sets the frame the learner answers in.
    # No self-introduction: the listener descriptions are third-person
    # descriptors ("a relative who does not understand your job at all"), and
    # dropping one into "I'm {listener}, and I don't know this at all" read as
    # "...does not understand your job at all, and I don't know this at all".
    # The header already shows who is listening, so the line just asks.
    # What the listener says when the model granted a point with no words.
    'explain_ack': {
        'English': 'I see — that makes sense.',
        'Japanese': 'なるほど、そういうことですね。',
    },
    'explain_opening': {
        'English': "I don't know anything about this — could you explain "
                   "{topic} to me? I'll ask if I don't follow.",
        'Japanese': '{topic}について、まったく知らないんです。教えて'
                    'もらえますか。わからないところがあったら聞きますね。',
    },
    # The web front end's own labels. They live here rather than in
    # index.html because /api/strings' docstring already claimed the web
    # "adds no parallel translation table" while thirteen hardcoded English
    # labels in the markup were exactly that: a Japanese session showed
    # Japanese scenario, tasks and dialogue framed by an English chrome.
    'web_skip_task': {'English': 'Skip task', 'Japanese': 'タスクをスキップ'},
    'web_end': {'English': 'End', 'Japanese': '終了'},
    'web_send': {'English': 'Send', 'Japanese': '送信'},
    'web_tasks': {'English': 'Tasks', 'Japanese': 'タスク'},
    'web_coach': {'English': 'Margin notes', 'Japanese': '赤ペンメモ'},   # Red Pen (#50b)
    'web_vocabulary': {'English': 'Vocabulary', 'Japanese': '単語'},
    'web_coach_empty': {
        'English': 'Your grammar feedback will appear here after each message.',
        'Japanese': 'メッセージごとに文法のフィードバックがここに表示されます。',
    },
    'web_vocab_empty': {
        'English': 'New words from the conversation will appear here.',
        'Japanese': '相手が教えてくれた単語がここにたまります。',
    },
    'web_progress': {'English': 'Progress', 'Japanese': 'シナリオ別の記録'},
    'web_browse': {'English': 'Browse all 80 scenarios', 'Japanese': '全80シナリオを見る'},
    'web_close': {'English': 'Close', 'Japanese': '閉じる'},
    'web_search': {'English': 'Search scenarios…', 'Japanese': 'シナリオを検索…'},
    'web_again': {'English': 'Practice again', 'Japanese': 'もう一度練習する'},
    'web_review': {'English': 'Review conversation', 'Japanese': '会話を見返す'},
    'web_input_placeholder': {'English': 'Type your reply…', 'Japanese': '返事を入力…'},
    # The Progress page's scenario table used to also list explain topics —
    # "Coffee Shop" (1 of 80 roleplay scenarios) sat next to "how to get from
    # home to work" (1 of 10 explain topics) with the same columns, so a
    # learner could not tell which kind of thing a row was, and the mastery
    # ladder read as though it meant the same thing for both. These head the
    # two tables the Progress page now shows instead of one merged table.
    'web_stat_scenarios': {'English': 'Scenarios', 'Japanese': 'シナリオ'},
    'web_stat_topics': {'English': 'Explain topics', 'Japanese': '説明練習のテーマ'},
    'web_col_plays': {'English': 'Plays', 'Japanese': 'プレイ回数'},
    'web_col_best': {'English': 'Best score', 'Japanese': '最高スコア'},
    'web_col_mastery': {'English': 'Mastery', 'Japanese': '習熟度'},
    'web_no_stats': {'English': 'No sessions recorded yet.', 'Japanese': 'まだ記録がありません。'},
    # The goal line for a vocabulary task. Composed from an authored target
    # rather than translated, so those 401 goals never enter translate_hints'
    # batch — the shape that reproducibly came back as 使用「voucher」这个词.
    'vocab_goal': {
        'English': "Use the word '{word}'",
        'Japanese': '「{word}」という単語を使う',
    },
    'cli_title': {
        'English': '   Language Conversation Coach CLI',
        'Japanese': '   言語会話コーチ CLI',
    },
    'retried_tasks_included': {
        'English': "{n} tasks you didn't finish last time are included.",
        'Japanese': '前回達成できなかったタスクが{n}件含まれています。',
    },
    'task_header': {
        'English': '--- Task {n}/{total} ---',
        'Japanese': '--- タスク {n}/{total} ---',
    },
    'objective_line': {
        'English': "🎯 Objective: {hint} (type 'skip' to move on)",
        'Japanese': "🎯 目標: {hint} (次へ進むには 'skip' と入力)",
    },
    'skipped_task': {
        'English': '⏭️  Skipped: {goal}',
        'Japanese': '⏭️  スキップしました: {goal}',
    },
    'spinner_analyzing': {
        'English': 'Analyzing feedback & goal progress',
        'Japanese': 'フィードバックと進捗を分析中',
    },
    'task_completed': {
        'English': '✅ TASK COMPLETED! Moving to next...',
        'Japanese': '✅ タスク達成！ 次へ進みます…',
    },
    'moving_on_failed': {
        'English': '➡️  Moving on after {n} tries. Goal was: {goal}',
        'Japanese': '➡️  {n}回挑戦したので、次へ進みます。目標: {goal}',
    },
    'task_not_completed': {
        'English': '❌ Task not yet completed. Keep trying! ({n}/{max} attempts)',
        'Japanese': '❌ タスクはまだ達成できていません。もう一度どうぞ！（{n}/{max}回目）',
    },
    'strategy_hint': {
        'English': '💡 Strategy Hint: {hint}',
        'Japanese': '💡 ヒント: {hint}',
    },
    'judge_note': {
        'English': '🎯 Judge Note: {hint}',
        'Japanese': '🎯 判定メモ: {hint}',
    },
    'drill_intro': {
        'English': '✍️  Type the corrected form to lock it in: "{correction}"',
        'Japanese': '✍️  正しい形を入力して覚えましょう:「{correction}」',
    },
    'drill_prompt': {
        'English': 'Retype: ',
        'Japanese': 'もう一度入力: ',
    },
    'drill_retry': {
        'English': '❌ Almost. Type it exactly as shown: "{correction}"',
        'Japanese': '❌ 少し違います。この通りに入力してください:「{correction}」',
    },
    'drill_correct': {
        'English': '✅ Got it.',
        'Japanese': '✅ 正解です。',
    },
    'spinner_thinking': {
        'English': '{speaker} is thinking',
        'Japanese': '{speaker}が考え中',
    },
    'msg_not_processed': {
        'English': "[Your last message wasn't processed — please try again.]",
        'Japanese': "[最後のメッセージが処理されませんでした。もう一度お試しください。]",
    },
    'summary_tasks_failed': {
        'English': '• Tasks Skipped/Failed: ⏭️ {n}',
        'Japanese': '• スキップ/失敗したタスク: ⏭️ {n}',
    },
    'vocab_tip_box': {
        'English': '\n📖 Vocab Tip:\n• Word: {word}\n• Meaning: {exp}\n• Try it: {enc}\n',
        'Japanese': '\n📖 単語のヒント:\n• 単語: {word}\n• 意味: {exp}\n• 使ってみましょう: {enc}\n',
    },
    'newbie': {
        'English': '⭐ Not played yet',
        'Japanese': '⭐ 未挑戦',
    },
    'apprentice': {
        'English': '🥉 Apprentice (Level 1)',
        'Japanese': '🥉 見習い（レベル1）',
    },
    'experienced': {
        'English': '🥈 Experienced (Level 2)',
        'Japanese': '🥈 経験者（レベル2）',
    },
    'mastered': {
        'English': '🏆 Mastered (Level 3)',
        'Japanese': '🏆 マスター（レベル3）',
    },
    'stats_mistakes_header': {
        'English': 'Mistakes you keep making:',
        'Japanese': '繰り返している間違い:',
    },
    'web_vocab_used': {
        'English': '✓ You used “{word}” ({n} of 3)',
        'Japanese': '✓ 「{word}」を使いました（{n}/3）',
    },
    'web_vocab_learned': {
        'English': '★ You’ve learned “{word}” — used 3 times, so it’s off your review list',
        'Japanese': '★ 「{word}」を覚えました — 3回使ったので復習リストから外れます',
    },
    'review_nothing_yet': {
        'English': 'Nothing to practice yet: the coach has not corrected anything short enough to say again. Play a scenario first.',
        'Japanese': 'まだ練習する間違いがありません。先にシナリオで会話してみましょう。',
    },
    'web_review_mistakes': {'English': 'Practice your mistakes', 'Japanese': '間違えたところを練習'},
    'web_dashboard': {'English': 'Dashboard', 'Japanese': '学習の記録'},
    'web_repeat_badge': {
        'English': '🔁 {n}× — you’ve made this mistake before',
        'Japanese': '🔁 {n}回目 — 前にも同じ間違いをしています',
    },
}



class _SafeDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"


def t(key: str, language: str, /, **fmt) -> str:
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

# The actor is given one of six moods, and the web header shows it so the
# learner knows who they are about to talk to. The prompt strings are written
# for the model ("harried and rushing, keen to keep things moving") and are
# English, so a Japanese session showed an English mood in an otherwise
# Japanese interface. Keyed on the prompt string's first clause, which is the
# part the header displays.
MOOD_LABELS = {
    'harried and rushing': {'English': 'rushed and in a hurry', 'Japanese': 'せかせかと急いでいる'},
    'chatty and friendly': {'English': 'chatty and friendly', 'Japanese': '話し好きで親しみやすい'},
    'curt and impatient': {'English': 'short and impatient', 'Japanese': 'そっけなくて気が短い'},
    'skeptical and questioning': {'English': 'skeptical and questioning', 'Japanese': '疑い深く問いただす'},
    'cheerful but scatterbrained': {'English': 'cheerful but forgetful', 'Japanese': '陽気だが忘れっぽい'},
    'calm and unhurried': {'English': 'calm and unhurried', 'Japanese': '落ち着いていておだやか'},
}


def mood_label(mood: str, language: str) -> str:
    """The short, localized description of an NPC mood, or '' if unknown."""
    if not mood:
        return ''
    head = mood.split(',')[0].strip()
    entry = MOOD_LABELS.get(head)
    if not entry:
        return head
    return entry.get(language) or entry.get('English') or head

# Scenarios carry name and place translations but no speaker translations, so a
# Japanese session labelled every NPC turn with an English role — Clerk,
# Waiter, Barista — beside otherwise Japanese dialogue (OPEN-36).
#
# Kept in code rather than added to 80 JSON files: the speakers are a closed set
# of 58 role labels, they are not scenario prose, and a mapping degrades
# gracefully when a new scenario introduces one. Roles with a personal name keep
# it in katakana ahead of the role, which is how Japanese addresses them.
SPEAKER_LABELS = {
    'Waiter': 'ウェイター', 'Barista': 'バリスタ', 'Clerk': '店員',
    'Receptionist': '受付', 'Agent': '係員', 'Advisor': 'アドバイザー',
    'Consultant': 'コンサルタント', 'Cashier': 'レジ係', 'Guide': 'ガイド',
    'Interviewer': '面接官', 'Technician': '技術者', 'Staff': 'スタッフ',
    'Vendor': '販売員', 'Pharmacist': '薬剤師', 'Librarian': '司書',
    'Mechanic': '整備士', 'Veterinarian': '獣医', 'Sommelier': 'ソムリエ',
    'Tailor': '仕立て屋', 'Stylist': 'スタイリスト', 'Baker': 'パン職人',
    'Florist': '花屋', 'Cobbler': '靴修理職人', 'Curator': '学芸員',
    'Farmer': '農家', 'Driver': '運転手', 'Ranger': 'レンジャー',
    'Host': '案内係', 'Bookseller': '書店員', 'Banker': '銀行員',
    'Postal Clerk': '郵便局員', 'Shopkeeper': '店主',
    'Sales Assistant': '販売員', 'Real Estate Agent': '不動産業者',
    'Property Manager': '管理人', 'Admissions Officer': '入学担当官',
    'Officer': '税関職員', 'Duty Officer': '警察官', 'Ticket Officer': '駅員',
    'Transit Officer': '交通局職員', 'Chef Instructor': '料理講師',
    'Community Manager': 'コミュニティ担当', 'Game Master': 'ゲームマスター',
    'Scoop Staff': 'アイス店員', 'Specialist': '専門家', 'Artist': 'アーティスト',
    'Assistant': '店員', 'Neighbor': '隣人', 'Friend': '友達', 'Nurse Morgan': 'モーガン看護師',
    'Officer Vance': 'ヴァンス巡査', 'Inspector Zhao': 'ジャオ検査官',
    'Adjuster Miller': '損害査定担当のミラー', 'Director Henderson': 'ヘンダーソン部長',
    'Supervisor Karen': 'カレン主任', 'Planner Celeste': 'プランナーのセレステ',
    'Founder Sam': '創業者のサム', 'Landlord Mr. Sterling': '大家のスターリングさん',
    'Loan Officer Arthur': '融資担当のアーサー',
}


def speaker_label(speaker: str, language: str) -> str:
    """The NPC's on-screen name in the language being studied.

    Falls back to the English label, which is what shipped before this existed:
    an untranslated speaker is worse than a translated one and better than a
    blank chat line.
    """
    if not speaker:
        return ''
    if language.strip().lower() not in ('japanese', 'ja'):
        return speaker
    return SPEAKER_LABELS.get(speaker, speaker)
