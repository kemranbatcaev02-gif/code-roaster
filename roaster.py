#!/usr/bin/env python3
"""
Code Roaster 🔥
Ироничный CLI-ревьюер кода в терминале: находит костыли, странный нейминг и едко их прожаривает.
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Поддержка UTF-8 на консолях Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@dataclass
class RoastIssue:
    file_path: str
    line_number: int
    line_content: str
    rule_name: str
    severity: int  # 1 to 5
    comment: str

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "comment": self.comment,
        }


PERSONALITIES = {
    "senior": {
        "name": "Сеньор-Помидор Геннадий",
        "title": "Lead Architect (25 лет опыта на Fortran)",
        "avatar": [
            r"      .-========-.",
            r"     (  (•)  (•)  )",
            r"     /     __     \   'В наше время за такое",
            r"    (   .-'  '-.   )   лишали кофемашины...'",
            r"     \  `------'  /",
            r"      `-========-'",
        ],
        "flame_comments": {
            "lazy_name": "Переменная '{name}'? Серьезно? Памяти в мозгу не хватило на нормальное слово?",
            "todo": "Вечный TODO '{text}'. Это памятник архитектурной лени, да? Внукам оставишь?",
            "debug": "Опять отладочный вывод '{text}' на проде? Логи для слабаков?",
            "swallowed_error": "Заглушил ошибку и сделал вид, что всё ок? Архитектура страуса!",
            "magic_number": "Магическое число {val}. Это твой пин-код от карты или откровение свыше?",
            "lazy_commit": "Коммит '{msg}'? Очень информативно, Шерлок. Завтра сам не вспомнишь, что сломал.",
            "zombie_code": "Закомментированный кусок кода. Git для кого придумали? Археолог ты наш.",
            "hardcoded_secrets": "Хардкоженный секрет '{secret}' прямо в кодовой базе?! Пентестеры даже кофе допить не успеют, как нас взломают!",
            "wildcard_import": "Импорт через звёздочку '{stmt}'? Засоряешь неймспейс как свалку за гаражами!",
            "sql_injection_risk": "Склеивание SQL-строк '{query}'? Привет от Little Bobby Tables! Где параметризация?!",
        },
    },
    "ramsay": {
        "name": "Шеф Гордон Рамзи",
        "title": "Kitchen & Code Nightmare Inspector",
        "avatar": [
            r"      /¯¯¯¯¯¯¯¯¯\ ",
            r"     |  (◣)  (◢) |",
            r"    <|     Д     |>  'ТВОЙ КОД НАСТОЛЬКО СЫРОЙ,",
            r"     |   \____/  |    ЧТО ОН ЕЩЁ МЫЧИТ!'",
            r"      \_________/ ",
        ],
        "flame_comments": {
            "lazy_name": "Что это за мерзкое имя '{name}'?! Это переменная или кусок мусора из мусорного бака?!",
            "todo": "TODO '{text}'?! ТЫ БРОСИЛ ЭТО ПОСРЕДИ КУХНИ ГНИТЬ?! УБЕРИ НЕМЕДЛЕННО!",
            "debug": "'{text}'?! ТЫ КОРМИШЬ КЛИЕНТОВ СЫРЫМИ ПРИНТАМИ?! ПОШЁЛ ВОН ИЗ РЕПОЗИТОРИЯ!",
            "swallowed_error": "ТЫ ПРОСТО ПРОГЛОТИЛ ОШИБКУ?! Это не обработка исключений, это кулинарное преступление!",
            "magic_number": "Число {val} без константы?! Ты сыплешь соль горстями вслепую?! ИДИОТ-СЭНДВИЧ!",
            "lazy_commit": "Коммит '{msg}'?! Даже собака наблевала бы коммит-сообщение получше этого!",
            "zombie_code": "Тухлый закомментированный код! ВОНЯЕТ НА ВЕСЬ ГИТХАБ!",
            "hardcoded_secrets": "ТЫ ВШИЛ СЕКРЕТ '{secret}' В ОТКРЫТЫЙ КОД?! ТЫ БРОСИЛ КЛЮЧИ ОТ РЕСТОРАНА В МУСОРКУ ПОСРЕДИ УЛИЦЫ?!",
            "wildcard_import": "ТЫ СВАЛИЛ ВСЕ ИНГРЕДИЕНТЫ В ОДНУ КАСТРЮЛЮ ЗВЁЗДОЧКОЙ '{stmt}'?! ЭТО ПОМОИ, А НЕ КОД!",
            "sql_injection_risk": "СЫРОЙ SQL СО СТРОКОВОЙ СКЛЕЙКОЙ?! ТЕБЯ ВЗЛОМАЮТ ЧЕРЕЗ 5 СЕКУНД, ИДИОТ-СЭНДВИЧ!",
        },
    },
    "cyber": {
        "name": "КИБЕР-АУДИТОР v9000",
        "title": "Autonomous Code Purge Subroutine",
        "avatar": [
            r"     .----------------.",
            r"    | [0100]    [1011] |",
            r"    |    [ ====== ]    |  <ОБНАРУЖЕНА ДЕГРАДАЦИЯ",
            r"    |    |  SYNC  |    |   БИОЛОГИЧЕСКОГО ИНТЕЛЛЕКТА>",
            r"     '----------------'",
        ],
        "flame_comments": {
            "lazy_name": "Идентификатор '{name}' нарушает энтропию кодовой базы на 84.7%.",
            "todo": "Нерешенная директива '{text}'. Вероятность исправления биологическим носителем: 0.001%.",
            "debug": "Телеметрический мусор '{text}'. Прямое замусоривание стандартного потока вывода.",
            "swallowed_error": "Аномалия: деструктивный перехват исключения без логирования. Угроза стабильности ядра.",
            "magic_number": "Константа {val} не документирована в семантическом регистре.",
            "lazy_commit": "Символьная строка '{msg}' не несет смысловой нагрузки. Зафиксирован когнитивный отказ.",
            "zombie_code": "Обнаружены мертвые байты в виде комментариев. Рекомендуется протокол аннигиляции.",
            "hardcoded_secrets": "Критическая уязвимость: открытый секрет '{secret}'. Угроза компрометации контура: 100%.",
            "wildcard_import": "Загрязнение пространства имен через '{stmt}'. Нарушена детерминированность резолвинга.",
            "sql_injection_risk": "Обнаружена уязвимость типа SQL Injection: интерполяция входных данных в '{query}'.",
        },
    },
    "teamlead": {
        "name": "Пассивно-Агрессивный Тимлид",
        "title": "Engineering Manager (На созвоне 24/7)",
        "avatar": [
            r"       .--------.",
            r"      /  -   -   \ ",
            r"     |  (•) (•)   |  'Интересное решение...",
            r"     |     ~      |   А ты на прод это сам",
            r"      \   ----   /    деплоить будешь?'",
            r"       '--------'",
        ],
        "flame_comments": {
            "lazy_name": "Переменная '{name}'... Мы же на ретро договаривались называть вещи понятно. Ну ладно, как знаешь.",
            "todo": "'{text}'... Надеюсь, это войдет в текущий спринт, а не как обычно?",
            "debug": "'{text}'... Забыл удалить перед пушем? Ничего страшного, все ошибаются, но осадочек остался.",
            "swallowed_error": "Пустой catch? Смело. Очень смело. Бизнес оценит, когда всё ляжет в пятницу вечером.",
            "magic_number": "Магическое число {val}. Наверное, только ты знаешь, почему именно оно. Гениально.",
            "lazy_commit": "Коммит '{msg}'... Очень подробный changelog, клиенты будут в восторге.",
            "zombie_code": "Закомментировал полфайла? Ну да, git blame же платный стал, надо хранить в файле.",
            "hardcoded_secrets": "Пароль в открытом коде '{secret}'... Это чтобы на онколле быстрее логиниться? Завтра объяснишь службе безопасности.",
            "wildcard_import": "'from ... import *'... Мы же говорили про явные импорты. Теперь в автокомплите каша.",
            "sql_injection_risk": "Инъекция в SQL? Надеюсь, ты сам будешь восстанавливать базу из бэкапа в 3 часа ночи.",
        },
    },
    "junior": {
        "name": "Джуниор Саня",
        "title": "Junior Developer (3 месяца после курсов)",
        "avatar": [
            r"       .--------. ",
            r"      /  o   o   \ ",
            r"     |     ∇      |  'Я не знаю, почему это",
            r"     |   \____/   |   работает, пожалуйста,",
            r"      \          /    НЕ ТРОГАЙТЕ НИЧЕГО!'",
            r"       '--------' ",
        ],
        "flame_comments": {
            "lazy_name": "Переменная '{name}'... О, я тоже так называю, когда не знаю, что писать! Брат!",
            "todo": "TODO '{text}'? Да и ладно, потом кто-нибудь починит... наверное.",
            "debug": "'{text}'! Я так дебажу всё подряд! Без принтов код вообще не понятен!",
            "swallowed_error": "Пустой except? О, отличный трюк, теперь ничего не падает!",
            "magic_number": "Число {val}... Ну работает же! Зачем константы выдумывать?",
            "lazy_commit": "Коммит '{msg}'? Коротко и ясно! А что надо было целое сочинение писать?",
            "zombie_code": "Закомментированный код? Не удаляй, вдруг пригодится через 5 лет!",
            "hardcoded_secrets": "О, пароль прямо тут! Удобно же, не надо переменные окружения настраивать!",
            "wildcard_import": "Импорт всего сразу! Зато всё под рукой и не надо вспоминать, что откуда брать!",
            "sql_injection_risk": "Склеил строки и работает! А что такое эти ваши prepared statements?",
        },
    },
}

# Расширения файлов для сканирования
SOURCE_EXTENSIONS = {
    ".py", ".go", ".rs", ".js", ".ts", ".jsx", ".tsx",
    ".c", ".cpp", ".h", ".hpp", ".java", ".kt", ".dart",
    ".cs", ".php", ".rb", ".swift", ".sh", ".sql"
}

IGNORED_DIRS = {
    ".git", "node_modules", "target", "venv", ".venv",
    "dist", "build", "__pycache__", ".idea", ".vscode", "vendor"
}

# Регулярные выражения для поиска типовых грехов
RE_LAZY_VARS = re.compile(r"\b(let|var|const|def|int|float|auto|val)\s+([a-zA-Z_]\w*)", re.IGNORECASE)
RE_BARE_ASSIGN = re.compile(r"^\s*([a-zA-Z_]\w*)\s*=[^=]", re.IGNORECASE)
BAD_VAR_NAMES = {
    "a", "b", "c", "x", "y", "z", "temp", "tmp", "data", "data2", "test",
    "test1", "temp2", "foo", "bar", "baz", "kek", "lol", "val", "num",
    "res", "ret", "obj", "flag", "flag2", "asdf", "qwerty", "item2"
}

RE_TODO = re.compile(r"(//|#|/\*|--)\s*(TODO|FIXME|HACK|XXX|BUG)\b[:\s]*(.*)", re.IGNORECASE)
RE_DEBUG_PRINTS = re.compile(r"\b(console\.log|print|println|fmt\.Print(ln|f)?|dbg!|System\.out\.print(ln)?)\s*\(", re.IGNORECASE)
RE_SWALLOWED_ERROR = re.compile(r"(except\s*:\s*pass|catch\s*\([^\)]*\)\s*\{\s*\}|_,\s*_\s*=\s*\w+|catch\s*\{\s*\})")
RE_ZOMBIE_CODE = re.compile(r"^\s*(//|#)\s*(if|for|while|return|function|def|var|let|const|class)\b")

# Новые регулярные выражения
RE_MAGIC_NUMBER = re.compile(r"(?:==|!=|[=+\-*/<>])\s*([0-9]{3,7})\b")
SAFE_NUMBERS = {100, 200, 201, 204, 301, 302, 400, 401, 403, 404, 500, 502, 503, 1000, 1024, 2048, 4096, 8192}

RE_HARDCODED_SECRETS = re.compile(
    r"""(?i)\b(api[_-]?key|secret|password|passwd|auth[_-]?token|access[_-]?token|private[_-]?key)\s*[:=]\s*["']([^"'\s]{8,})["']"""
)
RE_BEARER_TOKEN = re.compile(r"""(?i)["']Bearer\s+([A-Za-z0-9_\-\.]{20,})["']""")

RE_WILDCARD_IMPORT = re.compile(r"(from\s+[\w\.]+\s+import\s+\*|import\s+\*\s+as\b|using\s+namespace\s+\w+;)")

RE_SQL_INJECTION = re.compile(
    r"""(?i)(f["'].*?\b(SELECT|INSERT|UPDATE|DELETE)\b|\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b.*(\+|%|\.format|\{))"""
)


def scan_file(file_path: Path, personality: dict) -> list[RoastIssue]:
    issues = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return issues

    comments = personality["flame_comments"]
    lines = content.splitlines()

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        # 1. Поиск странного / ленивого нейминга
        found_name = None
        var_match = RE_LAZY_VARS.search(line)
        if var_match and var_match.group(2).lower() in BAD_VAR_NAMES:
            found_name = var_match.group(2)
        else:
            assign_match = RE_BARE_ASSIGN.search(line)
            if assign_match and assign_match.group(1).lower() in BAD_VAR_NAMES:
                found_name = assign_match.group(1)

        if found_name:
            issues.append(RoastIssue(
                file_path=str(file_path),
                line_number=idx,
                line_content=stripped,
                rule_name="Нейминг от бога 🤡",
                severity=3,
                comment=comments["lazy_name"].format(name=found_name)
            ))

        # 2. Поиск вечных TODO / FIXME
        todo_match = RE_TODO.search(line)
        if todo_match:
            todo_text = todo_match.group(3).strip()[:40] or "Без описания"
            issues.append(RoastIssue(
                file_path=str(file_path),
                line_number=idx,
                line_content=stripped,
                rule_name="Вечный TODO 📜",
                severity=2,
                comment=comments["todo"].format(text=todo_text)
            ))

        # 3. Отладочный вывод, забытый перед коммитом
        if RE_DEBUG_PRINTS.search(line):
            if not stripped.startswith(("//", "#", "/*", "*")):
                issues.append(RoastIssue(
                    file_path=str(file_path),
                    line_number=idx,
                    line_content=stripped,
                    rule_name="Отладочный спам 🗑️",
                    severity=3,
                    comment=comments["debug"].format(text=stripped[:30])
                ))

        # 4. Проглоченные ошибки (однострочные и двухстрочные)
        is_swallowed = False
        if RE_SWALLOWED_ERROR.search(line):
            is_swallowed = True
        elif stripped in ("except:", "except Exception:", "except BaseException:") and idx < len(lines):
            next_line = lines[idx].strip()
            if next_line == "pass":
                is_swallowed = True

        if is_swallowed:
            issues.append(RoastIssue(
                file_path=str(file_path),
                line_number=idx,
                line_content=stripped,
                rule_name="Проглоченная ошибка 🦹",
                severity=5,
                comment=comments["swallowed_error"]
            ))

        # 5. Код-зомби (закомментированный код)
        if RE_ZOMBIE_CODE.search(line):
            issues.append(RoastIssue(
                file_path=str(file_path),
                line_number=idx,
                line_content=stripped,
                rule_name="Код-зомби 🧟",
                severity=2,
                comment=comments["zombie_code"]
            ))

        # 6. Магические числа без констант
        if not stripped.startswith(("//", "#", "/*", "*")):
            num_match = RE_MAGIC_NUMBER.search(line)
            if num_match:
                val = int(num_match.group(1))
                if val not in SAFE_NUMBERS:
                    issues.append(RoastIssue(
                        file_path=str(file_path),
                        line_number=idx,
                        line_content=stripped,
                        rule_name="Магическое число 🔮",
                        severity=3,
                        comment=comments["magic_number"].format(val=val)
                    ))

        # 7. Хардкоженные секреты и токены
        if not stripped.startswith(("//", "#", "/*", "*")):
            sec_match = RE_HARDCODED_SECRETS.search(line)
            if sec_match:
                key_name = sec_match.group(1)
                issues.append(RoastIssue(
                    file_path=str(file_path),
                    line_number=idx,
                    line_content=stripped,
                    rule_name="Секрет нараспашку 🔓",
                    severity=5,
                    comment=comments["hardcoded_secrets"].format(secret=key_name)
                ))
            elif RE_BEARER_TOKEN.search(line):
                issues.append(RoastIssue(
                    file_path=str(file_path),
                    line_number=idx,
                    line_content=stripped,
                    rule_name="Секрет нараспашку 🔓",
                    severity=5,
                    comment=comments["hardcoded_secrets"].format(secret="Bearer Token")
                ))

        # 8. Импорт со звездочкой (wildcard)
        if not stripped.startswith(("//", "#", "/*", "*")):
            wc_match = RE_WILDCARD_IMPORT.search(line)
            if wc_match:
                issues.append(RoastIssue(
                    file_path=str(file_path),
                    line_number=idx,
                    line_content=stripped,
                    rule_name="Импорт-свалка 🌌",
                    severity=3,
                    comment=comments["wildcard_import"].format(stmt=wc_match.group(1))
                ))

        # 9. Потенциальная SQL-инъекция со строковой конкатенацией
        if not stripped.startswith(("//", "#", "/*", "*")):
            sql_match = RE_SQL_INJECTION.search(line)
            if sql_match:
                issues.append(RoastIssue(
                    file_path=str(file_path),
                    line_number=idx,
                    line_content=stripped,
                    rule_name="Дыра в SQL 💉",
                    severity=5,
                    comment=comments["sql_injection_risk"].format(query=stripped[:35])
                ))

    return issues


def scan_git_history(repo_dir: Path, personality: dict, limit: int = 15) -> list[RoastIssue]:
    """Анализ последних коммит-сообщений в репозитории."""
    issues = []
    lazy_commits = {"fix", "upd", "update", "test", "asdf", "wip", "commit", "1", "q", "fixed", "changes", "patch"}
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_dir), "log", f"-n{limit}", "--oneline"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines():
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    hash_val, msg = parts
                    clean_msg = msg.strip().lower()
                    if clean_msg in lazy_commits or len(clean_msg) <= 3:
                        issues.append(RoastIssue(
                            file_path=f"Git Commit {hash_val}",
                            line_number=0,
                            line_content=msg,
                            rule_name="Коммит-загадка 🪵",
                            severity=4,
                            comment=personality["flame_comments"]["lazy_commit"].format(msg=msg)
                        ))
    except Exception:
        pass
    return issues


