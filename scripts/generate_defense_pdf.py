from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "defense.pdf"
FONT_DIR = Path(r"C:\Windows\Fonts")

pdfmetrics.registerFont(TTFont("Arial", str(FONT_DIR / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_DIR / "arialbd.ttf")))

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="TitleRu",
        parent=styles["Title"],
        fontName="Arial-Bold",
        fontSize=24,
        leading=29,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#16324F"),
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="SubtitleRu",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=12,
        leading=17,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4C6272"),
        spaceAfter=18,
    )
)
styles.add(
    ParagraphStyle(
        name="H1Ru",
        parent=styles["Heading1"],
        fontName="Arial-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#16324F"),
        spaceBefore=12,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="H2Ru",
        parent=styles["Heading2"],
        fontName="Arial-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#176B87"),
        spaceBefore=8,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyRu",
        parent=styles["BodyText"],
        fontName="Arial",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#202A30"),
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="SmallRu",
        parent=styles["BodyText"],
        fontName="Arial",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#56636B"),
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="BulletRu",
        parent=styles["BodyText"],
        fontName="Arial",
        fontSize=10.5,
        leading=15,
        leftIndent=13,
        firstLineIndent=-8,
        bulletIndent=0,
        textColor=colors.HexColor("#202A30"),
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="CodeRu",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        backColor=colors.HexColor("#F2F5F6"),
        borderColor=colors.HexColor("#D7E0E4"),
        borderWidth=0.5,
        borderPadding=7,
        spaceBefore=4,
        spaceAfter=8,
    )
)


def p(text: str, style: str = "BodyRu"):
    return Paragraph(text, styles[style])


def bullet(text: str):
    return Paragraph(f"• {text}", styles["BulletRu"])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E0E4"))
    canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
    canvas.setFont("Arial", 8)
    canvas.setFillColor(colors.HexColor("#68757D"))
    canvas.drawString(18 * mm, 9 * mm, "Colorist Assistant — материалы к защите")
    canvas.drawRightString(192 * mm, 9 * mm, f"{doc.page}")
    canvas.restoreState()


story = []
story += [
    Spacer(1, 28 * mm),
    p("Защита проекта", "TitleRu"),
    p("Colorist Assistant — ИИ-ассистент колориста", "SubtitleRu"),
    HRFlowable(width="70%", thickness=1.3, color=colors.HexColor("#2D8CA8"), hAlign="CENTER"),
    Spacer(1, 12 * mm),
    p("Готовый текст выступления, сценарий демонстрации и ответы на вопросы комиссии.", "BodyRu"),
    p("Версия подготовлена по текущей реализации проекта: Python, FastAPI, rule-based калькулятор, профили Wella, веб-интерфейс и отдельный ИИ-ассистент.", "SmallRu"),
    PageBreak(),
]

