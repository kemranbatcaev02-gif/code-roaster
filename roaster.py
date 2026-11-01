#!/usr/bin/env python3
"""
Code Roaster 🔥
Ироничный CLI-ревьюер кода в терминале: находит костыли, странный нейминг и едко их прожаривает.
"""

import argparse
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
        },
    },
}

# Расширения файлов для сканирования
SOURCE_EXTENSIONS = {
    ".py", ".go", ".rs", ".js", ".ts", ".jsx", ".tsx",
    ".c", ".cpp", ".h", ".hpp", ".java", ".kt", ".dart",
    ".cs", ".php", ".rb", ".swift", ".sh"
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


def render_terminal_report(issues: list[RoastIssue], personality: dict, flame_score: int, total_files: int):
    p_name = personality["name"]
    p_title = personality["title"]
    avatar = personality["avatar"]
    verdict_title, verdict_desc = get_verdict(flame_score)

    print("\n" + "═" * 68)
    print(f" 🔥 CODE ROASTER — СЕССИЯ ПРОЖАРКИ КОДА")
    print("═" * 68)

    for line in avatar:
        print(f"  {line}")
    print(f"\n  Ревьюер: {p_name} | {p_title}")
    print("═" * 68)

    # Прогресс-бар прожарки
    bar_width = 24
    filled = int((flame_score / 100) * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"\n  ИНДЕКС ПРОЖАРКИ: [{bar}] {flame_score}/100")
    print(f"  ВЕРДИКТ:         {verdict_title}")
    print(f"  ИТОГ:            \"{verdict_desc}\"")
    print(f"  ПРОВЕРЕНО:       {total_files} файлов | НАЙДЕНО ЗАМЕЧАНИЙ: {len(issues)}\n")

    if not issues:
        print("  🎉 Поздравляем! Ни одного очевидного костыля не обнаружено.")
        print("     Либо код писал гений, либо ревьюер ещё не выпил утренний кофе.\n")
        print("═" * 68 + "\n")
        return

    print("─" * 68)
    print(" 📋 СПИСОК ВЫЯВЛЕННЫХ ПРЕСТУПЛЕНИЙ ПРОТИВ ЧИСТОГО КОДА:")
    print("─" * 68)

    # Показываем до 15 самых сочных замечаний
    sorted_issues = sorted(issues, key=lambda x: x.severity, reverse=True)
    display_issues = sorted_issues[:15]

    for idx, issue in enumerate(display_issues, 1):
        loc = f"{issue.file_path}:{issue.line_number}" if issue.line_number > 0 else issue.file_path
        print(f"\n  #{idx} [{issue.rule_name}] ── {loc}")
        if issue.line_content:
            print(f"      Код:    `{issue.line_content}`")
        print(f"      Вердикт: {issue.comment}")

    if len(sorted_issues) > 15:
        print(f"\n  ...и ещё {len(sorted_issues) - 15} замечаний скрыто из гуманных соображений.")

    print("\n" + "═" * 68 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Code Roaster 🔥 — Ироничный CLI-ревьюер кода в терминале"
    )
    parser.add_argument("path", nargs="?", default=".", help="Файл или папка для прожарки (по умолчанию: текущая папка)")
    parser.add_argument("--persona", choices=["senior", "ramsay", "cyber", "teamlead", "junior"], default="senior", help="Выбор личности ревьюера")
    parser.add_argument("--git", action="store_true", help="Также прожарить историю git-коммитов")
    parser.add_argument("--ext", nargs="+", help="Пользовательский список расширений (например: .py .go .rs)")
    parser.add_argument("--json", action="store_true", help="Вывести отчет в машинно-читаемом формате JSON")
    parser.add_argument("--min-severity", type=int, choices=[1, 2, 3, 4, 5], default=None, help="Фильтр минимальной строгости замечаний (1-5)")

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

    if args.json:
        output_data = {
            "persona": args.persona,
            "flame_score": score,
            "total_files": len(files_to_scan),
            "total_issues": len(all_issues),
            "issues": [i.to_dict() for i in all_issues],
        }
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
        return

    render_terminal_report(all_issues, personality, score, len(files_to_scan))


if __name__ == "__main__":
    main()