def calculate_flame_score(issues: list[RoastIssue], total_files: int) -> int:
    """Вычисление индекса прожарки (0 до 100)."""
    if total_files == 0:
        return 0
    raw_score = sum(i.severity * 6 for i in issues)
    # Нормализуем по количеству файлов
    normalized = min(100, int(raw_score / max(1, total_files ** 0.5)))
    return normalized


def get_verdict(score: int) -> tuple[str, str]:
    if score == 0:
        return "СВЯТОЙ МОНАХ (0-10)", "Код идеален или проект пустой. Придраться не к чему, аж скучно."
    elif score <= 25:
        return "ЛЕГКИЙ ДЫМОК (11-25)", "Жить можно. Пара костылей для душевного тепла присутствуют."
    elif score <= 55:
        return "УВЕРЕННЫЙ ШАШЛЫЧОК (26-55)", "Пахнет жареным, но компилируется. Рефакторинг плачет в углу."
    elif score <= 80:
        return "ПОЖАР НА СКЛАДЕ ФЕЙЕРВЕРКОВ (56-80)", "Кто тебя пустил в прод?! Каждая третья строка кричит о помощи."
    else:
        return "ЧЕРНОБЫЛЬ РЕПОЗИТОРИЯ (81-100)", "ТУШИТЕ СВЕТ! Немедленно отойди от клавиатуры и покайся!"