story += [p("1. Текст выступления", "H1Ru")]
speech = [
    "Здравствуйте. Тема моего проекта — «ИИ-ассистент колориста для расчёта и проверки формул окрашивания волос».",
    "Проблема проекта заключается в том, что при подборе формулы мастер должен учитывать исходный уровень волос, длину, процент седины, желаемое направление оттенка, бренд и линию красителя. Ошибка в одном из параметров может привести к неправильному покрытию седины, выбору неподходящего оксида или нежелательному оттенку.",
    "Цель проекта — создать MVP-систему, которая помогает мастеру рассчитать формулу окрашивания, объясняет решение по правилам и проверяет уже готовую формулу на возможные риски.",
    "В проекте реализованы два основных режима. Первый — расчёт формулы. Пользователь указывает исходное состояние волос, желаемый уровень и направление оттенка. Система рассчитывает компоненты формулы, количество красителя, процент оксида, соотношение компонентов и время выдержки.",
    "Второй режим — проверка формулы мастера. Пользователь вводит уже выбранные оттенки и оксид, а система проверяет их по тем же правилам и показывает потенциальные проблемы.",
    "Основой проекта является детерминированный rule-based движок. Формула не придумывается языковой моделью. Она рассчитывается программными правилами, поэтому одинаковые входные данные дают одинаковый результат. Каждый шаг расчёта связан с идентификатором правила, например правилом определения уровня, покрытия седины или выбора оксида. Это делает результат объяснимым и проверяемым.",
    "Поддерживаются универсальный профиль и линии Wella: Koleston Perfect, Illumina Color и Color Touch. Также реализован зональный расчёт для случаев, когда корни и длина требуют разных параметров.",
    "ИИ-ассистент является отдельным модулем. Его задача — объяснить уже рассчитанную формулу простым языком и помочь мастеру разобраться в ситуации. Он не является источником самой формулы и не должен самостоятельно менять результат калькулятора. При отсутствии API-ключа приложение продолжает работать в демонстрационном режиме.",
    "Приложение реализовано на Python с использованием FastAPI. Веб-интерфейс обращается к API. Основные маршруты — получение списка брендов, расчёт формулы, проверка формулы, чат с ассистентом и health-check.",
    "Для проверки проекта написаны автоматические тесты. Сейчас проходят 70 тестов. Дополнительно есть сценарии оценки на 13 примерах. В отчёте отдельно отмечены случаи, которые пока не входят в границы MVP, например осветление и некоторые сложные реальные формулы.",
    "Границы MVP определены специально. Система не выполняет полноценное осветление, не заменяет профессионального колориста, не заменяет тест на аллергию и требует сверки правил с техническими картами конкретного бренда. Поэтому проект предназначен как вспомогательный инструмент для расчёта и проверки, а не как автономная система принятия профессионального решения.",
    "В результате получено рабочее веб-приложение с расчётом, проверкой, объяснением результата, поддержкой брендов, тестами и документацией. Следующим этапом развития будет подтверждение правил практикующими колористами, расширение проверенных кейсов, добавление аутентификации и защиты API.",
]
for paragraph in speech:
    story.append(p(paragraph))

story += [p("2. Сценарий демонстрации", "H1Ru")]
story += [p("Запуск", "H2Ru"), Preformatted("cd C:\\colorist-assistant\n.\\.venv\\Scripts\\Activate.ps1\nuvicorn colorist.api.main:app --reload", styles["CodeRu"])]
story += [p("Открыть в браузере", "H2Ru"), p("http://127.0.0.1:8000/ — веб-интерфейс; http://127.0.0.1:8000/docs — Swagger API; http://127.0.0.1:8000/health — проверка состояния.")]
story += [p("Основной расчёт", "H2Ru")]
for text in [
    "Выбрать Wella и линию Koleston Perfect.",
    "Исходный уровень корней и длины: 7.",
    "Седина: 30 процентов.",
    "Направление: холодное; цель: уровень 7, оттенок 7/1.",
    "Показать результат: 7/0 — 30 г, 7/1 — 70 г, оксид 6 процентов, соотношение 1:1, выдержка 35 минут.",
    "Показать объяснение, где указаны причины добавления натуральной базы и выбора оксида.",
]:
    story.append(bullet(text))
story += [p("Проверка формулы мастера", "H2Ru")]
for text in [
    "Указать седину 30 процентов и холодное направление.",
    "Ввести формулу 7/3 — 60 г и оксид 3 процента.",
    "Показать найденные риски: нет натуральной базы, оксид не соответствует задаче, выбран тёплый нюанс вместо холодного.",
]:
    story.append(bullet(text))
story += [p("Проверка тестами", "H2Ru"), Preformatted("python -m pytest -q\npython scripts\\evaluate.py", styles["CodeRu"])]
story.append(p("Фраза для пояснения отчёта: «Неподдерживаемые сценарии, например осветление, явно помечаются как ограничение MVP, чтобы система не выдавала неподтверждённую формулу»."))

story += [PageBreak(), p("3. Что показать в коде", "H1Ru")]
files = [
    ("colorist/brands/engine.py", "Основной расчёт формул и зональный режим."),
    ("colorist/brands/wella.py", "Профили линий Wella и их параметры."),
    ("colorist/rules/knowledge.py", "Правила с идентификаторами для объяснимости."),
    ("colorist/api/main.py", "FastAPI-маршруты и валидация входных данных."),
    ("colorist/api/static/index.html", "Пользовательский веб-интерфейс."),
    ("colorist/api/assistant.py", "ИИ-ассистент, кэширование и demo fallback."),
    ("tests/", "Автоматические тесты расчётов, API, брендов и ассистента."),
    ("docs/evaluation/report.md", "Отчёт по 13 эталонным сценариям и ограничениям."),
]
table_data = [[p("Файл", "SmallRu"), p("Что объяснить", "SmallRu")]]
for path, description in files:
    table_data.append([p(f"<font name='Courier'>{path}</font>", "SmallRu"), p(description, "SmallRu")])
table = Table(table_data, colWidths=[72 * mm, 102 * mm], repeatRows=1)
table.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEEF2")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B9C9CE")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )
)
story.append(table)

story += [p("4. Ответы на вопросы комиссии", "H1Ru")]
answers = [
    ("Почему используется ИИ, если формула рассчитывается правилами?", "ИИ используется для объяснения результата и общения с мастером. Сам расчёт выполняется детерминированным движком, чтобы одинаковые входные данные давали одинаковый результат."),
    ("Что произойдёт без API-ключа OpenAI?", "Калькулятор продолжит работать. Ассистент перейдёт в демонстрационный режим и будет давать ограниченные объяснения на основе рассчитанной формулы."),
    ("Почему система не поддерживает осветление?", "Осветление требует отдельного набора правил, диагностики волос и проверки технических карт. В текущем MVP такой запрос явно отклоняется."),
    ("Можно ли использовать приложение без Wella?", "Да. Есть универсальный профиль. Новые бренды можно добавлять через профиль бренда и набор его параметров."),
    ("Как проверяется качество результата?", "Через автоматические тесты, эталонные кейсы и отдельный отчёт оценки. Неподтверждённые сценарии отмечены отдельно."),
    ("Какие ограничения у проекта?", "Правила требуют проверки практикующими колористами и техническими картами брендов. Приложение не заменяет мастера, инструкцию производителя и тест на аллергию."),
]
for question, answer in answers:
    story.append(p(f"<b>{question}</b>", "BodyRu"))
    story.append(p(answer, "BodyRu"))

story += [p("5. Что было изменено в тексте защиты", "H1Ru")]
for text in [
    "Текст привязан к фактической реализации проекта, а не к общей идее приложения.",
    "Добавлены конкретные режимы работы, API-маршруты, профили Wella и зональный расчёт.",
    "Добавлены реальные результаты проверки: 70 автоматических тестов и 13 оценочных кейсов.",
    "Включён практический сценарий демонстрации с ожидаемыми значениями формулы.",
    "Отдельно объяснено разделение ответственности: правила рассчитывают формулу, ИИ объясняет результат.",
    "Ограничения MVP сформулированы прямо: осветление, доменная валидация, тест на аллергию и защита публичного API.",
]:
    story.append(bullet(text))

story += [Spacer(1, 6 * mm), p("Финальная фраза", "H2Ru"), p("«В проекте создан рабочий MVP ассистента колориста: он рассчитывает и проверяет формулы, объясняет результат, поддерживает несколько линий бренда, имеет API, веб-интерфейс и автоматические тесты. Архитектура позволяет постепенно расширять базу правил после экспертной валидации»."), p("Перед защитой рекомендуется один раз выполнить демонстрацию по этому сценарию и держать открытыми страницу приложения, Swagger и окно терминала с тестами.", "SmallRu")]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=A4,
    rightMargin=18 * mm,
    leftMargin=18 * mm,
    topMargin=17 * mm,
    bottomMargin=19 * mm,
    title="Материалы к защите Colorist Assistant",
    author="Colorist Assistant",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)