def render_terminal_report(issues: list[RoastIssue], personality: dict, flame_score: int, total_files: int) -> str:
    lines = []
    p_name = personality["name"]
    p_title = personality["title"]
    avatar = personality["avatar"]
    verdict_title, verdict_desc = get_verdict(flame_score)

    lines.append("\n" + "═" * 68)
    lines.append(" 🔥 CODE ROASTER — СЕССИЯ ПРОЖАРКИ КОДА")
    lines.append("═" * 68)

    for a_line in avatar:
        lines.append(f"  {a_line}")
    lines.append(f"\n  Ревьюер: {p_name} | {p_title}")
    lines.append("═" * 68)

    # Прогресс-бар прожарки
    bar_width = 24
    filled = int((flame_score / 100) * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    lines.append(f"\n  ИНДЕКС ПРОЖАРКИ: [{bar}] {flame_score}/100")
    lines.append(f"  ВЕРДИКТ:         {verdict_title}")
    lines.append(f"  ИТОГ:            \"{verdict_desc}\"")
    lines.append(f"  ПРОВЕРЕНО:       {total_files} файлов | НАЙДЕНО ЗАМЕЧАНИЙ: {len(issues)}\n")

    if not issues:
        lines.append("  🎉 Поздравляем! Ни одного очевидного костыля не обнаружено.")
        lines.append("     Либо код писал гений, либо ревьюер ещё не выпил утренний кофе.\n")
        lines.append("═" * 68 + "\n")
        return "\n".join(lines)

    lines.append("─" * 68)
    lines.append(" 📋 СПИСОК ВЫЯВЛЕННЫХ ПРЕСТУПЛЕНИЙ ПРОТИВ ЧИСТОГО КОДА:")
    lines.append("─" * 68)

    sorted_issues = sorted(issues, key=lambda x: x.severity, reverse=True)
    display_issues = sorted_issues[:15]

    for idx, issue in enumerate(display_issues, 1):
        loc = f"{issue.file_path}:{issue.line_number}" if issue.line_number > 0 else issue.file_path
        lines.append(f"\n  #{idx} [{issue.rule_name}] ── {loc}")
        if issue.line_content:
            lines.append(f"      Код:    `{issue.line_content}`")
        lines.append(f"      Вердикт: {issue.comment}")

    if len(sorted_issues) > 15:
        lines.append(f"\n  ...и ещё {len(sorted_issues) - 15} замечаний скрыто из гуманных соображений.")

    lines.append("\n" + "═" * 68 + "\n")
    return "\n".join(lines)


def render_markdown_report(issues: list[RoastIssue], personality: dict, flame_score: int, total_files: int) -> str:
    p_name = personality["name"]
    p_title = personality["title"]
    verdict_title, verdict_desc = get_verdict(flame_score)
    bar_width = 20
    filled = int((flame_score / 100) * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    md = []
    md.append("# 🔥 Code Roaster Report")
    md.append("")
    md.append(f"> **Ревьюер:** {p_name} ({p_title})  ")
    md.append(f"> **Индекс прожарки:** `[{bar}]` **{flame_score}/100** — *{verdict_title}*  ")
    md.append(f"> **Вердикт:** *\"{verdict_desc}\"*")
    md.append("")
    md.append("## 📊 Сводка аудита")
    md.append(f"- **Проверено файлов:** `{total_files}`")
    md.append(f"- **Найдено замечаний:** `{len(issues)}`")
    md.append("")

    if not issues:
        md.append("🎉 **Замечаний не обнаружено!** Кодовая база чиста.")
        md.append("")
        md.append("---")
        md.append("*Отчет сформирован с помощью [Code Roaster](https://github.com/kemranbatcaev02-gif/code-roaster)*")
        return "\n".join(md)

    md.append("## 📋 Список замечаний")
    md.append("| # | Важность | Правило | Файл / Строка | Фрагмент кода | Комментарий ревьюера |")
    md.append("|---|:---:|---|---|---|---|")

    sorted_issues = sorted(issues, key=lambda x: x.severity, reverse=True)
    for idx, issue in enumerate(sorted_issues, 1):
        loc = f"`{issue.file_path}:{issue.line_number}`" if issue.line_number > 0 else f"`{issue.file_path}`"
        severity_icons = "🔥" * issue.severity
        code_snip = f"`{issue.line_content[:45]}`" if issue.line_content else "-"
        comment = issue.comment.replace("|", "\\|")
        md.append(f"| {idx} | {severity_icons} | {issue.rule_name} | {loc} | {code_snip} | {comment} |")

    md.append("")
    md.append("---")
    md.append("*Отчет сформирован с помощью [Code Roaster](https://github.com/kemranbatcaev02-gif/code-roaster)*")
    return "\n".join(md)


def render_html_report(issues: list[RoastIssue], personality: dict, flame_score: int, total_files: int) -> str:
    p_name = html.escape(personality["name"])
    p_title = html.escape(personality["title"])
    verdict_title, verdict_desc = get_verdict(flame_score)
    verdict_title = html.escape(verdict_title)
    verdict_desc = html.escape(verdict_desc)

    sorted_issues = sorted(issues, key=lambda x: x.severity, reverse=True)
    issues_rows = []
    for idx, issue in enumerate(sorted_issues, 1):
        loc = html.escape(f"{issue.file_path}:{issue.line_number}" if issue.line_number > 0 else issue.file_path)
        rule = html.escape(issue.rule_name)
        code = html.escape(issue.line_content)
        comm = html.escape(issue.comment)
        sev_flames = "🔥" * issue.severity
        issues_rows.append(f"""
        <tr>
            <td class="num">#{idx}</td>
            <td class="sev">{sev_flames}</td>
            <td class="rule">{rule}</td>
            <td class="loc"><code>{loc}</code></td>
            <td class="code"><code>{code}</code></td>
            <td class="comm">{comm}</td>
        </tr>
        """)

    table_content = "".join(issues_rows) if issues_rows else "<tr><td colspan='6' class='clean'>🎉 Код чист! Замечаний не обнаружено.</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Roaster Report 🔥</title>
    <style>
        :root {{
            --bg: #0d1117;
            --card-bg: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-bright: #f0f6fc;
            --flame: #ff5500;
            --flame-yellow: #ffb800;
            --accent: #58a6ff;
        }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 30px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: var(--text-bright);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .reviewer-card {{
            color: var(--accent);
            font-size: 1.05em;
            margin-bottom: 16px;
        }}
        .meter-container {{
            background: #21262d;
            border-radius: 8px;
            overflow: hidden;
            height: 24px;
            margin: 16px 0;
            position: relative;
        }}
        .meter-bar {{
            background: linear-gradient(90deg, #ffb800, #ff5500, #ff0055);
            height: 100%;
            width: {flame_score}%;
            transition: width 0.5s ease-in-out;
        }}
        .meter-label {{
            position: absolute;
            top: 2px;
            left: 12px;
            font-weight: bold;
            font-size: 14px;
            color: #fff;
            text-shadow: 1px 1px 2px #000;
        }}
        .verdict {{
            background: rgba(255, 85, 0, 0.1);
            border-left: 4px solid var(--flame);
            padding: 12px 16px;
            border-radius: 4px;
            font-size: 1.1em;
            color: var(--text-bright);
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        .stat-val {{
            font-size: 2em;
            font-weight: bold;
            color: var(--flame-yellow);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            margin-top: 16px;
        }}
        th, td {{
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        th {{
            background: #21262d;
            color: var(--text-bright);
            font-weight: 600;
        }}
        tr:hover {{
            background: #1c2128;
        }}
        code {{
            background: rgba(110, 118, 129, 0.4);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
            font-size: 12px;
            word-break: break-all;
        }}
        .clean {{
            text-align: center;
            padding: 40px;
            font-size: 1.2em;
            color: #3fb950;
        }}
        footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 12px;
            color: #8b949e;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔥 Code Roaster Audit Report</h1>
            <div class="reviewer-card">Ревьюер: <strong>{p_name}</strong> | <em>{p_title}</em></div>
            <div class="meter-container">
                <div class="meter-bar"></div>
                <div class="meter-label">Индекс прожарки: {flame_score} / 100</div>
            </div>
            <div class="verdict">
                <strong>{verdict_title}:</strong> "{verdict_desc}"
            </div>
        </header>

        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-val">{total_files}</div>
                <div>Файлов проверено</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{len(issues)}</div>
                <div>Найдено замечаний</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{flame_score}%</div>
                <div>Уровень деградации</div>
            </div>
        </div>

        <h2>📋 Список обнаруженных антипаттернов</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Строгость</th>
                    <th>Категория</th>
                    <th>Файл : Строка</th>
                    <th>Код</th>
                    <th>Комментарий</th>
                </tr>
            </thead>
            <tbody>
                {table_content}
            </tbody>
        </table>

        <footer>
            Сгенерировано утилитой Code Roaster • Kemran
        </footer>
    </div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(
        description="Code Roaster 🔥 — Ироничный CLI-ревьюер кода в терминале"
    )
    parser.add_argument("path", nargs="?", default=".", help="Файл или папка для прожарки (по умолчанию: текущая папка)")
    parser.add_argument("--persona", choices=["senior", "ramsay", "cyber", "teamlead", "junior"], default="senior", help="Выбор личности ревьюера")
    parser.add_argument("--git", action="store_true", help="Также прожарить историю git-коммитов")
    parser.add_argument("--ext", nargs="+", help="Пользовательский список расширений (например: .py .go .rs)")
    parser.add_argument("--format", choices=["terminal", "json", "markdown", "html"], default="terminal", help="Формат вывода отчета (по умолчанию: terminal)")
    parser.add_argument("--json", action="store_true", help="Вывести отчет в машинно-читаемом формате JSON (эквивалентно --format json)")
    parser.add_argument("--markdown", action="store_true", help="Вывести отчет в формате GitHub Markdown (эквивалентно --format markdown)")
    parser.add_argument("--html", action="store_true", help="Вывести отчет в формате HTML (эквивалентно --format html)")
    parser.add_argument("-o", "--output", help="Путь к файлу для сохранения отчета (если не указан, выводится в stdout)")
    parser.add_argument("--min-severity", type=int, choices=[1, 2, 3, 4, 5], default=None, help="Фильтр минимальной строгости замечаний (1-5)")
    parser.add_argument("--max-score", type=int, default=None, help="Максимально допустимый Flame Score для CI/CD (если превышен, код завершения 1)")

    args = parser.parse_args()
    target_path = Path(args.path).resolve()
    personality = PERSONALITIES[args.persona]

    if not target_path.exists():
        print(f"❌ Ошибка: Путь '{target_path}' не существует.")
        sys.exit(1)

    allowed_exts = set(args.ext) if args.ext else SOURCE_EXTENSIONS

    files_to_scan = []
    if target_path.is_file():
        files_to_scan.append(target_path)
    else:
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                p = Path(root) / file
                if p.suffix.lower() in allowed_exts:
                    files_to_scan.append(p)

    all_issues = []
    for f in files_to_scan:
        all_issues.extend(scan_file(f, personality))

    if args.git or (target_path / ".git").exists():
        all_issues.extend(scan_git_history(target_path, personality))

    if args.min_severity is not None:
        all_issues = [i for i in all_issues if i.severity >= args.min_severity]

    score = calculate_flame_score(all_issues, len(files_to_scan))

    # Определяем формат вывода
    output_format = args.format
    if args.json:
        output_format = "json"
    elif args.markdown:
        output_format = "markdown"
    elif args.html:
        output_format = "html"

    result_text = ""
    if output_format == "json":
        output_data = {
            "persona": args.persona,
            "flame_score": score,
            "total_files": len(files_to_scan),
            "total_issues": len(all_issues),
            "issues": [i.to_dict() for i in all_issues],
        }
        result_text = json.dumps(output_data, ensure_ascii=False, indent=2)
    elif output_format == "markdown":
        result_text = render_markdown_report(all_issues, personality, score, len(files_to_scan))
    elif output_format == "html":
        result_text = render_html_report(all_issues, personality, score, len(files_to_scan))
    else:
        result_text = render_terminal_report(all_issues, personality, score, len(files_to_scan))

    if args.output:
        try:
            out_file = Path(args.output).resolve()
            out_file.write_text(result_text, encoding="utf-8")
            print(f"✅ Отчет успешно сохранен в файл: {out_file}")
        except Exception as e:
            print(f"❌ Ошибка записи в файл '{args.output}': {e}")
            sys.exit(1)
    else:
        print(result_text)

    # Проверка допустимого порога для CI/CD
    if args.max_score is not None and score > args.max_score:
        print(f"\n🚨 CI/CD Gate Failed: Flame Score {score} превышает лимит {args.max_score}!")
        sys.exit(1)


if __name__ == "__main__":
    main()
