# Правки к учебнику «Siamang User Textbook» — отчёт о проверке корректности

**Дата проверки:** 2026-08-30
**Проверенная рукопись:** Siamang_User_Textbook_Manuscript_Corrected.docx (24 главы + приложения A–C)
**Источники истины:**
- `siamang-labs/siamang` — движок, версия 0.5.0 (пакет установлен, все ключевые примеры кода реально запускались: CLI, simulate, таблицы, графики, экспорт/импорт, deploy local/local end-to-end);
- `hanelias/siamang_cloud` — платформа Siamang Cloud (сверка с кодом api/, web/, worker/, sdk/, db/ и docs/; SDK-примеры установлены и выполнены).

## Итоговая статистика

| Категория | Кол-во |
|---|---|
| **ОШИБКА** (утверждение неверно / код не работает как описано) | 39 |
| **НЕТОЧНОСТЬ** (в целом верно, но детали расходятся с кодом) | 65 |
| **НЕ ПОДТВЕРЖДЕНО** (нет подтверждения в репозиториях / расхождение docs↔код) | 11 |
| **Итого правок** | 115 |

Общая оценка: учебник добротный и в подавляющем большинстве утверждений точен — сигнатуры API, таблицы полей, числовые примеры (частоты, кросстабы, статистики, вывод симуляции) в главах 4–6, 8–9, 13, 15–18 воспроизводятся при реальном запуске вплоть до символа. Главы 8 (квоты) и 13 (симуляция) фактически безупречны. Проблемы концентрируются в предсказуемых местах — см. системные темы ниже.

## Системные темы (важно понять до правок)

Большинство ошибок — не выдумки автора, а честное следование **устаревшей документации**, которая расходится с кодом. Повторяющиеся источники проблем:

1. **`docs/reference/*.md` движка местами отстали от кода** (recode_values, маппинг версий Stata, формат конфига `[profile.default]`, exit-коды CLI). Там, где docs и wiki противоречат друг другу, прав почти всегда код и wiki.
2. **`wiki/Cloud-*.md` движка сильно отстала от кода платформы** siamang_cloud: каталог и гейтинг коннекторов, число скриптов пример-проекта, поведение после триала, Data insights. Главы 20–24 надо править по коду платформы, а не по этой wiki.
3. **Часть задокументированного поведения движка НЕ реализована в рантайме респондента 0.5.0**, а учебник описывает её как рабочую. Это самый серьёзный пласт: роутинг `skip_to`/`next_if`/`default_next` (не сериализуется во фронтенд, рантайм идёт строго последовательно), 4 из 7 script-триггеров (`onPageEnter`, `onPageExit`, `onQuestionShow`, `onRandomize` никогда не вызываются), `randomize`/`randomize_blocks`, `exclusive`/`none_of_above`, `Matrix.subquestions`/`na_option`, строковые условия `show_if="age >= 18"` (в React-рантайме всегда истинны). Рекомендация: снабдить эти разделы явными «Beta limitation»-плашками (или эскалировать авторам движка).
4. **Хрупкие «канонические» примеры**: капстоун-туториал главы 19 не проходит `siamang validate --strict` (LikertScale + interval-шкала → INCOMPATIBLE_QUESTION_SCALE, exit 2), упражнение `Script.randomize_options("q_role")` неисполнимо (id вопроса — `it_role`), пример конфига в Приложении A не читается загрузчиком 0.5.0.

## Топ-10 самых серьёзных правок

1. **Гл. 7.2.2** — роутинг `skip_to`/`next_if` описан как работающий для респондента; в 0.5.0 он существует только в core-модели и валидаторе, фронтенд его не исполняет.
2. **Гл. 8.2.1** — из семи script-триггеров рантайм реально вызывает только `onInit`, `onAnswer`, `onSubmit`; дефолтный `onPageEnter` и фабрики `randomize_options`/`timed_question` не срабатывают.
3. **Гл. 19.2.1 / 19.4** — туториал не проходит `--strict`-валидацию, а упражнение прямо велит её запустить; `randomize_options("q_role")` падает на валидации.
4. **Приложение A.1.3 / A.2** — CLI 0.5.0 не загружает `~/.siamang.toml` автоматически; «канонический» пример конфига в формате `[profile.default]` загрузчиком не читается (правильный формат — `[defaults]/[backends]/[frontends]/[profiles]`, как в Приложении B).
5. **Гл. 14 / 15.3.1** — `recode_values` без `into` НЕ обновляет столбец на месте: всегда создаётся `<column>_recoded`, неперечисленные значения превращаются в NaN; параметра `labels` у метода нет; `create_index(method="sum")` не существует.
6. **Гл. 11.2.1** — basic-линт содержит 11 правил (4 структурных + 7 codebook/logic), а не 4; сценарий с exit-кодом 1 недостижим.
7. **Гл. 23.1 / 24 (FAQ, планы)** — каталог коннекторов: в коде 12 живых экспорт-таргетов + 2 импортёра, «Coming soon» только airtable/dropbox/mcp; гейтинг начинается с Plus (не Pro/Corporate), по-таргетно.
8. **Гл. 20.3.2 / 24 FAQ** — после окончания триала организация понижается до Free и продолжает работать, а не становится read-only.
9. **Гл. 20–22, 24.2.1** — пример-проект «Digital Life & Wellbeing 2026» содержит 2 скрипта (cleaning, tables), а не 4; шага weights нет; Data insights — opt-in через блок `insights:` в siamang.yaml, а не включены по умолчанию.
10. **Гл. 10.2.1** — `survey.deploy()` по умолчанию использует ReactRuntime, а не «default SurveyJS runtime» (SurveyJSRuntime — дефолт только у `FrontendBuilder` напрямую).

Далее — полные списки правок по главам. Формат каждой записи: цитата из учебника → что на самом деле (со ссылкой на файл:строку в репозитории) → конкретная правка. В конце каждого раздела — список утверждений, которые проверены и подтвердились.

---

# Ревью глав 1–3 (введение, установка, quickstart)

Проверка выполнена против /home/user/siamang (пакет siamang 0.5.0, editable): документация (README.md, MANUAL.md, docs/, wiki/, CHANGELOG.md, pyproject.toml) и исходный код; ключевые примеры кода реально запущены (`siamang validate`, `siamang preview`, `simulate()`, `data.report.freq/crosstab`, `data.export(...)`).

## Глава 1, раздел 1.2.1
### [ОШИБКА] Искажена цитата из README про движок и Cloud
- **В учебнике:** «The project's own summary is: "The engine in this repository is source available; the Cloud runs everything around it."»
- **На самом деле:** README.md:50-51 говорит: «The engine in this repository is **open source**; the Cloud runs everything around it.» Формулировка «source available» в документации проекта нигде не встречается (grep по всем .md — ноль совпадений); docs/cloud/terms-of-use.md:6 также называет движок «open-source». (Характеристика «source-available» сама по себе юридически ближе к истине при лицензии PolyForm, но в кавычках как цитата проекта она недопустима.)
- **Правка:** либо привести цитату дословно («The engine in this repository is open source; the Cloud runs everything around it»), при желании с оговоркой автора, что при лицензии PolyForm Noncommercial точнее термин «source-available»; либо убрать кавычки и дать пересказ без атрибуции проекту.

## Глава 1, раздел 1.3.1 (таблица возможностей, строка Data I/O)
### [НЕТОЧНОСТЬ] Round-trip «с сохранением меток» заявлен для всех форматов, но CSV/Excel переносят только данные
- **В учебнике:** «Round-trip import/export for CSV, Excel (.xlsx), SPSS (.sav), Stata (.dta), and R, with labels and missing values preserved.»
- **На самом деле:** так написано в README.md:128, но wiki/Home.md:68 прямо уточняет: «SPSS/Stata round-trip labels and missing values; **CSV/Excel carry data only** (labels via the JSON dictionary)». Код подтверждает: wiki/Data-Import-and-Export.md:60-63 («CSV carries data only. Metadata is not reconstructed»), :89 («Like CSV, Excel I/O carries data only»); CSVWriter/ExcelWriter пишут только data.frame. Метаданные полноценно round-trip'ятся только в SPSS/Stata (pyreadstat), для R — через JSON-словарь + .R-загрузчик.
- **Правка:** уточнить: «SPSS и Stata — полный round-trip с метками и пропусками; CSV/Excel переносят только данные (метки — через сопутствующий JSON-словарь); экспорт в R — CSV + словарь + .R-скрипт».

## Глава 1, раздел 1.1.2 (и Learning Objectives, Chapter Summary)
### [НЕ ПОДТВЕРЖДЕНО] «Пять стадий пайплайна» как канон фреймворка
- **В учебнике:** «Name the five stages of the Siamang pipeline…»; «The pipeline has five stages — validate, preview, deploy, collect, analyze/report».
- **На самом деле:** документация нигде не определяет пайплайн из пяти стадий: docs/index.md:4-6 перечисляет «validate, preview, simulate, deploy, collect, and analyse» (шесть глаголов, включая simulate); wiki/Home.md:4-6 — то же. «Пятёрка» в документации закреплена за другим — «five-layer data model» (wiki/Core-Concepts.md:30-40, модули core/frontend/deploy/data/io), с которой авторская «пятистадийность» легко перепутается (тем более что в 3.3.1 учебник сам говорит о «five layers»).
- **Правка:** либо представить пять стадий явно как авторскую дидактическую схему (не «стадии пайплайна Siamang»), либо перейти на формулу документации (validate → preview → simulate → deploy → collect → analyse), выделив simulate как отдельный шаг.

## Глава 2, раздел 2.2.1
### [НЕТОЧНОСТЬ] «local backend и local frontend не принимают аргументов вовсе»
- **В учебнике:** «the local backend and local frontend take no arguments at all, so a minimal configuration is just [defaults]…»
- **На самом деле:** формулировка взята из wiki/Configuration.md:48 («take no kwargs»), но по коду оба адаптера имеют необязательные параметры: LocalBackend(path="survey.db") — siamang/deploy/backends/local.py:51-60; LocalFrontend(host="0.0.0.0", port=0, open_browser=False) — siamang/deploy/frontends/local.py:216-220. Верно то, что они не **требуют** аргументов (минимальный конфиг — только [defaults]).
- **Правка:** заменить «take no arguments at all» на «не требуют обязательных аргументов» (у локального backend есть необязательный path, по умолчанию survey.db).

## Глава 3, раздел 3.1.2
### [НЕТОЧНОСТЬ] Пример вывода siamang validate не соответствует реальному
- **В учебнике:** «A well-formed questionnaire prints a confirmation along these lines: OK: Questionnaire<Hello, siamang> with 2 questions»
- **На самом деле:** реальный запуск `siamang validate hello.py` на этом же файле печатает `OK — no warnings.` (siamang/cli/validate.py:29-30: `print("OK — no warnings.")`). Строка «OK: Questionnaire<…> with 2 questions» есть только в MANUAL.md:389 и устарела относительно кода. Кроме того, при наличии lint-предупреждений вместо «OK» печатается их список вида `[warning] [code] message`.
- **Правка:** заменить пример вывода на фактический `OK — no warnings.` (можно добавить, что при софт-предупреждениях команда перечислит их построчно); при желании — сноска, что MANUAL показывает старый формат.

## Глава 3, раздел 3.2.1
### [НЕТОЧНОСТЬ] survey ID печатается при старте preview, а не при отправке ответов
- **В учебнике:** «the survey ID appears in the preview server's log when responses are submitted»
- **На самом деле:** ID печатается один раз при запуске сервера: siamang/cli/preview.py:58-59 — `Preview ready at …` / `  survey_id: …` (проверено реальным запуском: вывод появляется до какой-либо отправки). На отправку ответа ничего не логируется (в siamang/deploy/frontends/local.py логирования сабмитов нет; uvicorn запускается с log_level="warning").
- **Правка:** «the survey ID is printed when the preview server starts (line `survey_id: …` under `Preview ready at …`)».

## Глава 3, раздел 3.2.1
### [НЕТОЧНОСТЬ] get_responses возвращает не только колонки-переменные
- **В учебнике:** «The result is a pandas DataFrame — one row per respondent, one column per Variable name.»
- **На самом деле:** siamang/deploy/backends/local.py:155-169 — get_responses() добавляет к payload-колонкам служебные `_response_id` и `_submitted_at`; при отсутствии ответов возвращается пустой DataFrame.
- **Правка:** дополнить: «…плюс служебные колонки `_response_id` и `_submitted_at`».

## Глава 3, раздел 3.2.1 (и Chapter Summary)
### [НЕТОЧНОСТЬ] Round-trip метаданных «в CSV, Excel, SPSS, Stata или R» (повтор проблемы из гл. 1)
- **В учебнике:** «SurveyData.export() round-trips the data with its metadata — variable labels, value labels, missing-value conventions — to CSV, Excel, SPSS, Stata, or R» (и в Summary: «round-trips data and metadata to CSV, Excel, SPSS, Stata, and R»).
- **На самом деле:** экспорт во все пять форматов работает (проверено запуском: hello.csv/.xlsx/.sav/.dta/hello_R/ созданы; R-экспорт = import_survey.csv + import_survey_dictionary.json + import_survey.R), но метаданные встраиваются только в SPSS/Stata; CSV/Excel — только данные (wiki/Data-Import-and-Export.md:60-63, 89), R — через отдельный JSON-словарь.
- **Правка:** та же оговорка, что и в главе 1: полный round-trip метаданных — SPSS/Stata; CSV/Excel — данные без меток; R — метки через словарь и .R-загрузчик.

## Проверено и корректно
- Слоган из README процитирован точно: «Define variables, questionnaires, and logic in pure Python — then deploy, collect, and analyze in a single pipeline» (README.md:4-6); «No GUI builders. No drag-and-drop. No lock-in.» (README.md:40).
- Термины: Variable (шкалы nominal/ordinal/interval/ratio), Question, Page, Questionnaire с validate()/simulate()/deploy() — wiki/Core-Concepts.md, siamang/core/questionnaire.py.
- Семь типов вопросов: SingleChoice, MultiChoice, LikertScale, NumericInput, OpenText, Matrix, Ranking — siamang/__init__.py, wiki/Home.md:63 («7 question types»), MANUAL.md оглавление.
- Все core-датаклассы `frozen=True, slots=True` — 22 объявления в siamang/core/*.py; формулировка про иммутабельность совпадает с wiki/Core-Concepts.md:71-74.
- Версия 0.5.0, дата релиза 2026-05-28, статус Beta — CHANGELOG.md:19, pyproject.toml:7, classifier «Development Status :: 4 - Beta»; sg.__version__ == "0.5.0" (проверено запуском).
- Канонические команды пайплайна из README (pip install siamang; siamang validate/preview/deploy … --backend supabase --frontend vercel) — README.md:17-21.
- Siamang Cloud: open beta, https://app.siamang.org/login, набор возможностей (авторинг в браузере, one-click deploy, сбор, анализ, дашборды, команда) — README.md:45-53.
- Оператор Siamang Labs LLC (Wyoming, USA) — README.md:305; двойное именование репозитория Siamang-Labs/siamang (LICENSE-COMMERCIAL.md:24, docs/cloud/terms-of-use.md) и github.com/hanelias/siamang (pyproject.toml:47, MANUAL.md:39, docs/getting-started.md:8) — подтверждено.
- Двойная лицензия: PolyForm Noncommercial 1.0.0 (LICENSE) + коммерческая через info@siamang-team.org (README.md:295-302, LICENSE-COMMERCIAL.md:22); переход с MIT записан в CHANGELOG [Unreleased], «versions up to and including 0.5.0 remain available under the MIT License» (CHANGELOG.md:12-16).
- Google Sheets backend «experimental» для публичных деплоев — README.md:183.
- Требования: Python 3.11+ (3.11/3.12/3.13 tested), OS-independent, py.typed — pyproject.toml:10,15-27,58; wiki/Installation.md:10-12.
- Таблица core-зависимостей с минимальными версиями (pandas 2.0, scipy 1.11, openpyxl 3.1, pyreadstat 1.2, fastapi 0.110, uvicorn 0.29, markdown 3.5, tabulate 0.9, supabase 2.0, requests 2.31) — pyproject.toml:28-44, wiki/Installation.md:42-53.
- Extras: charts (matplotlib>=3.7, seaborn>=0.13), gsheets (google-auth>=2.0, google-auth-httplib2>=0.1, google-api-python-client>=2.0), dev (ruff>=0.4, mypy>=1.10, pytest>=8.0 + siamang[charts]) — pyproject.toml:64-81; легаси no-op extras all/excel/pyreadstat/server/supabase/vercel/scipy — pyproject.toml:85-91.
- Установка из Git и editable-install `pip install -e ".[dev]"` — wiki/Installation.md:88-97, docs/getting-started.md:8.
- Проверочный сниппет: print(sg.SingleChoice) → `<class 'siamang.core.question.SingleChoice'>` — подтверждено запуском.
- Smoke-тест из wiki/Installation.md:120-131 воспроизведён дословно, работает; simulate(n=50) без сервера, data.frame.head() печатает 5 строк.
- Сообщение об ошибке при графиках без matplotlib существует — siamang/reporting/charts.py:55.
- ~/.siamang.toml: четыре типа таблиц [defaults]/[backends.*]/[frontends.*]/[profiles.*] — wiki/Configuration.md:19-22; пример файла процитирован дословно (wiki/Configuration.md:24-46); siamang init --non-interactive пишет defaults local/local — siamang/cli/init.py:20-27.
- Переменные окружения перекрывают файл (env применяется поверх, побеждает) — siamang/config/loader.py:143-157; префиксы SIAMANG_SUPABASE_/GSHEETS_/VERCEL_/NETLIFY_ и легаси SURVLIB_* — loader.py:130-140; SIAMANG_SUPABASE_URL → backends.supabase["url"] (lowercase-суффикс) — подтверждено.
- VERCEL_TOKEN и NETLIFY_AUTH_TOKEN читаются адаптерами напрямую при пустом token — siamang/deploy/frontends/vercel.py:79, netlify.py:67.
- Права 0600: save()/init делают chmod 0o600 (loader.py:109), load() на POSIX проверяет биты 0o077 и логирует предупреждение с подсказкой chmod 600 (secrets.py:12-28).
- Заявление о двух несовместимых раскладках конфига в документации — верно: wiki/Configuration.md ([profiles.<name>]) vs docs/reference/cli.md:107-178 ([profile.<name>] + backend_kwargs/frontend_kwargs).
- CLI: ровно четыре субкоманды validate/preview/deploy/init — siamang/cli/entry.py; флаги --attribute (default "survey"), --strict; preview: --port (default 8000), --open, --db (default survey.db); deploy: --backend/--frontend/--profile/--config; init: --path/--non-interactive; --help на каждом уровне (argparse).
- hello.py из главы 3 дословно совпадает с docs/getting-started.md:30-51 и работает: `siamang validate hello.py` → OK, preview реально поднимается и отвечает 200 на http://127.0.0.1:<port>, ответы в survey.db.
- validate() в Python: сигнатура (strict: bool = False) -> None, ValueError при проблеме; strict/lint() ловят «мягкие» предупреждения (пустые страницы, категориальные переменные без labels) — wiki/Quickstart.md:47-66, siamang/cli/validate.py.
- Список проверок валидатора (дубли ID, битые навигационные цели, неизвестные переменные в выражениях, скрипты) — MANUAL.md:401-404.
- Опции SingleChoice берутся из labels переменной, если choices не задан — wiki/Question-Types.md:78-81.
- simulate: сигнатура (n: int = 100, seed: int | None = 42) — подтверждено inspect.signature; seed=None даёт свежую случайность — wiki/Quickstart.md:82-83.
- SurveyData = DataFrame (data.frame) + метаданные переменных; data.report.freq("fav_color").to_markdown() выдаёт таблицу с метками Red/Blue/Green (проверено запуском); data.report.crosstab(...) автоматически добавляет χ², df, p и Cramér's V (проверено: «χ² = 10.9670; … Cramér's V = 0.2340»).
- Аксессоры data.report / data.plot / data.analysis существуют (проверено hasattr).
- LocalBackend(path="survey.db").get_responses(survey_id=...) — сигнатура и пример совпадают с MANUAL.md:530-537 и кодом local.py:155.
- Экспорт data.export("csv"/"xlsx"/"spss"/"stata"/"r") работает; для "r" создаётся каталог с CSV + JSON-словарём + .R-загрузчиком, комментарий учебника точен (docs/getting-started.md:94, проверено запуском).
- examples/full_pipeline/ существует: full_pipeline_demo.ipynb + survey_preview.html; описание (12 переменных, 5 страниц, conditional routing, matrix, 250 синтетических респондентов, частотки, кросс-табы, корреляционные heatmap, графики) — README.md:100-114.
- Отсылки Documentation References в конце глав соответствуют реальному содержимому файлов (docs/index.md — пайплайн validate→preview→simulate→deploy→collect→analyse; wiki/Core-Concepts.md — five-layer model, 7 script-триггеров onInit…onRandomize; MANUAL.md — env-переменные, preview-флаги, LICENSE-COMMERCIAL.md).

---

# Ревью глав 4–6 (концепции, Pages/Blocks, типы вопросов)

Проверено против исходников `/home/user/siamang` (пакет siamang 0.5.0, editable). Все примеры кода из глав запускались; результаты запусков учтены ниже.

## Глава 6, раздел 6.1
### [ОШИБКА] Question можно инстанцировать напрямую
- **В учебнике:** «all seven inherit from the abstract base class Question … You never instantiate Question itself — it cannot be constructed directly — but its fields are the shared vocabulary…»
- **На самом деле:** `Question` — обычный (не абстрактный) frozen-датакласс без каких-либо механизмов запрета инстанцирования: `siamang/core/question.py:13-43`. Проверено запуском: `sg.Question("Some text?", var=age)` успешно создаёт объект. Ни wiki/Question-Types.md, ни docs/reference/core.md не называют его абстрактным.
- **Правка:** заменить на «Question — базовый класс, который на практике не используется напрямую (вы всегда создаёте один из семи подклассов)». Убрать «abstract» и «it cannot be constructed directly».

## Глава 5, раздел 5.2.1
### [ОШИБКА] Симуляция НЕ учитывает show_if/hide_if на уровне Block
- **В учебнике:** «…and simulation respects your structure, since invisible questions (including those inside a hidden block) are not sampled.»
- **На самом деле:** `simulate_from_pages()` учитывает только page-level и question-level условия; блоки разворачиваются через `page.flatten_questions()`, и их `show_if`/`hide_if` теряются: `siamang/local_simulator.py:166-215` (докстринг прямо говорит «respecting page-level and question-level show_if/hide_if»). Проверено запуском: блок с заведомо ложным `show_if=age.ge(200)` — все 10 симулированных респондентов получили непустые значения переменной внутри блока. Во фронтенде (React) блочные условия работают (`siamang/frontend/compiler/react.py:191-203`), но в симуляции — нет.
- **Правка:** ограничить утверждение: симуляция учитывает видимость страниц и отдельных вопросов; условия на уровне Block при симуляции в текущей версии игнорируются (учитываются только в рантайме). Это же затрагивает «Try it yourself» в §4.3.1/5.2.1, если читатель будет проверять NaN в симуляции для скрытого блока.

## Глава 4, раздел 4.2
### [НЕТОЧНОСТЬ] «Every public class in siamang.core» — VariableMap не является frozen-датаклассом
- **В учебнике:** «Every public class in siamang.core is declared as a frozen Python dataclass — @dataclass(frozen=True, slots=True)».
- **На самом деле:** `VariableMap` — публичный класс `siamang.core`, но это изменяемый подкласс `dict` (`class VariableMap(dict[str, Variable])`, `siamang/core/variable.py:178`), с мутирующими методами `add()`/`add_many()` — которыми учебник сам пользуется в §4.3.2. Перечисленные в этом же абзаце классы (Variable, 7 подклассов Question, Page, Block, Option, Media, Expression, Quota, Script, Questionnaire) действительно все frozen+slots.
- **Правка:** «Every building-block class of the model…» с оговоркой: реестр VariableMap — исключение, это обычный изменяемый словарь (что и позволяет наполнять его add_many до передачи в Questionnaire).

## Глава 4, раздел 4.3.2 (и Warning + Chapter Summary)
### [НЕТОЧНОСТЬ] Проверка реестра сравнивает переменные по равенству, а не по идентичности («same instance»)
- **В учебнике:** «validate() then enforces that every question variable is the same instance registered there»; в Warning: «a question whose Variable instance is not the registered one fails validation».
- **На самом деле:** проверка — по равенству датаклассов, не по `is`: `siamang/core/questionnaire.py:96-98` (`known = self.variables.require(var.name); if known != var: raise ValueError("Variable '...' differs from registry instance.")`). Проверено запуском: два разных, но равных по значению экземпляра `Variable("age", ...)` проходят валидацию без ошибки. Ошибка возникает только если переменная не зарегистрирована (KeyError) или отличается по значению полей (ValueError).
- **Правка:** заменить «the same instance» на «равную по значению (тому же определению) переменную»; совет «Build each Variable once and reuse that single object» остаётся хорошей практикой, но мотивировать его надо не валидацией.

## Глава 4, раздел 4.1.1 (Layer 5)
### [НЕТОЧНОСТЬ] Для R существует только writer, reader'а нет
- **В учебнике:** «Readers and writers exist for CSV, Excel (.xlsx), SPSS (.sav), Stata (.dta), and R, plus a JSON dictionary format.»
- **На самом деле:** для R есть только `RScriptWriter` (пишет CSV + JSON-словарь + R-скрипт загрузки), reader отсутствует: `siamang/io/r.py:13`, таблица в `docs/concepts.md:140-147` (строка «R | — | RScriptWriter»).
- **Правка:** «…and R (writer only — a loader script plus CSV/JSON dictionary), …» или перечислить R отдельно от парных reader/writer форматов.

## Глава 4, раздел 4.3.2
### [НЕТОЧНОСТЬ] construct и source не попадают в codebook() и не экспортируются в SPSS/Stata
- **В учебнике:** «Fields such as label, description, construct …, and source … surface in SurveyData.codebook() and travel with your data into SPSS and Stata exports.»
- **На самом деле:** `SurveyData.codebook()` возвращает колонки name, label, scale, dtype, role, description, missing_values, missing_kinds, missing, valid_range — без `construct` и `source`: `siamang/data/survey_data.py:68-89` (проверено запуском). В `siamang/io/*` поля `construct`/`source` не упоминаются вовсе — в .sav/.dta они не «путешествуют» (SPSS/Stata переносят variable labels, value labels, missing values).
- **Правка:** оставить construct/source как документационные поля Variable (это верно, `siamang/core/variable.py:72-73`), но убрать утверждение, что они появляются в codebook() и в SPSS/Stata-экспортах; в codebook() попадают label и description.

## Глава 5, раздел 5.1.1
### [НЕТОЧНОСТЬ] next_if и default_next принимают только имена страниц, question id — только для skip_to
- **В учебнике:** «every skip_to, next_if, and default_next target in the questionnaire is a page name (or a question id)».
- **На самом деле:** для `next_if`/`default_next` валидны только имена страниц (`_validate_targets_exist`, `siamang/core/questionnaire.py:809-814` — проверка `target not in known` по множеству имён страниц). Question id допустим только как цель `skip_to` (`siamang/core/questionnaire.py:118-124`: `known_targets = question_ids | page_names`).
- **Правка:** «every next_if and default_next target is a page name; skip_to additionally accepts a question id».

## Глава 5, раздел 5.2.1 / Глава 6 (randomize)
### [НЕ ПОДТВЕРЖДЕНО] Рандомизация (Block.randomize, Page.randomize_blocks, Question.randomize) не реализована в рантайме
- **В учебнике:** «Setting randomize=True shuffles the order of the block's items for each respondent…», «Page(randomize_blocks=True) shuffles the order of the page's immediate Block items, leaving standalone questions in place»; в гл. 6 shared-поле randomize — «Shuffle the answer choices».
- **На самом деле:** поля существуют в модели и описаны так же в wiki (`siamang/core/block.py:15`, `siamang/core/page.py:39`, wiki/Pages-Blocks-and-Structure.md), но: React-компилятор не сериализует ни `Block.randomize`, ни `Page.randomize_blocks`, ни `Question.randomize` (`siamang/frontend/compiler/react.py`, `_compile_block`/`_compile_page` — grep по «randomize» пуст); в React-рантайме (`templates/react/*.jsx`, `dist/bundle.js`) перемешивания нет. Флаг `randomizeBlocks` эмитится только SurveyJS-schema-компилятором (`siamang/frontend/compiler/schema.py:77-78`), и его никто не потребляет. Реальная рандомизация делается через `Script.randomize_options`/`Script.randomize_pages` (docs/concepts.md:211-213).
- **Правка:** учебник соответствует wiki, но не поведению движка; либо добавить оговорку «в текущей версии React-рантайма флаги randomize не применяются — используйте Script.randomize_options», либо согласовать с авторами движка.

## Глава 6, раздел 6.2.1
### [НЕ ПОДТВЕРЖДЕНО] none_of_above и exclusive не реализованы во фронтенде
- **В учебнике:** «none_of_above=True appends a "None of the above" option that deselects the others»; «selecting an exclusive code clears all other selections».
- **На самом деле:** `none_of_above` существует только как поле модели (`siamang/core/question.py:49`) — не упоминается ни в компиляторах, ни в сериализации, ни в React-рантайме. `exclusive` не попадает в скомпилированную схему (нет в `siamang/frontend/compiler/react.py`, `siamang/core/serialization.py`, `templates/react/`); используется он только линтером (правило EXCLUSIVE_CODE_UNKNOWN, `siamang/core/questionnaire.py:602-617`). Формулировки учебника дословно совпадают с wiki/Question-Types.md, но заявленное поведение в рантайме отсутствует.
- **Правка:** сверить с авторами движка; как минимум не обещать читателю наблюдаемое поведение «deselects the others» без оговорки о состоянии реализации.

## Глава 6, раздел 6.2.2
### [НЕ ПОДТВЕРЖДЕНО] Matrix: subquestions и na_option игнорируются React-компилятором
- **В учебнике:** «subquestions … Row labels; default to each variable's label»; «na_option … True adds a "Not applicable" column; a string sets its header».
- **На самом деле:** описания совпадают с wiki/Question-Types.md и docs/reference/core.md, и поля есть в модели (`siamang/core/question.py:194-196`), но при компиляции Matrix строки всегда берутся из `v.label or v.name`, а `subquestions` и `na_option` не используются вовсе: `siamang/frontend/compiler/react.py:290-293`. (Для LikertScale `na_option` реализован: react.py:268-270 + `naOption` в questions.jsx:317.)
- **Правка:** оговорка о реализации либо согласование с движком; утверждение «row labels default to each variable's label» само по себе верно — не работает именно переопределение через subquestions и NA-колонка.

## Проверено и корректно
- Пять слоёв и их модули: siamang.core / siamang.frontend / siamang.deploy / siamang.data / siamang.io — совпадают с docs/concepts.md.
- Все перечисленные классы модели (Variable, MissingValue, ValidationIssue, Question + 7 подклассов, Page, Block, Option, Media, Expression, Quota, Script, FilterRule, Questionnaire, SurveySchema) — `@dataclass(frozen=True, slots=True)`; присваивание полю даёт FrozenInstanceError (проверено запуском).
- Цитата «side-effect free, thread-safe, and deterministic across compilation, simulation, and analysis» дословно есть в wiki/Core-Concepts.md:73 и docs/reference/core.md:5.
- Ровно семь конкретных типов вопросов: SingleChoice, MultiChoice, LikertScale, NumericInput, OpenText, Matrix, Ranking; все импортируются из siamang.core и из siamang.
- «Fourteen shared Question fields» — пересчитано по question.py: text, var, required, hint, show_if, hide_if, skip_to, randomize, other_specify, tag, id, name, media, metadata — действительно 14, типы и значения по умолчанию в таблице гл. 6 совпадают с кодом.
- Правило pages-XOR-blocks: одновременная передача pages и blocks даёт ValueError «Use either 'blocks' or 'pages', not both.» (questionnaire.py:46-47; проверено запуском).
- Questionnaire: поля title/blocks/pages/deadline/variables/scripts; методы validate(), lint(), compile(), simulate(), deploy(), all_questions() — всё есть; CLI по умолчанию ищет module-level атрибут `survey` (cli/loader.py, entry.py).
- validate() проверяет: уникальность question id и имён страниц, существование целей skip_to/next_if/default_next, достижимость всех страниц от первой, отсутствие циклов, ссылки выражений только на известные переменные, дубликаты переменных, согласованность с явным реестром.
- Таблица полей Page (name/title/items/next_if/default_next/randomize_blocks/show_if/hide_if/kind/body/redirect_url/redirect_delay) — полностью совпадает с page.py, включая «runtime default 5» для redirect_delay (app.jsx:399).
- Виды страниц: kind ∈ {content, disqualification, final, redirect}; неизвестный kind → ValueError; is_terminal True ровно для трёх терминальных; content остаётся в Next/Prev-потоке (page.py:26-55).
- Сигнатуры четырёх фабрик ContentPage/DisqualificationPage/FinalPage/RedirectPage — до параметра совпадают с кодом (включая: hide_if есть только у ContentPage и DisqualificationPage; обязательные body у ContentPage и redirect_url у RedirectPage; keyword-only).
- Фабрики не реэкспортируются в top-level siamang (sg.ContentPage отсутствует), импорт из siamang.core работает — как и написано.
- Block: ровно пять полей (title/items/randomize/show_if/hide_if), flatten_questions() рекурсивен; Page.flatten_questions() и Questionnaire.all_questions() дают плоский список в порядке отображения (пример гл. 5 даёт 2, проверено).
- Пустая страница проходит validate(), lint даёт EMPTY_PAGE warning, на strict — error (проверено запуском).
- VariableMap: подкласс dict[str, Variable]; add() при дубликате бросает KeyError; require() бросает KeyError; add_many/by_scale/validate_frame работают как описано; validate_frame репортит MISSING_COLUMN/OUT_OF_RANGE/INVALID_LABEL_VALUE и т.п.; при явном реестре незарегистрированная переменная вопроса валит validate() (KeyError «Variable 'trust' is not registered», проверено).
- Автопостроение VariableMap обходом вопросов при отсутствии явного реестра — есть (simulate, docs/concepts.md).
- Квоты прикрепляются на этапе деплоя через `survey.deploy(..., quota=quotas)`, а не хранятся в Questionnaire (wiki/Quotas.md:54-75; опция quota → compile_quota → schema.quotas).
- Fallback id: имя переменной; для Matrix — `matrix_<first var>`, для wide-MultiChoice — `multi_<first var>` (question_fallback_id; проверено: matrix_trust_govt, multi_src_tv); name по умолчанию равен id (question_output_name).
- MultiChoice: vars= — keyword-only, автоматически включает wide; var+vars одновременно → ValueError; в wide max_answers > числа переменных → ValueError; дефолты min_answers=1, max_answers=None, exclusive=[], mode="array" (всё проверено запуском). min_answers действительно проверяется в рантайме (подсказка «Select at least N more», questions.jsx:284).
- Формы данных при симуляции: array-MultiChoice — один столбец со списком кодов; wide — по бинарному столбцу на переменную; Matrix — столбец на строку; Ranking — один столбец со списком-упорядочением (проверено запуском simulate).
- Option: поля code/label/show_if/hide_if/media; label непустой; media — одиночный Media; дубликаты кодов в choices → ValueError (проверено).
- Media: поля url/kind/alt/caption/autoplay(False)/loop(False)/controls(True); kind выводится из расширения (png→image, mp4→video, mp3→audio, query-string отрезается); URL без распознаваемого расширения без kind → ValueError (проверено).
- Конструкторные ограничения падают сразу: points>=2, step>0, max_chars>0, max_ranked>0, display из допустимого множества (все проверены — ValueError при нарушении).
- LikertScale: points=5 по умолчанию, left_label/right_label, na_option bool|str — реализован в React (naOption); NumericInput: display input/slider, unit, step=1; valid_range переменной действительно пробрасывается в min/max React-схемы (react.py:278-280).
- Strict-линтер: REQUIRED_CONDITIONAL (warning, только strict), INCOMPATIBLE_QUESTION_SCALE (error) для LikertScale≠ordinal и NumericInput∉{interval,ratio}, CATEGORICAL_WITHOUT_LABELS (error) для nominal/ordinal без labels — коды и уровни совпадают с questionnaire.py:411-450.
- Три бэкенда (local, supabase, gsheets), три фронтенда (local, vercel, netlify), расширение через entry points siamang.backends/siamang.frontends (deploy/registry.py).
- SurveyData: аксессоры report, plot, analysis, processing, tables существуют; codebook() есть; DeployResult.collect() есть.
- dataclasses.replace(get_preset("modern"), institution_name=..., primary_color=...) работает (проверено); бандл содержит index.html, style.css, env.js; рантайм — React 18 (18.3.1).
- Примеры кода из §4.2, §4.3.1, §4.3.2, §5.1.2, §5.2.1 (итоговый), §6.1.1 (Option/Media), §6.2.1–6.2.3 — все запускаются без ошибок и дают заявленные результаты.

---

# Ревью глав 7–9 (siamang 0.5.0)

Все примеры кода из глав запускались против установленного пакета (editable, /home/user/siamang). Ошибочные утверждения проверялись и по исходникам, и выполнением кода.

## Глава 7, раздел 7.1.1

### [НЕТОЧНОСТЬ] Обоснование запрета `==` и умолчание про `!=`
- **В учебнике:** «Equality is the exception: Python reserves == on dataclasses for object identity, so you must write gender.eq(1) rather than gender == 1.» и Warning: «gender == 1 silently produces a plain Python bool».
- **На самом деле:** практический вывод верен (проверено: `gender == 1` → `False`, тип `bool`), но объяснение неточно: сгенерированный dataclass-метод `__eq__` сравнивает поля, а не «identity» (siamang/core/variable.py:60 — `@dataclass(frozen=True, slots=True)` без переопределения `__eq__`). Важнее другое: `!=` тоже НЕ перегружен (перегружены только `__gt__/__ge__/__lt__/__le__`, variable.py:165–175), и `gender != 1` молча даёт `True` — всегда истинный bool, что ещё опаснее, чем `==` (элемент будет показан всем). Учебник об этом не предупреждает, хотя `var.ne(v)` есть в таблице хелперов.
- **Правка:** переформулировать: «`==` и `!=` не перегружены (dataclass использует их для пофилдового сравнения объектов), поэтому для равенства/неравенства используйте `.eq()`/`.ne()`»; в Warning добавить, что `gender != 1` так же молча даёт `bool` (`True`).

### [НЕТОЧНОСТЬ] Expression.raw как «escape hatch» для гейтов не проходит validate() и ломает видимость в рантайме
- **В учебнике:** «Construct conditions from variable-name strings with compare, and fall back to verbatim SurveyJS strings or Expression.raw when needed» и в таблице: «Expression.raw(text) … Wrap a verbatim SurveyJS string as an escape hatch; passed through to the frontend but cannot be evaluated or validated in Python.»
- **На самом деле:** сам по себе объект описан верно, но использовать `Expression.raw(...)` как `show_if`/`hide_if` нельзя: `Questionnaire.validate()` прогоняет каждый Expression-гейт через `expr.validate()` (siamang/core/questionnaire.py:246–251), а тот отвергает `raw` — проверено: `validate()` падает с «Page 'p2' has invalid show_if expression: Raw string expressions cannot be validated safely.» Кроме того, в React-рантайме raw-AST вычисляется в `false` (templates/react/app.jsx:36 — `if (op === "raw") return false;`), т.е. элемент с `show_if=Expression.raw(...)` будет скрыт навсегда. Рабочий escape hatch для гейтов — только простая строка.
- **Правка:** уточнить, что `Expression.raw` пригоден там, где выражение сериализуется как есть, но как гейт `show_if`/`hide_if` он не проходит `Questionnaire.validate()` (и в React-рантайме такой гейт всегда скрывает элемент); для «сырых» гейтов оставить только строковую форму.

### [НЕ ПОДТВЕРЖДЕНО] Строковые гейты «отправляются на фронтенд», но React-рантайм их не вычисляет
- **В учебнике:** «Every gate also accepts a plain string in the SurveyJS dialect: sg.Page("adults", items=[...], show_if="age >= 18"). Strings are preserved verbatim and sent to the frontend, but they are not evaluated in Python.»
- **На самом деле:** строка действительно передаётся на фронтенд как есть (frontend/compiler/react.py:365–367), но штатный React-рантайм строковые условия НЕ вычисляет — они считаются всегда истинными: templates/react/visibility.jsx:38 (`if (typeof condition === "string") return true; // raw string — can't evaluate`) и app.jsx:71. То есть `show_if="age >= 18"` не гейтит страницу ни в Python, ни в браузере (в React-рантайме, который используется deploy() по умолчанию — questionnaire.py:161 `ReactRuntime()`). Строки реально работают только в альтернативном SurveyJS-рантайме (CDN-движок сам парсит visibleIf).
- **Правка:** добавить предупреждение: в дефолтном React-рантайме строковый гейт игнорируется (элемент всегда виден); строковая форма даёт рабочую видимость только с SurveyJS-рантаймом. Рекомендацию «типизированные выражения — default» усилить именно этим аргументом.

## Глава 7, раздел 7.2.2

### [ОШИБКА] validate() не защищает от петель через skip_to
- **В учебнике:** «Questionnaire.validate() raises a ValueError if skip_to references an unknown id, and it also checks reachability and detects cycles across the page graph — so you cannot accidentally strand respondents in a routing loop.»
- **На самом деле:** для `skip_to` проверяется только существование цели (siamang/core/questionnaire.py:120–124). Навигационный граф для reachability/циклов строится ТОЛЬКО из `next_if`/`default_next` и неявного порядка страниц (questionnaire.py:768–779, `_build_navigation_graph` не учитывает `skip_to`). Проверено выполнением: анкета из двух страниц с взаимными `skip_to` («p1 → p2 → p1») проходит `validate()` без ошибок.
- **Правка:** оставить «target must exist», а фразу про reachability/циклы либо убрать, либо явно оговорить, что эти проверки покрывают только `next_if`/`default_next`, и петля из `skip_to` валидатором не ловится.

### [ОШИБКА] simulate() не «проходит маршруты»
- **В учебнике:** «Run survey.simulate() to generate synthetic, logically valid responses and confirm that every route is exercised.» и в листинге: «survey.simulate(n=200)     # synthetic responses traverse both routes».
- **На самом деле:** симулятор учитывает только `show_if`/`hide_if` на уровне страниц и вопросов; `next_if`, `default_next`, `skip_to` и терминальность страниц полностью игнорируются — все страницы обрабатываются последовательно (siamang/local_simulator.py:166–216). Проверено: в примере «Screening Flow» симуляция не отражает маршрутизацию «до 18 → dq» (все respondents проходят обе страницы по правилам видимости, роутинг не моделируется).
- **Правка:** убрать утверждение, что simulate() «exercises routes» / «traverse both routes»; написать, что симуляция проверяет логику видимости (show_if/hide_if), а маршрутизация next_if/skip_to симулятором не воспроизводится.

### [ОШИБКА] preview() не рендерит структуру и роутинг
- **В учебнике:** «…inspect the routing with survey.preview(), which renders a static text view of the survey structure including routing logic.»
- **На самом деле:** `preview()` возвращает одну строку: `f"Questionnaire<{self.title}> with {len(self.all_questions())} questions"` (siamang/core/questionnaire.py:126–127). Проверено: `Questionnaire<Eligibility Example> with 1 questions` — ни структуры, ни роутинга.
- **Правка:** убрать это задание либо заменить на честное описание («preview() выводит однострочную сводку — название и число вопросов»); роутинг можно инспектировать только по самим объектам Page (`page.next_if`, `page.default_next`).

### [НЕ ПОДТВЕРЖДЕНО] skip_to и next_if не реализованы в рантайме респондента
- **В учебнике:** «The skip_to field on a Question jumps to a target page name or question id immediately after the question is answered» и «next_if is a list of (condition, target_page_name) pairs, evaluated in order; the first matching rule wins. If no rule matches, default_next is used…»
- **На самом деле:** `skip_to`, `next_if` и `default_next` существуют только в core-модели и используются исключительно валидатором: grep по всему пакету показывает эти поля только в siamang/core/{page,question,questionnaire}.py — ни один из компиляторов фронтенда (frontend/compiler/react.py, frontend/compiler/schema.py) их не сериализует, и в React-рантайме навигация строго последовательна по видимым страницам (templates/react/hooks.jsx:111–116, `goNext` = index+1; то же в собранном dist/bundle.js). Скрин-аут в реальности реализуется терминальной страницей с `show_if` (см. пример DisqualificationPage — он работает), а не переходами.
- **Правка:** это ключевая проблема раздела. Либо честно оговорить, что в версии 0.5.0 skip_to/next_if — design-time-метаданные (валидируются, документируют замысел, но фронтенд-рантайм их не исполняет; рабочий механизм ветвления для респондента — гейты видимости и терминальные страницы), либо перестроить раздел вокруг гейтов. Как минимум убрать формулировки, описывающие фактическое поведение респондента.

## Глава 8, раздел 8.2.1

### [НЕ ПОДТВЕРЖДЕНО] Из семи триггеров рантайм реально запускает только три
- **В учебнике:** «The seven lifecycle triggers…» (таблица onInit/onPageEnter/onPageExit/onQuestionShow/onAnswer/onSubmit/onRandomize) и полный пример `custom = sg.Script(name="log_exit", trigger="onPageExit", …)` — «posting a diagnostic timestamp whenever a page is left».
- **На самом деле:** все 7 триггеров валидируются при конструировании (siamang/core/script.py:26–34) — это верно. Но в штатном React-рантайме диспетчеризуются только три: `onInit` (templates/react/app.jsx:494), `onAnswer` (app.jsx:522), `onSubmit` (hooks.jsx:152). Методы `runForPage` (onPageEnter) и `runForQuestion` (onQuestionShow) определены (app.jsx:162–163), но нигде не вызываются; для `onPageExit` и `onRandomize` вызовов нет вовсе (подтверждено и по собранному dist/bundle.js). Следствия: пример `log_exit` (onPageExit) никогда не выполнится; фабрики `Script.randomize_options` и `Script.timed_question` (обе onQuestionShow) в текущем рантайме не срабатывают; дефолтный триггер `"onPageEnter"` — тоже мёртвый.
- **Правка:** оговорить, какие триггеры реально диспетчеризуются рантаймом 0.5.0 (onInit, onAnswer, onSubmit), пометить остальные как зарезервированные/пока не исполняемые; пример log_exit перевести на onSubmit или onAnswer, а фабрики randomize_options/timed_question сопроводить оговоркой.

### [НЕ ПОДТВЕРЖДЕНО] Специальные ключи answers.__errors__/__pages__ не потребляются рантаймом
- **В учебнике:** «Special keys: answers.__options__[qid] (per-question option order), answers.__pages__ (page order), answers.__errors__[field] (validation messages), answers.__timers__ (timer handles)» и Tip: «write messages into answers.__errors__[field] … rather than trying to block navigation directly».
- **На самом деле:** рантайм инициализирует только `__options__` и `__pages__` (templates/react/app.jsx:454); ни `__errors__`, ни `__timers__` он нигде не читает (grep по templates/react: `__errors__` встречается только в генерируемом коде фабрики validate_fields_match, script.py:144) — сообщение, записанное скриптом в `__errors__`, респонденту не показывается. `__pages__` навигация тоже не использует: `useSurveyNav` работает с исходным `allPages` (hooks.jsx:87–94), так что перетасовка `answers.__pages__` скриптом randomize_pages на порядок страниц не влияет.
- **Правка:** описать `__errors__`/`__timers__`/`__pages__` как соглашение уровня скриптов (script-to-script), а не как ключи, «понимаемые рантаймом»; совет про cross-field validation через `__errors__` снабдить оговоркой, что отображение таких сообщений в текущем рантайме не реализовано.

## Глава 9, раздел 9.1.1 (и Chapter Summary / Tip)

### [НЕТОЧНОСТЬ] Проверка реестра — по равенству, а не «тот же экземпляр»
- **В учебнике:** «…validate() checks registry consistency — every question variable must be the same instance registered in the map. Define each variable once and reuse the object everywhere.»
- **На самом деле:** проверка — `if known != var: raise ...` (siamang/core/questionnaire.py:96–98), т.е. сравнение по равенству полей frozen-датакласса. Проверено выполнением: равная по полям копия переменной (другой объект) проходит `validate()` без ошибок. (Та же неточность есть в wiki/Validation-and-Linting.md:35 — учебник её унаследовал.)
- **Правка:** «must be equal to the registered definition» вместо «the same instance»; совет «определяйте один раз и переиспользуйте» оставить как best practice, но не как техническое требование.

## Глава 9, раздел 9.3.1

### [НЕТОЧНОСТЬ] raise_on_error срабатывает после полного прохода, а не «как только»
- **В учебнике:** «with raise_on_error=True it raises ValueError as soon as any issue has severity == "error"».
- **На самом деле:** `validate_frame` сначала собирает все issues по всем переменным и только в конце, если среди них есть error, бросает `ValueError` с перечислением всех кодов ошибок (siamang/core/variable.py:263–265). Проверено: сообщение — «DataFrame validation failed: MISSING_COLUMN, OUT_OF_RANGE, INVALID_LABEL_VALUE» (агрегат, не первая ошибка).
- **Правка:** «raises ValueError after the check completes if any issue has severity "error" (the message lists all error codes)».

## Проверено и корректно

- Гл. 7: импорт-поверхность `from siamang.core import Expression, VarRef, compare, AND, OR, NOT, FilterRule` работает (core/__init__.py:4–12); Expression — frozen dataclass с полями op/left/right (expression.py:37–41).
- Гл. 7: ровно восемь хелперов сравнения (eq, ne, gt, ge, lt, le, isin, notin) с указанными операторами и SurveyJS-формами (variable.py:141–163); `>,>=,<,<=` перегружены на Variable (variable.py:165–175); `age >= 18` даёт `Expression(">=", VarRef("age"), 18)` — проверено.
- Гл. 7: AND/OR требуют ≥2 аргументов (ValueError — проверено), складываются слева направо; NOT/`&`/`|`/`~` эквивалентны функциональной форме (проверено: деревья идентичны); `str(VarRef)` = `{name}` (expression.py:33–34).
- Гл. 7: методы Expression — evaluate (ValueError на raw — expression.py:115–118), variables(), validate(set|Mapping, отвергает raw), to_surveyjs() (вывод `"({age} >= 18) and ({gender} = 2)"` — проверено), to_dict()/from_dict() round-trip без потерь (проверено), classmethod Expression.raw (expression.py:94–96).
- Гл. 7: `compare(var_name, op, value)` — точная сигнатура (expression.py:206–207); допустимые op: =, !=, >, >=, <, <=, in, not in (expression.py:9).
- Гл. 7: FilterRule(predicate, description=None) с единственным методом evaluate → bool (filter_rule.py:10–18); в SurveyJS не компилируется — проверено, пример из учебника работает.
- Гл. 7: show_if/hide_if есть на всех четырёх уровнях — Page (page.py:40–41), Block (block.py:15–16), Question (question.py:21–22), Option (option.py:27–28); правило «rendered iff show_if истинно и hide_if не истинно» соответствует visibility.jsx:54–57.
- Гл. 7: пример «Eligibility Example» (ContentPage/DisqualificationPage/FinalPage, body — keyword-only) собирается и проходит validate() — запускалось; сигнатуры фабрик страниц соответствуют page.py:67–141.
- Гл. 7: типизированные выражения действительно вычисляются и в Python (validate/simulate — questionnaire.py:246–251, local_simulator.py:101–104), и в браузере из сериализованного дерева/скомпилированного JS (app.jsx:12–44, compiler/react.py:346–368).
- Гл. 7: `Questionnaire.validate()` проверяет `{name}`-токены в строковых гейтах (проверено: неизвестный `{agee}` → ValueError), а голые имена (как в `"age >= 18"`) не извлекает — проверено (questionnaire.py:227, 238).
- Гл. 7: `next_if: list[tuple[str, str]]`, `default_next: str | None` (page.py:37–38); первое совпадение побеждает, потом default_next, потом следующая страница — так строится граф валидации (questionnaire.py:768–779); неизвестные цели next_if/skip_to → ValueError (проверено); недостижимые страницы и циклы next_if ловятся (questionnaire.py:213–219).
- Гл. 7: `age.lt(18).to_surveyjs()` даёт `"{age} < 18"`, пример «Screening Flow» проходит validate() и simulate(n=200) — запускалось.
- Гл. 8: Quota — frozen dataclass с полями variable/target_value/limit (quota.py:13–17); `reached(answers: list[dict]) -> bool` считает совпадения и сравнивает с limit (quota.py:19–21); примеры False/True из учебника воспроизведены, включая «Try it yourself» (99 → False, 100 → True).
- Гл. 8: квоты не хранятся на Questionnaire, передаются в deploy через `quota=` (questionnaire.py:136–164 → options → compile_questionnaire → SurveySchema.quotas, compiler/schema.py:51); реальный `survey.deploy(backend="local", frontend="local", quota=[...])` выполнен успешно.
- Гл. 8: enforcement — сервер проверяет каждую ячейку при сабмите: local SQLite держит атомарные счётчики (deploy/backends/local.py:128–146, «Atomically check + increment»), Supabase создаёт quota_counters (deploy/backends/supabase.py:400–408), gsheets — лист _quotas (gsheets.py:210–225, 366+); при заполненной ячейке фронтенд показывает «quota full»-экран (hooks.jsx:155–158, app.jsx:373).
- Гл. 8: каждый деплой создаёт новый survey_id (uuid4 — local.py:77) со свежими счётчиками, т.е. «Redeploying resets all quota counters» — верно.
- Гл. 8: Script — frozen dataclass с полями code/trigger="onPageEnter"/name/target/context/sandbox=True (script.py:37–70); конструктор валидирует триггер (ValueError — проверено), непустой code (проверено) и непустой name при передаче (проверено).
- Гл. 8: триггеров ровно семь и имена совпадают: onInit, onPageEnter, onPageExit, onQuestionShow, onAnswer, onSubmit, onRandomize (script.py:26–34).
- Гл. 8: ровно четыре фабрики с заявленными пресетами (проверено выполнением): randomize_options → onQuestionShow/target=qid/seed в context (script.py:91–108), randomize_pages → onInit/глобально/фиксирует первую и последнюю страницы (110–128), validate_fields_match → onAnswer/target=field_b/пишет в __errors__[field_b] (130–152), timed_question → onQuestionShow/target=qid/автопереход через window.siamangNext (154–174).
- Гл. 8: `Questionnaire(scripts=[...])`; validate() проверяет триггер и то, что target — реальный question id или имя страницы (questionnaire.py:76–87; висячий target → ValueError, проверено).
- Гл. 8: utils = shuffle, sample, clamp, debounce, now, formatDate (app.jsx:112–129); api = {get, post} (app.jsx:131–141); context передаётся в снippet как есть, рантайм ничего не подмешивает (app.jsx:143–163: во всех вызовах runtime-context = {}).
- Гл. 9: полный список полей Variable и их порядок соответствуют variable.py:60–76; name непустой, scale/dtype/role нормализуются lower/strip и проверяются по множествам (проверено: "Ordinal" → "ordinal", неверные значения → ValueError), valid_range — упорядоченная пара (ValueError — проверено), malformed missing → TypeError (проверено).
- Гл. 9: scale ∈ {nominal, ordinal, interval, ratio}; dtype ∈ {int, float, str, bool, category, datetime}; role ∈ {input, target, weight, id, grouping, derived} (variable.py:12–14) — все три перечня в учебнике точны.
- Гл. 9: strict-линт действительно даёт INCOMPATIBLE_QUESTION_SCALE для NumericInput вне interval/ratio и LikertScale вне ordinal (оба severity=error, questionnaire.py:424–445) и CATEGORICAL_WITHOUT_LABELS для категориальных без labels (questionnaire.py:717–729).
- Гл. 9: замечание о расхождении документации по dtype подтверждено дословно: docs/reference/core.md:38 «inferred during validation» vs wiki/Variables-and-Measurement.md:50 «simply skipped during validation»; код пропускает проверку при dtype=None (variable.py:379–380) — практический вывод учебника верен.
- Гл. 9: labels подставляются как варианты ответа SingleChoice/MultiChoice/Ranking при отсутствии choices (compiler/react.py:307–313); valid_range у NumericInput уходит в браузер как min/max (compiler/react.py:278–280).
- Гл. 9: MissingValue(code, label, kind="system_missing") — ровно пять kinds: refusal, dont_know, not_applicable, not_asked, system_missing (variable.py:15–21); пустой label и неизвестный kind → ValueError (проверено); to_dict/from_dict работают (проверено).
- Гл. 9: is_missing / structured_missing_values / missing_kinds_dict работают как описано (проверено, включая «Try it yourself» с 97/99); legacy missing_values+missing_labels и structured missing= сливаются в канонический вид (missing — кортеж MissingValue, missing_values — коды, missing_labels — обратная засыпка; legacy-коды получают kind="system_missing" — проверено); ключ missing_labels без объявленного кода → ValueError (проверено).
- Гл. 9: VariableMap — dict-подкласс; add (KeyError на дубликат — проверено), add_many, require (KeyError — проверено), by_scale/by_role case-insensitive (variable.py:196–206), from_dict восстанавливает реестр (round-trip проверен); все шесть кодбук-аксессоров существуют и возвращают заявленные формы (labels_dict с фолбэком на имя — проверено).
- Гл. 9: validate_frame(frame, raise_on_error=False) -> list[ValidationIssue] (variable.py:223–266); коды и severity таблицы совпадают: MISSING_COLUMN/INVALID_DTYPE/OUT_OF_RANGE/INVALID_LABEL_VALUE/INVALID_WEIGHT/DUPLICATE_ID — error, EXTRA_COLUMN/MISSING_VALUE_WITHOUT_LABEL — warning; «Try it yourself» (age=12, gender=7, нет employment) даёт ровно OUT_OF_RANGE, INVALID_LABEL_VALUE, MISSING_COLUMN — проверено; ролевые ограничения weight/id срабатывают (проверено: INVALID_WEIGHT, DUPLICATE_ID).
- Гл. 9: ValidationIssue — frozen dataclass code/severity/message/variable/column (variable.py:24–30).
- Гл. 9: без variables= карта переменных строится из вопросов автоматически (compiler/schema.py:35, questionnaire.py:174–184); объявления missing попадают в схему датасета (SurveySchema.variables) и в SPSS-экспорт как user-missing (io/spss.py:22, 61–76).

---

# Ревью глав 10–11 (theming/UIConfig/фронтенды; валидация и линтинг)

Проверено против движка siamang 0.5.0 (editable install); все ключевые примеры кода реально запущены.

## Глава 10, раздел 10.1.1

### [НЕТОЧНОСТЬ] «Nine colour fields» — цветовых полей десять
- **В учебнике:** «Palette. Nine colour fields define the visual identity.»
- **На самом деле:** в самой же таблице учебника перечислено 10 полей (строка `error_color / error_soft_color` — это два поля, плюс `warn_color`). В коде палитра — 9 полей в секции palette (siamang/frontend/theme/ui_config.py:55-63) плюс `warn_color` (ui_config.py:132), итого 10 цветовых полей.
- **Правка:** заменить «Nine colour fields» на «Ten colour fields» (либо явно исключить `warn_color` из подсчёта, но тогда убрать его из таблицы палитры).

### [ОШИБКА] Автологотип показывает «RH», а не «RHC»
- **В учебнике:** «Because logo_text was left unset, the header automatically shows "RHC", derived from the institution's initials.»
- **На самом деле:** `effective_logo_text` берёт инициалы только первых **двух** слов: `initials = "".join(w[0].upper() for w in words[:2])` (siamang/frontend/theme/ui_config.py:202-203). Проверено запуском: для `institution_name="Riverside Health Collective"` свойство возвращает `'RH'`, не `'RHC'`.
- **Правка:** заменить «RHC» на «RH» и уточнить формулировку: «derived from the initials of the first two words of the institution's name».

## Глава 10, раздел 10.2.1

### [ОШИБКА] survey.deploy() по умолчанию использует ReactRuntime, а не SurveyJS
- **В учебнике:** «Note that siamang preview uses the React runtime locally, so the preview you see while developing reflects the React design system even if you deploy with the default SurveyJS runtime.»
- **На самом деле:** `SurveyJSRuntime()` — дефолт только у `FrontendBuilder` (siamang/frontend/builder.py:36). Но повседневный путь `survey.deploy(...)` явно подставляет React: `runtime = options.pop("runtime", None) or ReactRuntime()` (siamang/core/questionnaire.py:161). То есть деплой по умолчанию идёт именно через ReactRuntime, и посылка «даже если вы деплоите с дефолтным SurveyJS-рантаймом» ложна. Wiki (wiki/Frontend-and-Theming.md:134) называет SurveyJSRuntime «default» только в контексте FrontendBuilder.
- **Правка:** переписать примечание: preview и `survey.deploy(...)` оба используют ReactRuntime по умолчанию; SurveyJSRuntime является дефолтом лишь при ручной работе через `FrontendBuilder`. Это же уточнение стоит внести в Learning Objectives («Choose between the SurveyJSRuntime (default)…»), в шапку таблицы рантаймов «SurveyJSRuntime (default)» и в пункт Chapter Summary «SurveyJSRuntime is the default renderer» — везде оговорить «default for FrontendBuilder; survey.deploy() defaults to ReactRuntime».

### [НЕТОЧНОСТЬ] «SurveyBundle содержит пять файлов» — верно только для SurveyJS-рантайма
- **В учебнике:** «The builder returns a SurveyBundle whose filenames are already content-hashed. It contains five files: index.html, closed.html, style.css, env.js, manifest.json.»
- **На самом деле:** пять файлов — это бандл SurveyJSRuntime (у него `static_assets()` пуст — siamang/frontend/runtime/base.py:47-50). ReactRuntime добавляет `bundle.js` и два vendor-файла React (siamang/frontend/runtime/react.py:197-203); проверено запуском — react-бандл содержит 8 файлов (`bundle.*.js`, `vendor/react.production.min.*.js`, `vendor/react-dom.production.min.*.js` плюс пять базовых).
- **Правка:** уточнить: «содержит пять базовых файлов … рантайм может добавлять собственные статические ассеты (ReactRuntime добавляет bundle.js и vendored React)».

## Глава 11, раздел 11.1.1

### [НЕТОЧНОСТЬ] CLI также валидирует module-level `options` (квоты)
- **В учебнике:** «siamang validate my_survey.py is a thin wrapper around these methods: it loads the survey object, calls validate(strict=...), then prints all lint() warnings.»
- **На самом деле:** между validate и lint CLI дополнительно вызывает `validate_options(survey, options)` — проверку module-level словаря `options` (в т.ч. квот); её ValueError тоже даёт exit-код 2 (siamang/cli/validate.py:20-26).
- **Правка:** добавить полфразы: «…calls validate(strict=...) and additionally validates the module-level options dict (quotas etc.), then prints all lint() warnings».

### [ОШИБКА] Интерпретация exit-кода 1: описанный сценарий даёт код 2 или 0, но не 1
- **В учебнике:** «1 means it can deploy but trips a rule Siamang considers an error (such as an incompatible question scale)»; и в 11.2.1: «This is also why validate(strict=True) promotes them to hard failures, and why the CLI exits with code 1 when they appear.»
- **На самом деле:** ветка exit-кода 1 в CLI существует (siamang/cli/validate.py:42-44), но error-severity правила (INCOMPATIBLE_QUESTION_SCALE, CATEGORICAL_WITHOUT_LABELS, EMPTY_PAGE в strict) запускаются только на strict-уровне, а CLI с `--strict` сначала вызывает `validate(strict=True)`, которая сама поднимает ValueError по этим же находкам (siamang/core/questionnaire.py:99-103) → exit 2. Без `--strict` эти правила вообще не выполняются → exit 0. Проверено запуском: survey с LikertScale на nominal-переменной даёт `siamang validate` → exit 0, `siamang validate --strict` → «validation error: Strict questionnaire validation failed: INCOMPATIBLE_QUESTION_SCALE» → exit 2. На basic-уровне ни одно правило не имеет severity=error, так что код 1 при текущем наборе правил практически недостижим.
- **Правка:** убрать пример с «incompatible question scale» из объяснения кода 1 и фразу «why the CLI exits with code 1 when they appear» в 11.2.1; честно сказать: таблица exit-кодов — контракт CLI, но при текущем наборе правил error-находки на strict-уровне перехватываются validate(strict=True) и дают код 2; код 1 зарезервирован на случай error-severity находок, не промотированных валидацией.

## Глава 11, раздел 11.2.1

### [ОШИБКА] «4 basic-правила» — на basic-уровне реально срабатывает 11 кодов
- **В учебнике:** «With the default level="basic", four rules are checked» (и в Learning Objectives: «the four basic-level and four strict-level lint rules»; в Chapter Summary: «lint(level="basic") checks four rules»).
- **На самом деле:** помимо четырёх структурных кодов (EMPTY_QUESTIONNAIRE, EMPTY_PAGE, REDUNDANT_NAVIGATION, MISSING_NAVIGATION) `lint()` на **любом** уровне, включая basic, всегда прогоняет ещё три группы проверок (siamang/core/questionnaire.py:325-330) с семью кодами: UNKNOWN_CONDITION_VALUE (questionnaire.py:544), CONTRADICTORY_VISIBILITY (:576), EXCLUSIVE_CODE_UNKNOWN (:608), OPTION_CODE_WITHOUT_LABEL (:628), LIKERT_POINTS_LABEL_MISMATCH (:645), MISSING_CODE_NOT_IN_LABELS (:668), RANGE_LABEL_MISMATCH (:690). Все они severity="warning". Продемонстрировано запуском: `siamang validate` (basic) на survey с LikertScale(points=5) и переменной с 2 label'ами печатает `[warning] [LIKERT_POINTS_LABEL_MISMATCH] …`. Strict-уровень действительно добавляет ровно 4 заявленных правила (REQUIRED_CONDITIONAL, INCOMPATIBLE_QUESTION_SCALE, CATEGORICAL_WITHOUT_LABELS, UNUSED_VARIABLE). Итого движок знает 15 кодов, а не 8. Примечание: wiki/Validation-and-Linting.md:90-107 документирует только 4+4 — wiki отстала от кода; учебник воспроизвёл её, но источник истины — движок.
- **Правка:** переписать раздел: «basic» = 4 структурных правила + 7 codebook/logic-правил (перечислить коды, все warning), «strict» добавляет 4. Соответственно исправить заголовок 11.2.1, Learning Objectives и Chapter Summary («…adds four more, two of which carry error severity» — это про strict остаётся верным).

## Проверено и корректно

- UIConfig — ровно 66 полей (`len(dataclasses.fields(UIConfig)) == 66`), «roughly 66» корректно; frozen dataclass (ui_config.py:39).
- Семь функциональных групп и все имена/дефолты полей в таблицах гл. 10 совпадают с ui_config.py: палитра (все hex-дефолты), типографика (font_size "15.5px", line_height "1.6", font_pair), layout (width "700px", radius "4px", density, question_style), брендинг (9 полей), футер (3 поля), ровно 20 i18n-строк, advanced (progress_style/default_theme/redirect_url/allow_back/enable_analytics/access-гейт из 6 полей/custom_css).
- `__post_init__` валидирует ровно перечисленные 5 полей; `question_style="card"` → ValueError (проверено запуском, ui_config.py:148-158).
- FONT_PRESETS: academic (Source Serif 4 + Inter, дефолт), modern (Inter), humanist (Nunito), каждый со своим Google Fonts URL (ui_config.py:17-36).
- THEME_PRESETS — ровно 6 пресетов с именами default, academic, dark, modern, humanist, high_contrast (presets.py:17-91); характеристики из таблицы (academic 680px; dark #10131a; modern 16px/spacious/белый; humanist зелёный/скруглённый; high_contrast 18px/modern) совпадают.
- `get_preset()` на неизвестное имя поднимает KeyError со списком доступных (presets.py:94-98, проверено запуском).
- Пример с `dataclasses.replace(get_preset("modern"), ...)` работает (запущен).
- `compile_css(ui)` возвращает CSS-строку на custom properties; это fallback style.css, когда рантайм не даёт свой (builder.py:65-67).
- Импорт-блок 10.2 — все 12 имён реально экспортируются из siamang.frontend (frontend/__init__.py:47-66); проверено запуском.
- SurveySchema: все перечисленные поля точны (schema.py:16-29); to_surveyjs даёт showProgressBar:"top", questionsOnPageMode:"questionPerPage", срезает _quota_variable/_meta (schema.py:31-46,70); to_dict — полная сериализация.
- FrontendBuilder: оба аргумента конструктора опциональны, дефолты SurveyJSRuntime()/UIConfig() (builder.py:32-37); сигнатура build() воспроизведена дословно (builder.py:39-46); build() сам вызывает with_hashed_filenames() (builder.py:86).
- ClientEnv несёт только frontend-safe значения, секреты не попадают в бандл (client/base.py:11-20).
- ReactRuntime без survey= поднимает ValueError «Pass \`survey=\` to FrontendBuilder.build()» (runtime/react.py:111-114, проверено); SurveyJSRuntime работает от схемы (survey игнорируется).
- SurveyJSRuntime — не-React, на SurveyJS core (survey-core + survey-js-ui с CDN, constants.py:8-12); ReactRuntime — standalone React 18 со своим design-system стилем (react.py docstring).
- SurveyBundle: write_to, to_zip (ZIP_DEFLATED), manifest_json, compute_digest (16-символьный префикс SHA-256), with_hashed_filenames для .js/.css (bundle.py:24-97); манифест содержит runtime/client/backend/survey_id/schema_hash/built_at (builder.py:99-110).
- Сквозной пример 10.2.1 (compile_questionnaire → FrontendBuilder → LocalClientTemplate → write_to("./dist")) запущен успешно; «Try it yourself» (два рантайма, разные digest/manifest) — подтверждено.
- `siamang preview` действительно поднимает React-preview (cli/preview.py:1).
- FinalPage/RedirectPage с redirect_url/redirect_delay и «quota full»-экран (closed.html, reason quota_full) существуют (core/page.py:102-123,45-46; runtime/surveyjs.py:13-23).
- validate(): все заявленные проверки соответствуют коду — дубликаты ID вопросов и переменных (questionnaire.py:105-116, 88-94), skip_to (:118-124), пустые/дублирующиеся имена страниц (:66-72), evaluability show_if/hide_if/next_if и известность переменных (:221-251), export-safety page show_if для surveyjs (:253-268), навигация: существование целей, достижимость, ацикличность (:213-219), скрипты (:76-87), консистентность реестра VariableMap (:95-98). Возвращает None при успехе.
- validate(strict=True) прогоняет lint(level="strict") и промотирует error-находки в ValueError (:99-103); пример 11.1.1 запущен — оба вызова проходят молча.
- Сигнатуры `validate(self, strict: bool = False) -> None` и `lint(self, level: str = "basic") -> list[LintWarning]` точны (:63, :275).
- LintWarning — ровно 4 поля code/severity/message/location, импортируется из siamang.core.questionnaire (:26-31).
- Отмеченное учебником расхождение доков реально: docs/reference/core.md:477-480 говорит "info"/"warning"/"error", "unreachable_page", "page:welcome"; в коде только "warning"/"error" — выбор учебника в пользу wiki-энумерации верен.
- lint() поднимает исключение только на неверный level (:276-277, проверено); находки возвращаются все сразу.
- Строгие правила: REQUIRED_CONDITIONAL (warning), INCOMPATIBLE_QUESTION_SCALE (error; NumericInput не interval/ratio, LikertScale не ordinal), CATEGORICAL_WITHOUT_LABELS (error), UNUSED_VARIABLE (warning) — коды, severity и условия совпадают (:411-450, :717-729, :331-347).
- EMPTY_PAGE: warning на basic, error на strict (:298, проверено запуском); пример 11.2.1 с «flawed survey» воспроизводит вывод `[warning] EMPTY_PAGE: Page 'p2' has no items. (p2)` дословно.
- Таблица exit-кодов 0/1/2 как контракт соответствует коду CLI (cli/validate.py:26, 31, 42-44); реальные прогоны: валидный survey → 0, структурная ошибка → 2 (см. однако замечание об интерпретации кода 1 выше).
- SurveyData.validate() → list[ValidationIssue] (data/survey_data.py:113); VariableMap.validate_frame с кодами MISSING_COLUMN/OUT_OF_RANGE/INVALID_LABEL_VALUE (core/variable.py:233, 424, 442).

---

# Ревью глав 12–14 (deploy, симуляция, импорт/экспорт)

Проверка против движка siamang 0.5.0 (editable-установка, /home/user/siamang). Ключевые примеры запущены: `survey.deploy()` (local/local, end-to-end с POST /responses и `collect()`), `survey.simulate(...)` (пример с consent-гейтом из 13.2.2), round-trip CSV/Excel/SPSS/Stata, R-бандл, JSON-словарь, `validate()`, `recode_values()`, `create_index()`.

---

## Глава 12, раздел 12.1.1

### [НЕТОЧНОСТЬ] Опция `ui=` не уходит в компиляцию — её потребляет сам `deploy()`

- **В учебнике:** «Remaining **options go to compilation. These are the same options survey.compile(...) accepts: ui=UIConfig(...) for theming (Chapter 10), quota=[...] …» и в листинге: «**options, # ui=..., quota=..., language=... → compile_questionnaire».
- **На самом деле:** `Questionnaire.deploy()` сам извлекает `ui` (и `runtime`) из `options` — `options.pop("ui", None)` — и передаёт их в `FrontendBuilder`, а не в `compile_questionnaire` (siamang/core/questionnaire.py:160–163). До компиляции доходят только остальные опции; `compile_questionnaire` понимает `language`, `description`, `completion_text`, `show_progress`, `allow_back`, `one_question_per_page`, `max_responses`, `quota`, `metadata` (siamang/frontend/compiler/schema.py:43–52). `survey.compile(ui=...)` молча проигнорирует `ui`. Формулировка унаследована из wiki/Deployment.md:29, но коду не соответствует.
- **Правка:** разделить: «`quota`, `language`, `one_question_per_page`, `show_progress`, `allow_back` уходят в компиляцию (те же, что у `survey.compile(...)`); `ui=UIConfig(...)` и `runtime=` `deploy()` извлекает сам и передаёт в `FrontendBuilder`». Комментарий в листинге поправить соответственно. То же в Chapter Summary («Compile-time options — ui, quota, …»).

## Глава 12, раздел 12.2.2

### [НЕТОЧНОСТЬ] LocalFrontend по умолчанию слушает 0.0.0.0, а не 127.0.0.1

- **В учебнике:** «local. Serves the bundle on 127.0.0.1 and forwards POST /responses and POST /quota-check to the backend.»
- **На самом деле:** дефолт `host: str = "0.0.0.0"` (siamang/deploy/frontends/local.py:218; также LocalServer:165). Проверено запуском: `survey.deploy()` вернул `url == "http://0.0.0.0:42873"`. Значение `127.0.0.1` фигурирует только в docs/reference/deploy.md:302 — документация здесь расходится с кодом.
- **Правка:** «Serves the bundle on all interfaces (host="0.0.0.0" by default; pass host="127.0.0.1" to bind loopback only)» — либо просто «on localhost», не называя конкретный адрес.

### [НЕТОЧНОСТЬ] У Vercel CLI-фолбэк тоже требует токен; без токена — сразу локальная папка

- **В учебнике:** «Publishing follows a three-step fallback strategy: (1) the Vercel REST API when a token is set; (2) otherwise the npx vercel CLI; (3) otherwise the bundle is written to .vercel_deploy_<survey_id>/…»
- **На самом деле:** в `VercelFrontend.publish()` REST используется при `token and session`; CLI (`npx vercel --prod --token <token>`) — только когда токен есть, но недоступна библиотека `requests`; без токена бандл сразу пишется в `.vercel_deploy_<survey_id>/` (siamang/deploy/frontends/vercel.py:116–127, 174). Цепочка «otherwise CLI» без токена не срабатывает — `--token` обязателен в команде. Та же неточность в docs/reference/deploy.md:314–317.
- **Правка:** «(1) REST API, когда задан token и доступен requests; (2) npx vercel CLI, когда token задан, но REST-путь недоступен; (3) без token бандл пишется в .vercel_deploy_<survey_id>/ для ручного деплоя».

### [НЕТОЧНОСТЬ] «Analytics route» в vercel.json не существует — аналитика подключается скриптом в бандле

- **В учебнике:** «Every publish injects a strict vercel.json with a Content-Security-Policy, X-Frame-Options: DENY, cache-control for the content-hashed assets, and an analytics route when your UIConfig sets enable_analytics=True.»
- **На самом деле:** `_VERCEL_CONFIG` статичен и содержит только headers/rewrites — никакого analytics-route в него не добавляется (siamang/deploy/frontends/vercel.py:34–66, 84–88). При `UIConfig.enable_analytics=True` `ReactRuntime` вставляет скрипт Vercel Web Analytics в сам бандл (siamang/frontend/runtime/react.py:140; docs/reference/frontend.md:191). Формулировка «analytics route» повторяет ошибку docs/reference/deploy.md:323. Отметим: CSP при этом уже содержит `https://va.vercel-scripts.com` безусловно (vercel.py:24).
- **Правка:** «…cache-control for assets; при UIConfig(enable_analytics=True) в страницу бандла автоматически вставляется скрипт Vercel Web Analytics (CSP уже разрешает va.vercel-scripts.com)».

## Глава 12, раздел 12.2.2 (блок «Try it yourself»)

### [НЕТОЧНОСТЬ] `deploy()` сам ничего не печатает — survey ID нужно взять из result

- **В учебнике:** «…then use LocalBackend(path="survey.db").get_responses(survey_id=...) (the survey ID is printed at deploy time)…»
- **На самом деле:** метод `survey.deploy()` ничего не выводит (siamang/core/questionnaire.py:136–164; siamang/deploy/pipeline.py:50–81) — ID доступен как `result.survey_id`. Печатает survey_id только CLI-команда `siamang preview` (siamang/cli/preview.py:58–59).
- **Правка:** «…(the survey ID is available as result.survey_id; the siamang preview CLI prints it)».

---

## Глава 14, раздел 14.2 (вводный абзац)

### [НЕТОЧНОСТЬ] «Единая конвенция read/write» не распространяется на Dictionary*/RScriptWriter

- **В учебнике:** «The whole layer follows one convention: every reader exposes read(path, **kwargs) -> SurveyData, and every writer exposes write(data, path, **kwargs) -> Path».
- **На самом деле:** `DictionaryReader.read(path) -> VariableMap` (не SurveyData) и без `**kwargs`; `DictionaryWriter.write(variables, path)` принимает VariableMap, не SurveyData, и без `**kwargs` (siamang/io/dictionary.py:12–27); `RScriptWriter.write(data, path)` тоже без `**kwargs` (siamang/io/r.py:16). Сам учебник ниже корректно описывает Dictionary-API, противореча собственной формулировке «whole layer».
- **Правка:** «Все табличные читатели/писатели (CSV, Excel, SPSS, Stata) следуют конвенции read(path, **kwargs) -> SurveyData / write(data, path, **kwargs) -> Path; DictionaryReader/DictionaryWriter работают с VariableMap, а RScriptWriter не принимает kwargs».

## Глава 14, раздел 14.2.1

### [ОШИБКА] «Канонический» пример recode_values не делает того, что обещает

- **В учебнике:** «The canonical SPSS recode-and-export round-trip: … data = data.recode_values("age", {-1: pd.NA})  # treat -1 as missing … SPSSWriter().write(data, "output.sav")».
- **На самом деле:** `recode_values` строит новую колонку через `frame[column].map(mapping)` и без `into` пишет её в **новый** столбец `age_recoded` (siamang/data/survey_data.py:244–246). Исходный `age` не меняется, а в `age_recoded` все значения, отсутствующие в mapping, становятся NaN. Проверено: на age=[34,28,45,52] вызов `recode_values("age", {34: pd.NA})` даёт `age_recoded == [<NA>, NaN, NaN, NaN]` при нетронутом `age`. Пример «treat -1 as missing» в таком виде уничтожает данные, а не помечает −1 пропуском.
- **Правка:** заменить пример на корректный способ пометить −1 как missing: объявить missing-код в VariableMap (MissingValue(-1, ...)) и вызвать `data.apply_missing_values()`, либо `data = data.with_frame(data.frame.replace({"age": {-1: pd.NA}}))`. Если оставлять recode_values — явно оговорить семантику .map (неперечисленные значения → NaN) и создание нового столбца.

### [ОШИБКА] Параметр version у StataWriter — это версия Stata (8–15), а не код формата 117/118/119

- **В учебнике:** «StataWriter.write(data, path, version=15, **kwargs) forwards version as the target Stata file-format version (Stata 12 = 117, 13/14 = 118, 15 and later = 119).»
- **На самом деле:** `version=15` передаётся в `pyreadstat.write_dta(..., version=version)` (siamang/io/stata.py:19–37), где по документации pyreadstat это «dta file version, supported from 8 to 15, default is 15» — то есть номер версии Stata, а не внутренний код формата. Приведённый маппинг к тому же фактически неверен (у Stata: 12 → формат 115, 13 → 117, 14/15 → 118; 119 — вариант для >32767 переменных). Ошибка скопирована из docs/reference/io.md:115.
- **Правка:** «version — целевая версия Stata (поддерживаются 8–15, по умолчанию 15), передаётся в pyreadstat.write_dta». Скобку с маппингом 117/118/119 удалить.

### [НЕТОЧНОСТЬ] SPSSWriter пишет уровни измерения, а не «форматы»

- **В учебнике:** «SPSSWriter.write(data, path) writes variable labels, value labels, missing values, and formats via pyreadstat.write_sav.»
- **На самом деле:** передаются `column_labels`, `variable_value_labels`, `missing_ranges` и `variable_measure` (уровни измерения nominal/ordinal/scale) — siamang/io/spss.py:17–25. Параметр форматов (`variable_format`) не используется. «Formats» повторяет docs/reference/io.md:88.
- **Правка:** «…missing values, and measurement levels (nominal/ordinal/scale) via pyreadstat.write_sav».

### [НЕТОЧНОСТЬ] Round-trip Stata не сохраняет числовые missing-коды и шкалы; SPSS теряет kinds и valid_range

- **В учебнике:** «SPSS .sav and Stata .dta carry full metadata, so both round-trip your codebook.» (и в Try it yourself: «confirm that the SPSS round-trip preserves everything»).
- **На самом деле:** в Stata пользовательские missing-коды — только односимвольные a–z; числовые коды (99 и т.п.) `StataWriter` молча отбрасывает (`_is_stata_missing_code`, siamang/io/stata.py:99–101) — при чтении назад код 99 возвращается как обычное значение с меткой. `variable_measure` в .dta не пишется, поэтому nominal/ordinal после round-trip становятся "interval" (проверено: gender nominal → interval). В SPSS сохраняются метки, value labels и missing-коды, но kind вырождается в "system_missing" (spss.py:141–146), а valid_range не сохраняется вовсе. Проверено запуском round-trip.
- **Правка:** добавить оговорку: «SPSS сохраняет метки, value labels и missing-коды (но не kinds и не valid_range); Stata сохраняет метки и value labels, однако числовые missing-коды и уровни измерения при записи теряются — для полного сохранения кодбука прикладывайте JSON-словарь и к .dta». В Try it yourself смягчить «preserves everything».

## Глава 14, раздел 14.2.2

### [НЕТОЧНОСТЬ] Имена файлов R-бандла известны точно: import_survey.* — гадать не нужно

- **В учебнике:** «The documentation gives two different sets of file names for this bundle. … Inspect the generated directory after your first export to see which names your version produces.»
- **На самом деле:** в версии 0.5.0 код однозначен: при пути-каталоге создаются `import_survey.R`, `import_survey.csv`, `import_survey_dictionary.json` (siamang/io/r.py:31–36); скрипт использует jsonlite и оставляет объект `survey_data` (r.py:38–80) — то есть вариант wiki/Data-Import-and-Export.md верен, а docs/reference/io.md:130–136 (data.csv / dictionary.json / load_data.R с Hmisc::label) устарел. Проверено запуском. Заодно подтверждено: `path="trust.R"` даёт trust.csv / trust_dictionary.json / trust.R.
- **Правка:** заменить «version-dependent»-хедж на факт: «В текущей версии создаются import_survey.R / import_survey.csv / import_survey_dictionary.json (скрипт использует jsonlite и оставляет data frame survey_data); описание в docs/reference/io.md устарело». То же в Chapter Summary («the documented file names differ between sources»).

### [НЕТОЧНОСТЬ] data.export() полноценно поддерживает и "spss", и алиасы — хедж не нужен

- **В учебнике:** «data.export(fmt, path=None, **kwargs) supports "csv", "xlsx", "stata", and "r" per the reference documentation; the cookbook additionally uses data.export("spss", path="out.sav").»
- **На самом деле:** код поддерживает `"csv"`, `"xlsx"`/`"excel"`, `"r"`, `"spss"`/`"sav"`, `"stata"`/`"dta"` (siamang/data/survey_data.py:360–397); `export("spss", ...)` проверен и работает. Неизвестный формат поднимает `NotImplementedError` (не ValueError). Неполный список — из docs/reference/data.md:77–78.
- **Правка:** «data.export(fmt, ...) поддерживает "csv", "xlsx"/"excel", "spss"/"sav", "stata"/"dta" и "r"; неизвестный формат вызывает NotImplementedError».

## Глава 14, раздел 14.3.1

### [ОШИБКА] recode_values без `into` не обновляет столбец «на месте», а создаёт `<column>_recoded`

- **В учебнике:** «recode_values(column, mapping, *, into=None, label=None, scale=None) — Collapse or remap discrete values (e.g. {1: 0, 2: 0, 3: 1}); with into, stores the result in a new registered column, otherwise updates in place.»
- **На самом деле:** `target = into or f"{column}_recoded"` — без `into` результат пишется в новый столбец `<column>_recoded`, исходный столбец не меняется никогда (siamang/data/survey_data.py:244–246). Проверено: после `data.recode_values("gender", {1:0, 2:1})` в frame столбцы ['gender', 'age', 'gender_recoded']. Формулировка «otherwise updates the column in-place» скопирована из docs/reference/data.md:64, который расходится с кодом. Дополнительно: из-за `.map()` значения вне mapping становятся NaN (важно для примера «collapse»).
- **Правка:** «…with into, stores the result in the named new column; otherwise in a new column `<column>_recoded`. Values absent from the mapping become NaN — перечисляйте в mapping все коды, которые нужно сохранить».

### [ОШИБКА] create_index не поддерживает method="sum"

- **В учебнике:** «create_index(name, *, items, method="mean", label=None) builds the composite itself, by "mean" or "sum", and registers the new variable with an "interval" scale.»
- **На самом деле:** любой method, кроме "mean", вызывает `ValueError("create_index currently supports only method='mean'.")` (siamang/data/survey_data.py:326–327). Проверено запуском. «"mean" or "sum"» — из docs/reference/data.md:73, код это не подтверждает.
- **Правка:** «…builds the composite as the item mean (method="mean" — единственный поддерживаемый на данный момент; "sum" пока не реализован)». Соответственно поправить строку Chapter Summary, если она подразумевает sum.

### [НЕТОЧНОСТЬ] processing.recode не «in place» и не «не трогает метаданные» — он их теряет

- **В учебнике:** «data.processing.recode(column, mapping) applies a raw {old: new} mapping in place, without touching metadata.»
- **На самом деле:** `DataProcessing.recode` копирует frame, применяет `.replace(mapping)` и возвращает **новый** `SurveyData(copy)` без variables, questionnaire и weight — метаданные не «остаются нетронутыми», а полностью отбрасываются (siamang/data/processing.py:15–20). «In place» противоречит и собственному тезису книги о неизменяемости. Формулировка из docs/reference/data.md:142–143.
- **Правка:** «data.processing.recode(column, mapping) применяет сырой .replace-маппинг и возвращает новый SurveyData без метаданных (VariableMap, questionnaire и weight отбрасываются) — используйте его только когда метаданные не нужны дальше».

---

## Проверено и корректно

- 12.1.1: сигнатура `deploy(backend="local", frontend="local", *, backend_kwargs=None, frontend_kwargs=None, **options)` и дефолты "local"/"local" (questionnaire.py:136–144); bare `survey.deploy()` реально поднимает SQLite + фоновый FastAPI (проверено end-to-end: POST /responses → collect()).
- 12.1.1: entry-point-резолюция через группы `siamang.backends`/`siamang.frontends`, плагины имеют приоритет, затем встроенный реестр (registry.py:44–53); `list_backends()==['gsheets','local','supabase']`, `list_frontends()==['local','netlify','vercel']`, `backend_factory`/`frontend_factory` возвращают классы (проверено).
- 12.1.1: шестишаговый конвейер compile → provision → client template → build → publish → DeployResult и порядок ошибок (pipeline.py:50–81); NotImplementedError для неизвестного backend-шаблона.
- 12.1.1: секретная граница BackendConfig — только settings и dashboard_url попадают в бандл, internal остаётся на сервере (backend_config.py, pipeline.py:60–64); service_key в бандл не сериализуется.
- 12.2.1: таблица бэкендов (имена, хранилища, ключевые kwargs) и capability-матрица соответствуют wiki/Deployment.md и коду; LocalBackend(path="survey.db"), авто-создание родительского каталога, три таблицы survey_meta/responses/quota_counters, атомарный increment_quota через BEGIN IMMEDIATE (backends/local.py).
- 12.2.1: SupabaseBackend — конструктор url/anon_key/service_key/table="responses"/quota_function="quota-check"/auto_provision=True; env-фолбэки SIAMANG_SUPABASE_* c legacy SURVLIB_*; ValueError при пустых значениях; общая таблица responses c survey_id; RLS anon INSERT / authenticated SELECT+DELETE; SQL exec_sql дословно; SupabaseProvisionError; generate_migration_sql(); migration_dir → таймстампованный .sql (supabase.py:188–240, 334–381).
- 12.2.1: GoogleSheetsBackend — credentials_file/spreadsheet_id/sheet_name="Responses"/apps_script_url, env SIAMANG_GSHEETS_* (+SURVLIB_*), extra `pip install "siamang[gsheets]"` (pyproject.toml:77–81), системные столбцы _response_id/_submitted_at, предупреждение об Apps Script-прокси и лимиты (~100 req/100s, неатомарные квоты, 10 млн ячеек) — соответствуют коду и docs/reference/deploy.md.
- 12.2.2: таблица фронтендов; LocalFrontend port=0 → свободный порт, open_browser, проксирование POST /responses и /quota-check (проверено запросами), `siamang preview` блокируется до Ctrl+C; VercelFrontend token→VERCEL_TOKEN, team_id, project_name="siamang-survey"; NetlifyFrontend token→NETLIFY_AUTH_TOKEN c legacy SIAMANG_NETLIFY_TOKEN (netlify.py:67–70), site_id/site_name, REST-ZIP c поллингом, CLI `npx netlify deploy --prod`, локальный фолбэк .netlify_deploy_<id>/, файлы _headers (CSP, DENY, nosniff и др.) и _redirects.
- 12.2.2: пример gsheets+netlify и Tip про инициализацию из окружения — `backend_factory("gsheets")()` реально подхватывает SIAMANG_GSHEETS_CREDENTIALS_FILE/SPREADSHEET_ID без kwargs (проверено); ~/.siamang.toml пишется `siamang init` (cli/init.py, config/loader.py); таблица рекомендуемых пар совпадает с wiki.
- 12.3.1: все поля DeployResult (url, backend, frontend, survey_id, dashboard, deployed_at, backend_ref, frontend_ref, extras; frozen dataclass) — result.py; collect() возвращает pd.DataFrame через backend_ref.get_responses и поднимает RuntimeError без backend_ref (проверено оба случая); каждый deploy() создаёт новый survey_id (счётчики не переносятся).
- 13.1/13.2.1: сигнатура `simulate(self, n: int = 100, seed: int | None = 42)` (questionnaire.py:166); воспроизводимость при одинаковом seed (проверено), seed=None даёт свежие данные; результат — SurveyData c variables и questionnaire; при отсутствии реестра переменных VariableMap строится из вопросов (questionnaire.py:174–183).
- 13.2.1: таблица генерации значений по типам вопросов — NumericInput uniform в valid_range либо 18–70, LikertScale 1..points, SingleChoice случайный код, MultiChoice подмножество с min/max/exclusive (режим array — дефолтный), Ranking до max_ranked, Matrix код на суб-переменную из labels, OpenText "sample text" (local_simulator.py:24–91).
- 13.2.1: skip-logic-осведомлённость — page- и question-уровневые show_if/hide_if вычисляются по накопленным ответам, скрытое → NaN; в legacy flat-режиме условий нет и структурных NaN не возникает (simulate_from_pages/simulate_dataframe).
- 13.2.2: полный worked example выполнен дословно: shape (200, 2), число NaN в autonomy в точности равно числу consent != 1 (106 из 200 при seed=123), повторный запуск с тем же seed идентичен.
- 13.2.3: `data.report.freq(...).to_markdown()`, `data.describe_variables()`, `data.validate()` на симулированных данных работают; issues пуст (severity != "error" выполняется).
- 14.1: конструирование SurveyData вручную; `data.analysis.mean("age") == 39.75` (проверено); четыре поля frame/variables/questionnaire/weight (survey_data.py:17–22).
- 14.1.1: frozen dataclass; with_frame сохраняет variables/questionnaire/weight; with_weight поднимает ValueError для отсутствующего столбца (проверено); пять аксессоров processing/analysis/tables/report/plot с типами DataProcessing/DataAnalysis/SurveyTables/ReportAccessor/PlotAccessor; примеры data.analysis.mean, data.report.freq, data.plot.bar(...).show(), data.tables.banner(rows=..., columns=...) выполняются.
- 14.1.1: codebook() — ровно колонки name, label, scale, dtype, role, description, missing_values, missing_kinds, missing, valid_range и ValueError без метаданных; describe_variables() — name, label, scale, n, n_missing, n_unique (проверено; примечание книги о более кратком списке в docs/reference/data.md:46 точно цитирует доку).
- 14.2: реэкспорт I/O-символов на верхнем уровне — `from siamang import read_spss` работает (siamang/__init__.py); импорт-листинг из siamang.io валиден целиком.
- 14.2.1: CSV/Excel — только данные (variables=None после чтения, проверено), обёртки над pd.read_csv/to_csv(index=False)/pd.read_excel/to_excel; openpyxl и pyreadstat — обычные зависимости (pyproject.toml:33–35); SPSSReader — pyreadstat.read_sav(user_missing=True) и восстановление VariableMap (метки, value labels, missing, уровни измерения); SPSSWriter без variables пишет «голые» колонки; SurveyDataReader диспетчеризует по расширению (.csv/.xlsx/.xls/.sav/.dta) и поднимает ValueError для неизвестного суффикса (проверено).
- 14.2.2: RScriptWriter возвращает Path к R-скрипту; при path="trust.R" файлы trust.csv/trust_dictionary.json/trust.R (проверено); скрипт заменяет missing-коды на NA и применяет factor(...); DictionaryWriter/DictionaryReader — сериализация to_dict → JSON и обратно, ValueError если корень не объект; «канонический пайплайн» CSV+словарь из книги выполняется дословно; export_dictionary(path) -> Path.
- 14.3.1: сигнатура validate(raise_on_error=False) и весь список проверок (наличие колонок, dtype, valid_range, покрытие метками, weight существует и числовой, переменные questionnaire присутствуют); поля ValidationIssue (code, severity, message, variable/column); пример bad.validate() даёт ровно INVALID_LABEL_VALUE и OUT_OF_RANGE c теми же сообщениями и severity "error"; raise_on_error=True поднимает ValueError; без VariableMap — одиночный warning MISSING_METADATA (survey_data.py:113–169, variable.py:223–266; проверено).
- 14.3.1: apply_missing_values(kinds=None) → pd.NA, фильтр по kinds ({"refusal","dont_know"} — валидные kinds, variable.py:15–21); drop_missing(column); recode(...) через pandas.cut c ordinal-регистрацией; derive(...) — построчный Expression → 0/1; scale_alpha требует ≥2 items (ValueError проверен); create_index регистрирует переменную со шкалой "interval"; рекомендуемый порядок import → validate → apply_missing_values → recode/derive → analyse согласуется с API.

---

# Ревью глав 15–17 (анализ данных, таблицы и баннеры, графики)

Проверка выполнена по коду движка siamang 0.5.0 (editable-установка). Все ключевые примеры глав 15–17 запущены на симулированных данных (`survey.simulate(n=200, seed=123)`); численные выводы сверены с фактическим выводом.

## Глава 15, раздел 15.3.1
### [ОШИБКА] recode_values без `into` НЕ обновляет столбец «на месте»
- **В учебнике:** «SurveyData.recode_values(column, mapping, *, into=None, label=None, scale=None) … With into, registers a new variable; otherwise updates in place.» (таблица методов Tier 2); также далее: «passing into when you want to preserve the original column».
- **На самом деле:** в коде `target = into or f"{column}_recoded"` — без `into` результат записывается в **новый столбец** `<column>_recoded`, который регистрируется как новая переменная; исходный столбец никогда не изменяется (siamang/data/survey_data.py:235–267, проверено запуском: после `data.recode_values("remote_freq", {...})` появляется столбец `remote_freq_recoded`, исходный `remote_freq` не тронут). Учебник унаследовал ошибку из docs/reference/data.md:64 («otherwise, updates the column in-place»), но источником истины является движок.
- **Правка:** в таблице заменить «otherwise updates in place» на «без into результат записывается в новый столбец `<column>_recoded` и регистрируется как новая переменная; исходный столбец сохраняется в обоих случаях». Формулировку «passing into when you want to preserve the original column» заменить на «passing into to name the derived column yourself» (оригинал сохраняется всегда).

## Глава 15, раздел 15.3.1 (Try it yourself)
### [ОШИБКА] У recode_values нет параметра `labels`
- **В учебнике:** «once with data.recode_values(..., into="remote3", labels=...)».
- **На самом деле:** сигнатура — `recode_values(column, mapping, *, into=None, label=None, scale=None)` (siamang/data/survey_data.py:235–243); параметра `labels` нет, вызов с `labels=` даст `TypeError`. Метки значений новой переменной генерируются автоматически как `str()` от новых кодов (survey_data.py:252: `value_labels = {value: str(value) for value in mapping.values()}`), задать собственные метки через recode_values нельзя.
- **Правка:** убрать `labels=...` из упражнения: `data.recode_values("remote_freq", {1: 1, 2: 1, 3: 2, 4: 3, 5: 3}, into="remote3")`. При желании отметить, что метки новой переменной автогенерируются из кодов ("1", "2", "3").

## Глава 15, раздел 15.3.1
### [НЕТОЧНОСТЬ] data.processing.recode теряет метаданные целиком (а не «оставляет старые метки»)
- **В учебнике:** «the values change, but the variable metadata is not carried over or updated. If remote_freq keeps its old five-level value labels while the data now contains three levels, your next labeled table will mislabel or orphan categories.»
- **На самом деле:** `DataProcessing.recode` возвращает `SurveyData(copy)` — только фрейм, без `variables`, без `questionnaire` и без `weight` (siamang/data/processing.py:15–20; проверено запуском: `collapsed.variables is None`, `collapsed.weight is None`). Сценарий «переменная сохранит старые пятиуровневые метки и таблица их перепутает» невозможен: меток не остаётся вообще, следующая «labeled» таблица покажет сырые коды. Кроме того, теряется настроенный вес — это важное практическое следствие, не упомянутое в тексте.
- **Правка:** заменить гипотетическое предложение на описание реального поведения: «результат — SurveyData без каких-либо метаданных (variables, questionnaire и настроенный weight теряются); следующая таблица покажет сырые коды вместо меток, а взвешивание придётся настраивать заново».

## Глава 16, раздел 16.1
### [НЕТОЧНОСТЬ] Невалидное значение sort не «отклоняется», а молча игнорируется
- **В учебнике:** «This textbook follows the wiki; if a value is rejected in your installation, try the reference spelling.» (примечание о вариантах sort).
- **На самом деле:** FreqTable не валидирует `sort`: код проверяет только `== "freq"` и `== "label"`, любое иное значение (в т.ч. «reference-написания» "frequency"/"index") просто оставляет порядок по кодам без ошибки (siamang/reporting/tables.py:175–178; проверено: `sort="frequency"` возвращает таблицу в порядке value, исключение не возбуждается). Никакое значение никогда не «rejected». Рабочие значения — только "value"/"freq"/"label" (wiki права; docs/reference/reporting.md:48 ошибается).
- **Правка:** переформулировать: «в коде принимаются только "value"/"freq"/"label"; неизвестное значение (включая "frequency"/"index" из reference) не вызывает ошибки, а молча даёт сортировку по кодам — поэтому опечатка в sort может пройти незамеченной».

## Глава 16, раздел 16.1
### [НЕТОЧНОСТЬ] Конфликт источников о директориях export_xlsx разрешается кодом (директория обязана существовать)
- **В учебнике:** «The documentation sources disagree on directory handling for export_xlsx. … This contradiction … The safe habit is to create the output directory yourself before exporting.»
- **На самом деле:** конфликт источников описан верно (docs/reference/reporting.md:33 — «creates parent directories»; wiki/Reporting-Tables.md:179 — «the directory must already exist»), но движок его разрешает: `SurveyTable.export_xlsx` директорий не создаёт (siamang/reporting/tables.py:102–107, простой `to_excel`; проверено — экспорт в несуществующую директорию даёт OSError/FileNotFoundError). Права wiki. Заметим для контраста: `BannerTable.export_csv/export_xlsx` директории создают (siamang/data/tables.py:18–28) — учебник это корректно описывает в 16.2.
- **Правка:** совет оставить, но заменить «sources disagree / unresolved» на констатацию: «в текущей версии директории НЕ создаются (верна wiki); reference ошибается». 

## Глава 16, раздел 16.1
### [НЕТОЧНОСТЬ] Фактический HTML-класс таблицы — "dataframe siamang-table"
- **В учебнике:** «to_html() … <table class="siamang-table">; renders inline in Jupyter.»
- **На самом деле:** класс передаётся через `df.to_html(classes="siamang-table")`, и pandas добавляет свой класс: реальный тег — `<table border="0" class="dataframe siamang-table">` (siamang/reporting/tables.py:56; проверено запуском). Формулировка повторяет wiki/Reporting-Tables.md:28 и практически безвредна, но для тех, кто пишет CSS-селектор `table[class="siamang-table"]`, будет сюрпризом.
- **Правка:** уточнить: «таблица получает CSS-класс siamang-table (фактический атрибут — class="dataframe siamang-table")».

## Глава 17, раздел 17.1.1
### [НЕТОЧНОСТЬ] cmap в корреляционном режиме HeatMap действительно игнорируется — противоречие источников разрешимо
- **В учебнике:** «This contradiction is unresolved in the sources. If you need a specific correlation colormap, pass it — but verify visually that it took effect in your installation.»
- **На самом деле:** код однозначен: в режиме `by=None` seaborn.heatmap вызывается с жёстко заданными `cmap="RdBu_r", vmin=-1, vmax=1, center=0`; параметры `cmap`/`vmin`/`vmax` объекта не используются (siamang/reporting/charts.py:384–394; проверено запуском — переданный `cmap="coolwarm"` не влияет на фигуру). Права wiki (Reporting-Charts.md:113 «ignored for the correlation…»); пример из docs/reference/reporting.md:240 с `cmap="coolwarm", vmin=-1.0, vmax=1.0` вводит в заблуждение. Совет «pass it — but verify visually» предлагает заведомо бесполезное действие.
- **Правка:** заменить примечание: «в текущей версии cmap/vmin/vmax в корреляционном режиме игнорируются — матрица всегда рисуется на диверджентной шкале RdBu_r с центром 0 и диапазоном [-1, 1]; изменить colormap можно только через возвращаемый Axes/matplotlib».

## Глава 17, раздел 17.2.1
### [НЕТОЧНОСТЬ] save() гарантированно не создаёт директории — конфликт источников разрешается кодом
- **В учебнике:** «The sources disagree about directory handling in save(). The reference documentation states that parent directories are created if needed; the Reporting-Charts wiki states that the directory must already exist. To be safe across versions, create the output directory yourself…»
- **На самом деле:** `SurveyChart.save` — простой `fig.savefig(path, dpi=dpi, bbox_inches="tight")` без mkdir (siamang/reporting/charts.py:105–110; проверено — сохранение в несуществующую директорию даёт FileNotFoundError). Права wiki (Reporting-Charts.md:43); docs/reference/reporting.md:144 ошибается. Практический совет учебника верен, но подача «неизвестно, кто прав» слабее, чем позволяет источник истины.
- **Правка:** констатировать фактическое поведение («директории не создаются; верна wiki») и сохранить совет про `pathlib.Path("out").mkdir(exist_ok=True)`.

## Проверено и корректно
- Гл. 15: конструирование Work Study (Variable/VariableMap.add_many/SingleChoice/NumericInput/LikertScale/Page/Questionnaire — все импорты из siamang.core существуют) и `survey.simulate(n=200, seed=123)` — пример запускается без изменений.
- Гл. 15: `DataAnalysis` — frozen dataclass (frame, weight_column, variables) точно как в siamang/data/analysis.py:13–17; строится лениво свойством `data.analysis` (survey_data.py:28–30).
- Гл. 15: сигнатуры и семантика `mean(column, weighted=False)`, `median(column)`, `grouped_mean(column, by, weighted=False, labels=False)` (колонки group/mean/n, +label при labels=True) — совпадают; числа примеров воспроизведены точно (mean("autonomy")=3.06; вся таблица grouped_mean совпадает построчно).
- Гл. 15: weighted=True без настроенного веса → ValueError (analysis.py:26); при weighted grouped_mean колонка n = сумма весов (analysis.py:64); двухшаговая модель with_weight + weighted=True — верно.
- Гл. 15: frequencies/crosstab/proportion_ci действительно weight-aware (analysis.py:128–246), wiki/Analysis.md:139–140 перечисляет их без полных сигнатур — как и сказано в учебнике.
- Гл. 15: `kruskal` (dict statistic/p_value/groups; ValueError при <2 групп) и `mannwhitney` (ровно 2 группы, two-sided, group_a/group_b) — сигнатуры, семантика и все числа примеров (2.1330…/0.7112…; 794.0/0.8796…) воспроизведены точно; scipy — базовая зависимость (pyproject: scipy>=1.11), ImportError при отсутствии — верно.
- Гл. 15/16: правило автоселекции теста — точно как в коде GroupMeanTable (tables.py:350–367): ordinal/None → Mann–Whitney/Kruskal–Wallis, иначе t-test/ANOVA; t-test и ANOVA отдельными методами DataAnalysis не экспонируются — верно.
- Гл. 15: `effective_sample_size()` = (Σw)²/Σw², ValueError без веса (analysis.py:248–256) — верно.
- Гл. 15: сигнатура `data.processing.recode(column, mapping)` и пример collapse — верны; `SurveyData.recode(column, *, into, bins, labels=None, right=False, label=None)` через pandas.cut, регистрация ordinal-переменной, пример age_band c labels {1:'18-29',2:'30-44',3:'45+'} — воспроизведён точно; `derive(*, name, expression, label=None, scale="nominal", labels=None)` — сигнатура верна, работает (метки по умолчанию {0:'No',1:'Yes'}).
- Гл. 15: предупреждение об иммутабельности (все методы возвращают новую SurveyData) и чек-лист (validate, apply_missing_values, with_weight — все методы существуют) — верно.
- Гл. 16: `from siamang.reporting import FreqTable, CrossTable, GroupMeanTable` — есть в __init__; фабрики data.report.freq/crosstab/means — сигнатуры совпадают буквально (accessors.py:35–96); все три класса наследуют SurveyTable, строятся лениво.
- Гл. 16: общий интерфейс to_frame/to_markdown (GFM + футер статистик)/to_html/export_xlsx(path)->Path с листом "Table" — верно.
- Гл. 16: FreqTable (exclude_missing=True, sort "value"/"freq"/"label", Total-строка, футер «Variable = …; N valid = …») — markdown-вывод примера воспроизведён символ-в-символ (58/47/43/52).
- Гл. 16: CrossTable (pct "none"/"row"/"col"/"total"; Total-строка/колонка всегда в сырых счётчиках; футер χ²/df/p/Cramér's V/N; при отсутствии scipy — «scipy not installed») — вывод примера воспроизведён точно (χ²=21.4850; df=12; p=0.0437; V=0.1890); примечание о «Chi-square, Cramer's V, Phi» в reference подтверждено (reporting.md:63).
- Гл. 16: GroupMeanTable (Mean/SD/Median/N, автотест) — вывод примера воспроизведён точно (Kruskal-Wallis H = 2.1330; p = 0.7113); для age (ratio) действительно ANOVA (проверено: F = 0.8490).
- Гл. 16: `from siamang.data import SurveyTables, BannerTable`; сигнатура `banner(rows, columns, weight=None, labels=True)`, ValueError на пустые rows/columns и на отсутствующий weight, дефолт веса из with_weight — всё совпадает (data/tables.py:37–60).
- Гл. 16: структура фрейма banner (8 колонок row_variable…percent), percent — доля внутри колоночной категории, head(6) примера воспроизведён построчно; BannerTable — frozen dataclass; export_csv/export_xlsx создают родительские директории, index=False, возвращают Path — верно.
- Гл. 17: charts extra = matplotlib+seaborn (pyproject), тексты ImportError для matplotlib и seaborn совпадают с кодом дословно (charts.py:52–56, 338–339); seaborn нужен HeatMap и ScatterPlot — верно.
- Гл. 17: общий интерфейс SurveyChart — figsize=(10,6), palette="muted", title=None (авто из меток), plot()->Axes, show(), save(path, dpi=150)->Path c bbox_inches="tight", ленивое построение — всё совпадает; сигнатуры фабрик data.plot.bar/boxplot/heatmap/scatter совпадают буквально (включая отсутствие palette у heatmap).
- Гл. 17: режимы BarChart (частоты/групповые средние по by, horizontal, show_values), BoxPlot (show_points → stripplot), HeatMap (by → матрица средних; by=None → корреляция Спирмена на RdBu_r с центром 0), ScatterPlot (hue, trendline только при hue=None — charts.py:459) — верно, все примеры запущены успешно.
- Гл. 17: тик-метки из value labels («Never», «Occasionally»… — не сырые коды) — подтверждено запуском; escape hatch через plot()->Axes и пример ax.set_xlabel — работает.
- Гл. 17: встраивание в Report — add(component, *, caption=None), автоматический chart.save() в `fig_<index>.png` в asset-директории, caption → alt-text + курсивная подпись (document.py:73–141) — подтверждено запуском (fig_0.png, `![Figure 1…](fig_0.png)` + `*Figure 1…*`).
- Ссылки на документацию во всех трёх главах (wiki/Analysis.md, wiki/Working-with-Data.md, docs/reference/data.md, wiki/Reporting-Tables.md, wiki/Banner-Tables.md, docs/reference/reporting.md, wiki/Reporting-Charts.md, wiki/Report-Document.md) — все файлы существуют и покрывают заявленные темы.

---

# Ревью глав 18–19 (Report builder; сквозной туториал)

Проверка выполнена по коду siamang 0.5.0 (editable install): все примеры глав реально запускались, капстоун-туториал главы 19 собран и прогнан целиком (файл my_survey.py, `siamang validate`, `simulate(n=300, seed=42)`, все таблицы, все 7 графиков, экспорт в Markdown/HTML/xlsx/sav/dta/R, отчёт из главы 18, `Report.combine`).

## Глава 18, раздел 18.1.1
### [ОШИБКА] Имена файлов графиков: не `fig_0.png`, а `fig_<индекс блока>.png`
- **В учебнике:** «Charts materialize as PNGs named fig_<index>.png, numbered in document order» и в «Try it yourself»: «compare how Figure 1 is represented — a linked fig_0.png file versus an inline data: URI».
- **На самом деле:** `<index>` — это позиция блока во всём документе (включая текстовые блоки), а не сквозной номер фигуры: `Report.to_markdown` перебирает `enumerate(self._blocks)` и передаёт `i` в `_chart_ref` (siamang/reporting/document.py:100, 132–141). В примере раздела 18.1 график — пятый блок (heading, text, value, таблица, график), поэтому реальный прогон создаёт `out/fig_4.png`, а не `fig_0.png` (проверено запуском: в `out/` лежат `autonomy_report.md` и `fig_4.png`). Два графика в одном отчёте получат, например, `fig_4.png` и `fig_7.png` — нумерация не последовательная по фигурам.
- **Правка:** В «Try it yourself» заменить «a linked fig_0.png file» на «a linked fig_4.png file» (или «fig_<N>.png, где N — позиция блока графика»). В основном тексте уточнить: «named fig_<index>.png, where index is the block's position in the document (narrative blocks count too), so figure numbers are ordered but not consecutive».

## Глава 19, раздел 19.2.1
### [ОШИБКА] Туториальный опросник НЕ проходит `siamang validate --strict`
- **В учебнике:** «siamang validate my_survey.py --strict   # also fails on strict-level lint errors» (сразу после «# OK — no warnings.», без предупреждения, что на этом самом опроснике strict-проверка падает).
- **На самом деле:** реальный прогон `siamang validate my_survey.py --strict` на туториальном опроснике завершается с кодом 2 и сообщением `validation error: Strict questionnaire validation failed: INCOMPATIBLE_QUESTION_SCALE` — строгий линт требует, чтобы `LikertScale`-вопрос имел ordinal-шкалу, а `satisfaction` в туториале намеренно объявлена как `interval` (это нужно для автоматического выбора ANOVA в 19.3). Лinterна: `survey.lint(level='strict')` → «error INCOMPATIBLE_QUESTION_SCALE LikertScale question 'satisfaction' should use ordinal scale, got 'interval'». Обычный `siamang validate` действительно печатает «OK — no warnings.» (проверено).
- **Правка:** Явно оговорить конфликт: туториальный дизайн (interval-шкала на Likert-вопросе) осознанно нарушает strict-правило INCOMPATIBLE_QUESTION_SCALE, поэтому `--strict` на этом опроснике завершается ошибкой; либо убрать строку с `--strict` из примера. Это же исправление нужно для «Try it yourself» в 19.4 (см. ниже).

## Глава 19, раздел 19.4 (Try it yourself)
### [ОШИБКА] `sg.Script.randomize_options("q_role")` не пройдёт валидацию — id вопроса не `q_role`
- **В учебнике:** «add sg.Script.randomize_options("q_role") to the Questionnaire’s scripts list … then re-validate with siamang validate --strict and confirm the script did not disturb the routing logic.»
- **На самом деле:** упражнение падает дважды. (1) Идентификатор вопроса — это не имя Python-переменной `q_role`, а fallback-id вопроса, равный имени переменной кодбука: для туториального опросника это `it_role` (проверено: `question_fallback_id` даёт consent, age, gender, it_role, experience, remote_freq, matrix_surv_keystroke, satisfaction, autonomy, story). Реальный запуск `survey.validate()` со скриптом даёт: «Script 'randomize_q_role' targets 'q_role' which is not a known question ID or page name». (2) Даже с правильным id `--strict` всё равно завершится ошибкой INCOMPATIBLE_QUESTION_SCALE (см. предыдущий пункт). Рецепт в docs/cookbook.md:185 использует «q_party» для абстрактного опросника — переносить его буквально нельзя.
- **Правка:** Заменить на `sg.Script.randomize_options("it_role")` и предложить `siamang validate` без `--strict` (или предварительно объяснить ожидаемый strict-отказ).

## Глава 19, раздел 19.3.1
### [ОШИБКА] Ноутбук не сохраняет файлы fig_outcomes_by_remote.png и fig_surveillance_heatmap.png
- **В учебнике:** «The notebook saves two of these figures as fig_outcomes_by_remote.png and fig_surveillance_heatmap.png.»
- **На самом деле:** в шитом ноутбуке examples/full_pipeline/full_pipeline_demo.ipynb нет ни одного вызова `.save(...)` и ни одного `data.tables.banner(...)`/`export_xlsx(...)` в кодовых ячейках (проверено программным разбором всех 34 ячеек; единственные упоминания export_xlsx — в markdown и в финальном print). Графики только рендерятся через `.plot()`. Утверждение перекочевало из wiki/Tutorial-Full-Pipeline.md:264–265 и README (examples/full_pipeline/README.md перечисляет эти PNG и banner_satisfaction_by_remote.xlsx как файлы примера), но самих файлов в каталоге тоже нет — там только README.md, full_pipeline_demo.ipynb, survey_preview.html.
- **Правка:** Убрать фразу или переформулировать: «wiki и README упоминают сохранённые fig_outcomes_by_remote.png / fig_surveillance_heatmap.png, однако шитая версия ноутбука эти файлы не создаёт (нет вызовов .save()); сохраните их сами через chart.save(...)». Сами вызовы `.save()` работают — проверено.

## Глава 19, раздел 19.2.1 (Note)
### [НЕТОЧНОСТЬ] База SQLite на 250 ответов НЕ поставляется в каталоге примера
- **В учебнике:** «the SQLite database shipped in the example directory holds 250 responses stored exactly as in production. Both are documented; the difference is incidental.»
- **На самом деле:** файла survey_responses.db в examples/full_pipeline/ нет (в каталоге только README.md, full_pipeline_demo.ipynb, survey_preview.html). README действительно описывает такую базу, но wiki/Tutorial-Full-Pipeline.md:17–19 прямо говорит, что локальные артефакты (survey_responses.db, PNG, XLSX) «are git-ignored, so they are not shipped in the folder». Вдобавок шитый ноутбук базу не создаёт (в нём нет deploy-ячейки).
- **Правка:** «shipped in the example directory» → «описанная в README примера (но не поставляемая в репозитории — артефакты git-ignored)»; фразу «Both are documented» уточнить: источники противоречат друг другу, файл фактически отсутствует.

## Глава 19, раздел 19.2.1
### [НЕТОЧНОСТЬ] Комментарий к describe_variables: колонок «range/levels» нет
- **В учебнике:** «desc = data.describe_variables()     # one row per variable: scale, n, missing, range/levels»
- **На самом деле:** реальные колонки — name, label, scale, n, n_missing, n_unique (siamang/data/survey_data.py:91–111; проверено прогоном: для 300 симулированных — n=300, n_missing=148 для пост-консентных переменных, 175 для surveillance-блока). Никаких «range/levels» в выводе нет. Комментарий скопирован из wiki/Tutorial-Full-Pipeline.md:187, где он так же неточен.
- **Правка:** Комментарий заменить на «# one row per variable: scale, n, n_missing, n_unique».

## Глава 19, раздел 19.4.1 (квоты)
### [НЕТОЧНОСТЬ] «reprovisions only when the schema hash changes» противоречит коду и соседней фразе
- **В учебнике:** «Tightening a cell over time is cheap: siamang reprovisions only when the schema hash changes, so updating a limit does not rebuild the survey. Note that each deploy provisions a new survey instance with fresh quota counters.»
- **На самом деле:** первая фраза (из docs/cookbook.md:114–115) кодом не подтверждается: `SupabaseBackend.provision()` при каждом deploy генерирует новый `survey_id = uuid.uuid4().hex[:12]` и создаёт свежие записи survey_meta и quota_counters (siamang/deploy/backends/supabase.py:356–418); schema_hash вычисляется от нового survey_id + переменных (строки 108, 358) и лишь сохраняется — нигде не сравнивается. Верна вторая фраза (из wiki/Cookbook.md:86–87 и wiki/Quotas.md:113): каждый deploy — новый инстанс с обнулёнными счётчиками. В нынешнем виде два предложения учебника противоречат друг другу.
- **Правка:** Убрать «reprovisions only when the schema hash changes…» (или пометить как неточность docs/cookbook.md) и оставить: обновление лимита — это правка кода + повторный deploy, при этом создаётся новый инстанс опроса и счётчики квот начинаются с нуля.

## Глава 19, раздел 19.4.1 (взвешивание, Note)
### [НЕТОЧНОСТЬ] Взвешивание в data.report.* можно утверждать определённо: его нет
- **В учебнике:** «docs/cookbook.md shows data.report.freq("trust", weighted=True) … while wiki/Cookbook.md states that the declarative data.report.* tables are unweighted. Treat weighting in report.* as uncertain…»
- **На самом деле:** вопрос проверяем: у `ReportAccessor.freq/crosstab/means` параметра `weighted` нет вовсе (siamang/reporting/accessors.py:35–96), и вызов `data.report.freq("it_role", weighted=True)` даёт `TypeError: ReportAccessor.freq() got an unexpected keyword argument 'weighted'` (проверено). Прав wiki (wiki/Cookbook.md:200–221), а примеры docs/cookbook.md:225,235 неработоспособны.
- **Правка:** Вместо «treat as uncertain» написать определённо: декларативные data.report.*-таблицы не принимают weighted (TypeError); примеры с weighted=True в docs/cookbook.md ошибочны; веса поддерживает только data.analysis.*.

## Глава 19, раздел 19.4.1 (экспорт, Note)
### [НЕТОЧНОСТЬ] Имена файлов R-экспорта можно назвать точно; "spss" в data.export работает
- **В учебнике:** «The R export file names also differ between sources … Check your installed version’s output directory to see which naming it uses.» и «The documentation lists data.export formats as "csv", "xlsx", "stata", and "r"; the "spss" form appears in the cookbook examples.»
- **На самом деле:** проверено прогоном: `data.export("r", path="out_R/")` пишет `import_survey.csv`, `import_survey_dictionary.json`, `import_survey.R`, и скрипт оставляет объект `survey_data` — то есть верна wiki-версия (siamang/io/r.py:19–35; wiki/Data-Import-and-Export.md:152–163), а имена из docs/reference/data.md и docs/cookbook.md:324 (data.csv / dictionary.json / load_data.R) неверны. `data.export("spss", path="out.sav")` реально работает: код поддерживает "csv", "xlsx"/"excel", "r", "spss"/"sav", "stata"/"dta" (siamang/data/survey_data.py:360–397; sav/dta/R-файлы успешно созданы) — неполон именно docs/reference/data.md:78.
- **Правка:** Заменить «check your installed version» на определённое утверждение: текущая версия пишет import_survey.* и создаёт data frame survey_data (как в wiki); reference-док устарел. Отметить, что "spss" — поддерживаемый формат data.export, просто не попавший в docs/reference/data.md.

## Глава 19, раздел 19.1.1 (Tip)
### [НЕТОЧНОСТЬ] «Every siamang CLI subcommand» загружает атрибут survey — кроме init
- **В учебнике:** «Every siamang CLI subcommand loads that attribute by default, so the same file serves validation, preview, and deployment.»
- **На самом деле:** подкоманд четыре: validate, preview, deploy, init (siamang/cli/entry.py:45–52). `siamang init` создаёт ~/.siamang.toml и файл опросника не загружает; `--attribute` (default "survey") есть только у validate/preview/deploy.
- **Правка:** «Every siamang CLI subcommand» → «The validate, preview, and deploy subcommands» (вторая половина фразы уже перечисляет их корректно).

## Глава 19, раздел 19.2.1
### [НЕТОЧНОСТЬ] Пример вывода preview: survey_id короче реального, опущены строки вывода
- **В учебнике:** «# Preview ready at http://127.0.0.1:8000 / #   survey_id: 42a1c0e9 / # Press Ctrl+C to stop.»
- **На самом деле:** локальный бэкенд генерирует survey_id из 12 hex-символов (`uuid.uuid4().hex[:12]`, siamang/deploy/backends/local.py:77), а не 8, и команда дополнительно печатает строки `dashboard: …` и диагностику `[react] …` (siamang/cli/preview.py:58–62). 8-символьный id скопирован из примера wiki/CLI-Reference.md:92–96, который сам неточен. Мелочь, но пример выдаёт себя за дословный вывод.
- **Правка:** Показать 12-символьный id (например 42a1c0e9d3f1) и либо добавить строки dashboard/[react], либо пометить вывод как сокращённый.

## Проверено и корректно
- 18.1: `from siamang.reporting import Report` и `from siamang import Report` — оба импорта работают (siamang/__init__.py:66,126; reporting/__init__.py:10,23); сигнатура конструктора `Report(title=None, description=None)`, title → # H1, description → курсив (document.py:42–98).
- 18.1.1: все шесть narrative-методов и их рендеринг — heading(level=2)→`## text`, markdown/text (alias), note→`> **Note:**`, value→`**label:** value`, divider→`---` — совпадают с document.py:48–70; каждый возвращает self.
- 18.1.1: `add` принимает SurveyTable/SurveyChart/DataFrame, иначе TypeError (document.py:73–85; TypeError воспроизведён); caption курсивом над таблицей и alt-текст + курсив под графиком (document.py:107–121, подтверждено выводом); `image(path, caption=...)` есть (document.py:87).
- 18.1.1: пример отчёта воспроизводится дословно, включая числа «**Respondents:** 200», «| Never | 3.222 | 1.38 | 4.0 | 45 |» и заголовок «Remote Frequency» — это опросник Work Study из wiki/Analysis.md (n=200, seed=123), прогнан и совпал.
- 18.1.1: сигнатуры to_markdown(asset_dir=".", embed_images=False)/to_html()/save(path); embed_images=True даёт data:URI и не пишет файлов (проверено); to_html — через пакет markdown с расширением tables, всегда встраивает картинки (document.py:149–153).
- 18.1.1 (Warning): save: .md/.markdown/без суффикса → Markdown, .html/.htm → HTML, .pdf → NotImplementedError, прочие суффиксы → ValueError, родительские каталоги создаются (document.py:155–167; все три случая воспроизведены). docx/pptx-экспорт нигде в docs/wiki не упомянут — подтверждено grep.
- 18.2: Report.combine(reports, title=..., toc=True): H2-заголовки секций, описание курсивом, Contents со slug-якорями (lowercase, не-алфанумерика → «-», `#data-cleaning`) — совпадает с document.py:170–189 и воспроизведено; combine возвращает Report с теми же терминальными методами.
- 18.2.1 (Note): Report действительно документирован только в wiki/Report-Document.md; docs/reference/reporting.md описывает таблицы/графики и ReportAccessor, но не класс Report — подтверждено.
- Ссылки на документацию гл. 18 и 19: все упомянутые файлы (wiki/Report-Document.md, Reporting-Tables.md, Reporting-Charts.md, Tutorial-Full-Pipeline.md, Cookbook.md, Simulation.md, CLI-Reference.md, Working-with-Data.md; docs/reference/reporting.md, cli.md, data.md; docs/cookbook.md; examples/full_pipeline/{README.md,full_pipeline_demo.ipynb,survey_preview.html}) существуют.
- 19.1.1: весь код 12 переменных / 10 вопросов / 5 страниц с show_if собран и выполнен без изменений; `len(variables)` = 12, `len(survey.pages)` = 5; совпадает дословно с wiki/Tutorial-Full-Pipeline.md и ноутбуком (сверено с ячейками 3 и 5).
- 19.1.1: survey_preview.html — standalone SurveyJS-рендер именно этого опросника (title «Remote Work, Autonomy & Digital Surveillance», SurveyJS/survey-core в файле).
- 19.2.1: `siamang validate my_survey.py` → «OK — no warnings.» (exit 0); формат печати lint-предупреждений `[severity] [code] message (location)` — cli/validate.py:39–41.
- 19.2.1: preview — действительно локальный FastAPI (uvicorn) + React-рантайм + SQLite LocalBackend, флаги --port/--open/--db (cli/entry.py:20–26, deploy/frontends/local.py, deploy/backends/local.py).
- 19.2.1: simulate(n=300, seed=42) → SurveyData c frame (300, 12), VariableMap и questionnaire attached (questionnaire.py:166–186); паттерн пропусков подтверждён: у 148 не-консентеров NaN во всех последующих переменных, у 27 on-site (remote_freq=1) NaN во всех трёх surveillance-переменных. Сид воспроизводим: мой прогон freq("it_role") побайтно совпал с сохранённым выводом ноутбука. Try-it-yourself с seed=7 тоже работает (паттерн пропусков сохраняется).
- 19.2.1 (Warning): каветка о случайных данных без корреляционной структуры — дословно соответствует wiki/Simulation.md:48–50.
- 19.3.1: freq (N, %, Cumulative %, строка Total, sort="freq"), crosstab (χ², df, p, Cramér's V, N; pct: none/row/col/total), means (Kruskal–Wallis для ordinal, ANOVA для interval; Mann-Whitney/t-test для 2 групп) — всё совпадает с reporting/tables.py и подтверждено прогоном; таблица выбора тестов верна (tables.py:349–367).
- 19.3.1: все 7 вызовов графиков из главы выполняются (bar/bar by/boxplot/boxplot show_points/heatmap by с vmin-vmax/heatmap-корреляция Spearman/scatter hue); heatmap с by= — групповые средние, без by= — Spearman-корреляция (charts.py:350–395); charts-экстра `pip install "siamang[charts]"` существует (pyproject.toml:72–75).
- 19.3.1: экспорт xtab.to_frame()/to_markdown()/to_html() и data.tables.banner(...).export_xlsx(...) работают (banner xlsx создан); таблица «Traditional vs Siamang» и финальный «Pipeline complete!» дословно совпадают с ячейками 32–33 ноутбука; в ноутбуке 34 ячейки, все 20 кодовых — с сохранёнными выводами.
- 19.4.1: рецепты cookbook существуют в docs/cookbook.md и wiki/Cookbook.md; `sg.Quota("gender", 1, limit=200)` валиден (core/quota.py:13–17); `{"status": "quota_full"}` и закрытый экран — так и документировано (wiki/Cookbook.md:71–72, wiki/Quotas.md:61–63; React-рантайм проверяет status==="quota_full").
- 19.4.1: data.scale_alpha([...]) и data.create_index(..., method="mean") работают; индекс регистрируется со шкалой interval (survey_data.py:318–347, подтверждено).
- 19.4.1: код взвешивания выполняется: with_frame(...).with_weight("weight"), analysis.mean(weighted=True), proportion_ci(..., weighted=True), effective_sample_size() = (Σw)²/Σw² — формула Киша, ESS 277.3 ≤ 300 (analysis.py:248–257); simulate() действительно не создаёт колонку weight.
- 19.4.1: data.export("spss"/"stata"/"r") и export_dictionary("dict.json") выполнены успешно, файлы созданы.

---

# Ревью глав 20–21 (Siamang Cloud: обзор, аккаунты, первый проект; веб-приложение, организации и роли)

Проверка выполнена против кода платформы (/home/user/siamang_cloud: api/, web/, docs/) и
пользовательской документации (/home/user/siamang/wiki/Cloud-*.md, /home/user/siamang/docs/cloud/).
Важно: несколько утверждений учебника дословно повторяют wiki, но wiki в этих местах
отстала от кода — код считается источником истины о фактическом поведении продукта.

## Глава 20, раздел 20.3.1
### [ОШИБКА] Example-проект содержит два аналитических скрипта, а не четыре
- **В учебнике:** «plus four analysis scripts (cleaning.py, weights.py, tables.py, drivers.py)» и в Chapter Summary: «ships a full questionnaire, four analysis scripts, ~300 sample responses»; также в таблице layout: «scripts/ — Analysis scripts (in the example: cleaning.py, weights.py, tables.py, drivers.py)».
- **На самом деле:** сидируемый Example-проект содержит ровно два скрипта: `scripts/cleaning.py` и `scripts/tables.py` — /home/user/siamang_cloud/api/app/services/example_project.py:50-59 (tasks в siamang.yaml) и :539-540 (файлы стартового коммита). Файлы `weights.py` и `drivers.py` нигде в репозитории облака не встречаются (grep по всему api/ и web/ пуст). Wiki (Cloud-Quick-Start.md:37, Cloud-Your-First-Project.md:57) здесь тоже устарела — она утверждает четыре скрипта, но код им противоречит; UI-модалка создания проекта говорит нейтрально «analysis scripts and ~300 sample responses» (web/components/modals.tsx:80).
- **Правка:** заменить «four analysis scripts (cleaning.py, weights.py, tables.py, drivers.py)» на «two analysis scripts (cleaning.py — очистка данных, tables.py — частоты, кросстаб с хи-квадратом и Markdown-отчёт)». Исправить таблицу layout и соответствующую строку Chapter Summary.

## Глава 20, раздел 20.3.1
### [ОШИБКА] Порядок Run all «clean → weight → tabulate» не соответствует пайплайну примера
- **В учебнике:** «Click Run on a single script or Run all to run every step in order (clean → weight → tabulate) and combine the results into one report.»
- **На самом деле:** в Example-проекте два шага: cleaning → tables (example_project.py:50-59); шага взвешивания нет. Комментарий в сидируемом siamang.yaml: «Run both in order with "Run all"» (example_project.py:61).
- **Правка:** заменить «(clean → weight → tabulate)» на «(clean → tabulate)» либо убрать перечисление шагов.

## Глава 20, раздел 20.3.1 (шаг 7 и «Try it yourself»)
### [ОШИБКА] Data insights на Dashboard выключены по умолчанию и настраиваются через siamang.yaml
- **В учебнике:** «On the Dashboard, the Data insights section charts the data live — response and respondent counts, responses per day, a frequency chart for any variable, and a two-way crosstab.» И в «Try it yourself»: «open the Dashboard to see the frequency chart update».
- **На самом деле:** Data Insights выключены по умолчанию; секция появляется только если в `siamang.yaml` объявлен блок `insights:` — web/components/screens/dashboard.tsx:113-165 («Off by default. A project opts in by declaring an `insights:` block»; без блока показывается только подсказка с кнопкой Configure). В сидируемом Example-проекте блок `insights:` закомментирован — api/app/services/example_project.py:95-105. Прежний всегда включённый интерактивный explorer с селекторами frequency/crosstab удалён — docs/progress/0022-custom-data-insights.md. Frequency-график строится для переменной, заданной в конфиге, а не «для любой переменной» интерактивно.
- **Правка:** переписать шаг 7: базовая строка статистики Dashboard (status, branch, responses, commits, deployments) видна всегда, а живые графики (stats/timeseries/frequency/crosstab) нужно включить, раскомментировав или добавив блок `insights:` в siamang.yaml (в Example он приведён в комментарии). Скорректировать «Try it yourself» (сначала включить insights) и строку Chapter Summary.

## Глава 20, раздел 20.2.1
### [НЕ ПОДТВЕРЖДЕНО] SSH-адрес клона в диалоге Repository → Remotes
- **В учебнике:** «then clone or push using the SSH address shown under Repository → Remotes in your project».
- **На самом деле:** диалог Remotes («Repository connections») показывает только HTTPS: Clone URL (hint «HTTPS»), Username, Access token и готовую команду `git clone` — web/components/modals.tsx:616-628; API-ответ `CloneInfoOut` содержит только `http_url`, `username`, `token` и не имеет ssh_url — api/app/schemas.py:365-368. Регистрация SSH-ключей в Profile → SSH keys есть (api/app/routers/projects.py:719-737, web/components/screens/profile.tsx), ключи прописываются в Gitea, но SSH-адрес репозитория в UI нигде не отображается.
- **Правка:** убрать/смягчить фразу про «SSH address shown under Repository → Remotes»: указать, что диалог Remotes даёт HTTPS-URL и токен, а SSH-ключи добавляются в Profile → SSH keys (SSH-адрес UI сейчас не показывает). То же касается §21.2.1 («copy the HTTPS or SSH clone command») и Learning Objectives/Summary главы 21 («over HTTPS or SSH»).

## Глава 20, раздел 20.2.1
### [НЕТОЧНОСТЬ] Текущий пароль при смене пароля запрашивается не всегда
- **В учебнике:** «On the Security tab you enter your current password, then the new password twice, and click Save — you stay signed in.»
- **На самом деле:** поле «Current password» показывается только вне Supabase-режима аутентификации: «In supabase mode, current password is not needed (Supabase PUT /user updates directly)», `needsCurrent = !USE_MOCK && AUTH_MODE !== "supabase"` — web/components/screens/profile.tsx:31-36,152. Продакшен-развёртывание облака использует Supabase (deploy/path-a-vercel-coolify-supabase.md, path-b-vercel-fly-supabase.md), т.е. там текущий пароль не запрашивается.
- **Правка:** смягчить: «введите новый пароль дважды (в некоторых конфигурациях также текущий пароль) и нажмите Save».

## Глава 20, раздел 20.3.2
### [НЕ ПОДТВЕРЖДЕНО] «nothing is ever charged» — в коде существует платный бета-промо pro_year
- **В учебнике:** «Plan switching is turned off; other plans show "Available at the official release," and nothing is ever charged.»
- **На самом деле:** формулировка соответствует wiki (Cloud-Subscription-Tiers.md:66-78) и поведению без платёжного провайдера (кнопки планов задизейблены с подписью «Available at the official release» — web/components/screens/org-settings.tsx:336-341). Однако код уже содержит покупаемый во время беты промо «pro_year» — 12 месяцев Pro за разовый платёж $1200 через Stripe Checkout (api/app/services/billing.py:29-38, PROMO_PRICE_CENTS=120000) и CTA «Extend Pro» на карточке триала (org-settings.tsx:341-346). При включённом Stripe оплата во время беты возможна.
- **Правка:** оставить формулировку как «документированное правило беты», но убрать категоричное «nothing is ever charged» либо добавить оговорку, что платные предложения (например годовой Pro) могут появиться до официального релиза.

## Глава 21, раздел 21.1.1 (таблица Project screens, строка Connectors) и Chapter Summary
### [НЕТОЧНОСТЬ] Коннекторы доступны начиная с Plus, а не только Pro/Corporate
- **В учебнике:** «Connectors — Send project data to external stores … — a Pro / Corporate feature, with some targets still rolling out.»
- **На самом деле:** гейтинг по-цельный (per-target), и поверхность Connectors открывается с Plus: sheets, excel365, supabase, airtable, dropbox и github (git-зеркало) — план Plus; s3, gcs, azure, bigquery, snowflake, database, gitlab, sftp, redcap, http — Pro; mcp — Corporate. Источники: api/app/services/limits.py:106-127 (CONNECTOR_MIN_PLAN), web/lib/plans.ts:56-63, docs/progress/0018-connector-tiering.md («поверхность Connectors открывается с Plus»). Feature-флаг connectors входит в план Plus (limits.py:56). Wiki (Cloud-Subscription-Tiers.md:19,47) здесь устарела.
- **Правка:** заменить «a Pro / Corporate feature» на «доступно с плана Plus (первые цели: Google Sheets, Excel 365, Supabase); объектные хранилища и склады данных (S3, BigQuery, Snowflake, свой Postgres) — с Pro». Исправить и строку Summary главы 21.

## Глава 21, раздел 21.2.1 (Mirrors)
### [НЕТОЧНОСТЬ] Зеркало на GitHub доступно с Plus; Pro нужен только для GitLab
- **В учебнике:** «Mirror to GitHub or GitLab (a Pro / Corporate feature).»
- **На самом деле:** GitHub-зеркало доступно с плана Plus, GitLab — с Pro: api/app/services/limits.py:108,121 (github: "plus", gitlab: "pro"); комментарий в UI: «GitHub needs Plus, GitLab/Custom Pro» — web/components/modals.tsx:551; web/lib/plans.ts:57-61.
- **Правка:** «Mirror to GitHub (план Plus и выше) or GitLab (план Pro и выше)». Соответственно поправить строку Summary «GitHub/GitLab mirroring (Pro / Corporate)».

## Глава 21, раздел 21.3.1 (и Note-блок с чек-листом инвайта)
### [НЕТОЧНОСТЬ] Приглашать можно и человека без аккаунта — создаётся pending-инвайт по email
- **В учебнике:** «Inviting a teammate requires … an invitee who already has a Siamang Cloud account …» и в Note: «the person must already have a Siamang Cloud account».
- **На самом деле:** если аккаунта с таким email нет, код создаёт отложенное приглашение и отправляет ссылку на почту: «No account yet: create a pending invitation and email the link» — api/app/routers/orgs.py:259-262; приём инвайта по токену — api/app/routers/invites.py:74-123 и страница web/app/invite/[token]/page.tsx (приглашённый регистрируется/входит с тем же email и принимает приглашение). Wiki (Cloud-Organizations-and-Team.md:43, Cloud-FAQ-and-Troubleshooting.md:108) здесь устарела.
- **Правка:** заменить на «приглашение отправляется по email; если у человека ещё нет аккаунта, он получит ссылку-приглашение и создаст его при принятии (email аккаунта должен совпадать с email приглашения)». Убрать пункт «already has an account» из чек-листа Note.

## Глава 20, раздел 20.3.1 (шаг 8) и Глава 21, раздел 21.1.1 (строка Analysis)
### [НЕТОЧНОСТЬ] Run history: статусы и представление запусков описаны по старому UI
- **В учебнике:** «Each run appears in Run history as completed or failed, with Logs and Outputs tabs» (гл. 20) и «Run history records each run as completed or failed with Logs and Outputs» (гл. 21).
- **На самом деле:** статусы запусков в UI — success / warnings / failed / running (web/components/screens/analysis.tsx:10); история отображается карточками запусков со степпером шагов, чипами outputs и разворачиваемыми логами — отдельной панели с вкладками «Logs» и «Outputs» нет («output chips, actions and collapsible logs — no side panel needed» — analysis.tsx:79; рефакторинг описан в docs/progress/0016-analysis-run-cards-and-pipeline.md). Заголовок «Run history» существует (analysis.tsx:271).
- **Правка:** заменить «completed or failed, with Logs and Outputs tabs» на «завершается со статусом success/failed (или warnings); карточка запуска показывает шаги, ссылки на outputs (отчёт, таблицы, файлы) и разворачиваемые логи».

## Проверено и корректно
- Гл. 20: определение Siamang Cloud («the hosted home for your surveys»), связь с библиотекой и таблица «library vs Cloud» — дословно по wiki/Cloud-Overview.md:3-50.
- Гл. 20: оператор Siamang Labs LLC, open beta, бесплатно, «as is», без SLA, «features may change», совет хранить свои копии — /home/user/siamang/docs/cloud/terms-of-use.md:5-8,71-85.
- Гл. 20: вход через GitHub или email/пароль, «Forgot password? → Send reset link» — web/app/(auth)/login/page.tsx:21,28,365,234-254.
- Гл. 20: шесть вкладок Profile (Account, Security, Appearance, API keys, SSH keys, Support) — web/components/screens/profile.tsx:14; тема light/dark только в Appearance (profile.tsx:166-169; wiki/Cloud-Web-App.md:12); 2FA/сессий нет, и учебник их не обещает.
- Гл. 20: API-ключи формата sck_, показываются один раз, отзыв Revoke, заголовок Authorization: Bearer — api/app/auth/api_keys.py:3,18; profile.tsx:68-72,182.
- Гл. 20: SSH-ключи: ssh-keygen, публичный ключ, Add SSH key с меткой — api/app/routers/projects.py:719-737; profile.tsx:79-101 (сам SSH-адрес клона — см. замечание выше).
- Гл. 20: privacy: controller/processor, нет рекламных трекеров и продажи данных, cookies только для входа/предпочтений, 16+ — docs/cloud/privacy-policy.md:19-20,47,51-53,120; terms-of-use.md:34.
- Гл. 20: «You own what you create», экспорт/удаление в любой момент, удаление отдельных ответов (GDPR) — terms-of-use.md:57-67; api/app/routers/database.py:87-105.
- Гл. 20: исследование «Digital Life & Wellbeing 2026» существует и полное: consent, скрининг (DisqualificationPage), квоты (Quota age_group 3×400), все типы вопросов, show_if/AND/NOT/isin, кастомная финальная страница — api/app/services/example_project.py:109-401; ~300 синтетических ответов (synthetic_rows n=300, seed_sample_data n=300) — example_project.py:569,688.
- Гл. 20: стартовые точки Example / Template (минимальный опрос + два скрипта cleaning.py, final_tables.py) / Empty (опрос из одного вопроса) — api/app/services/skeleton.py:100-138,159-252; web/components/modals.tsx:78-80.
- Гл. 20: окружения pilot (cap 50) и main (cap 1200) — example_project.py:47-48, skeleton.py:15-16.
- Гл. 20: стандартный layout репозитория (siamang.yaml, survey/questionnaire.py, scripts/, outputs/, reports/, README.md) — skeleton.py:159-171; wiki/Cloud-Your-First-Project.md:53-60.
- Гл. 20: Preview строит staging-версию и не принимает реальных ответов — api/app/routers/deployments.py:152-166 («no ingest, not accepting responses»).
- Гл. 20/21: экспорт в CSV, Excel, SPSS (.sav), Parquet, SQLite — web/components/screens/database.tsx:139; api/app/services/export_service.py:23,66-73.
- Гл. 20: правила беты — 30-дневный Pro-триал (config.py:83 trial_default_days=30; invites.py:121), read-only после окончания с сохранением данных и экспортом (deps.py:116-131 FROZEN_DETAIL + _assert_org_access: GET/HEAD/OPTIONS разрешены, мутации 403), баннер «workspace is now read-only … until the official release» (app.tsx:292-301), переключение планов отключено с подписью «Available at the official release» (org-settings.tsx:340), Stripe-биллинг в коде подготовлен (routers/billing.py), биллинг per-org и только owner меняет план (orgs.py:159-162).
- Гл. 20: четыре плана Free/Plus/Pro/Corporate и их лимиты — api/app/services/limits.py:43-80; wiki/Cloud-Subscription-Tiers.md.
- Гл. 21: топ-бар: переключатель организаций, счётчик триала «Pro trial · Nd», кнопка Console внутри проекта, меню аккаунта — app.tsx:266-289,109; темы в топ-баре нет.
- Гл. 21: сайдбар организации (Projects, Team, Settings) и проекта (Dashboard · Repository · Database · Deployments · Analysis · Connectors · Files · Settings) с точкой статуса валидации у имени проекта — app.tsx:318-347; web/lib/mock.ts:83-93.
- Гл. 21: экран Organizations (тип, роль, план; owner конвертирует personal → cooperative, для не-owner кнопка задизейблена) — web/components/screens/organizations.tsx:21-67.
- Гл. 21: экран Projects (строки со статусом и числом ответов; на лимите плана кнопка New project задизейблена с призывом апгрейда) — web/components/screens/projects.tsx:40-56,91-101.
- Гл. 21: Team — read-only ростер (Member, Email, Role, Since) с кнопкой Manage members → Settings → Members — web/components/screens/team.tsx:7-53.
- Гл. 21: Dashboard: строка stats (status, branch, responses, commits, deployments), README, recent commits, Languages, latest deployment; в insights есть respondents/partial rate/last response/responses per day — dashboard.tsx:14-22,236-300 (сами insights — см. замечание выше).
- Гл. 21: Database: вкладки Data/Schema, фильтр, сортировка, пагинация, удаление отдельного ответа — database.tsx:11-45; api/app/routers/database.py:87-105.
- Гл. 21: Deployments: статусы Live/Building/Failed/Stopped, публичный URL, монитор (ответы против cap, quota cells, codebook), Logs, Stop/Redeploy — deployments.tsx:10,45-69,137-167.
- Гл. 21: Files: две группы Repository outputs и Assets (uploads & exports), Upload/Download/Delete, лимит 50 MB на файл — files.tsx:27-56; api/app/routers/files.py:27,88-91.
- Гл. 21: шесть вкладок настроек проекта General/Runtime/Secrets/Git/Activity/Danger Zone — settings.tsx:12; защита main требует прохождения валидации, включается owner/admin (manager+) — settings.tsx:161, projects.py:707-709.
- Гл. 21: Console — кнопка в топ-баре и клавиша backtick; команды `schedules`, `schedule add --cron "<expr>" (--all | --script <name>)`, `schedule rm <id>` — console.tsx:56, app.tsx:272-275, web/lib/console/commands.ts:430-456.
- Гл. 21: редактор — подсветка Python/YAML/Markdown, номера строк, маркер modified, Save & commit / Ctrl(Cmd)+S, валидация на каждом коммите, «никогда не сохраняет без коммита» — monaco-editor.tsx:22-24, repository.tsx:52,73.
- Гл. 21: история коммитов с diff, ветки, pull request'ы, New file/rename/move/delete как коммиты — repository.tsx, projects.py:655-676 и далее (PR endpoints).
- Гл. 21: секреты проекта — роль member (developer) достаточна, encrypted и write-only, ссылка по имени — api/app/routers/secrets.py:45,83; wiki/Cloud-Repository-and-Editing.md:54-68.
- Гл. 21: зеркала — Sync now, пауза/возобновление (Disable/Enable, тосты «Mirror paused/resumed»), удаление; секрет с токеном — modals.tsx:594-663; api/app/routers/mirrors.py:105-283.
- Гл. 21: Markdown-файлы с Preview/Edit и загрузкой MD/HTML — web/components/markdown.tsx:100-112.
- Гл. 21: типы организаций personal/cooperative, конвертация только owner'ом, cooperative→personal оставляет только owner'а — orgs.py:123-145.
- Гл. 21: роли owner/admin/member, ровно один owner (инвайтом owner не выдаётся, owner нельзя изменить/удалить) — deps.py:24-33; orgs.py:246-266,378-383.
- Гл. 21: матрица прав: создать проект — admin+ (projects.py:128-129); edit/commit/deploy/secrets — member (require_role("developer") в repository/deployments/secrets); инвайты и управление участниками — admin+ (orgs.py:247); план/биллинг — только owner (orgs.py:161-162); org Activity — admin+ (orgs.py:399), у проекта своя Activity (projects.py:386, settings.tsx).
- Гл. 21: Activity — аудит-фид (deploys, runs, invites, deletions) с фильтром по времени — web/components/audit-feed.tsx:3-46.
- Гл. 20/21: ссылки Documentation References — все перечисленные файлы wiki/Cloud-*.md и docs/cloud/*.md существуют (/home/user/siamang/wiki/, /home/user/siamang/docs/cloud/).
- Движок siamang корректно охарактеризован как source-available (PolyForm Noncommercial + коммерческая лицензия) — /home/user/siamang/LICENSE:1-9.

---

# Ревью глав 22–24 (Siamang Cloud: deploy/данные/анализ; коннекторы/расписания/вебхуки; тарифы/siamang.yaml/FAQ)

Общее замечание: часть спорных утверждений учебника дословно повторяет wiki движка
(/home/user/siamang/wiki/Cloud-*.md), которая отстала от кода платформы. Источник истины —
код и docs/ в /home/user/siamang_cloud; расхождения ниже сверены именно с ним.

---

## Глава 22, раздел 22.3.1

### [ОШИБКА] Пример-проект: «три шага» и «четыре скрипта» — на самом деле два
- **В учебнике:** «The example project wires three steps this way — cleaning, weighting, and final tables.» и «The example study “Digital Life & Wellbeing 2026” ships four analysis scripts (cleaning.py, weights.py, tables.py, drivers.py) in its scripts/ folder, while the annotated siamang.yaml examples in the documentation declare three analysis tasks.»
- **На самом деле:** пример-проект содержит ровно ДВА скрипта и ДВЕ analysis-задачи: `cleaning` (scripts/cleaning.py) и `tables` (scripts/tables.py) — /home/user/siamang_cloud/api/app/services/example_project.py:50-59 (siamang.yaml примера) и :534-545 (`example_files()`: только cleaning.py и tables.py). Файлов weights.py и drivers.py не существует; отдельного шага взвешивания нет (tables.py считает невзвешенные таблицы, example_project.py:13 «tables (weighted-free…»). Приведённый в учебнике yaml-фрагмент с задачами `cleaning`/`final_tables` — это скелет проекта типа Template (/home/user/siamang_cloud/api/app/services/skeleton.py:18-29), а не пример-проекта. Утверждение о «четырёх скриптах» взято из устаревшей wiki (/home/user/siamang/wiki/Cloud-Your-First-Project.md:57).
- **Правка:** заменить на: пример-проект объявляет два шага — cleaning и tables; убрать примечание про четыре скрипта и «три задачи в документации» (или переписать: «в проекте из шаблона Template задачи называются cleaning и final_tables»). Пайплайн-пример «clean → weight → tabulate» заменить на «clean → tabulate» либо явно пометить взвешивание как пользовательское расширение.

### [ОШИБКА] Dashboard «Data insights»: описан всегда включённый интерактивный обозреватель — на деле виджеты объявляются в siamang.yaml и по умолчанию выключены
- **В учебнике:** «The Dashboard’s Data insights section computes live over all collected responses and offers four views: a summary …; a responses-per-day chart …; a frequency chart showing any variable’s distribution as a bar chart (pick the variable from a dropdown); and a two-way crosstab of any two variables, with row and column totals.»
- **На самом деле:** Data insights по умолчанию выключены; проект включает их, объявив в siamang.yaml блок `insights:` со списком виджетов типов `stats` / `timeseries` / `frequency` / `crosstab` — /home/user/siamang_cloud/web/components/screens/dashboard.tsx:113-114 («Off by default. A project opts in by declaring an `insights:` block»), /home/user/siamang_cloud/api/app/routers/dashboard.py:30 (`_INSIGHT_TYPES`), :33-71 (`_insights_from_yaml`). Переменные виджетов фиксируются в конфиге (`variable:`, `rows:`/`cols:`), выпадающего списка выбора переменной в UI нет (dashboard.tsx:35-49, :53-96 — FrequencyWidget/CrosstabWidget получают переменные пропсами). Без блока insights показывается только подсказка «Data insights are off for this project…» (dashboard.tsx:151-165). Итоговые суммы по строкам/столбцам в кросстабе — есть (dashboard.tsx:72-90).
- **Правка:** переписать абзац: четыре типа виджетов (stats, timeseries, frequency, crosstab) «прикалываются» к Dashboard объявлением блока `insights:` в siamang.yaml (по умолчанию выключено, переменные задаются в конфиге, не выпадающим списком). Соответственно упомянуть ключ `insights:` в главе 24 (см. ниже).

### [НЕТОЧНОСТЬ] Run history: «панель с двумя вкладками Logs/Outputs и кнопкой Copy»
- **В учебнике:** «Clicking a run opens a detail panel with two tabs: Logs, containing everything the script printed plus the error if it failed (with a Copy button…), and Outputs, with links to what the run produced…»
- **На самом деле:** запуск отображается карточкой (в стиле карточки деплоя) с чипами выходов (report / таблицы / файлы), выдержкой ошибки и раскрывающимся блоком «View logs»; никаких вкладок и кнопки Copy у логов нет — /home/user/siamang_cloud/web/components/screens/analysis.tsx:78-79 («One run as a Deployments-style card … no side panel needed»), :112-131 (чипы outputs, клик по таблице ведёт в Database), :154-161 (сворачиваемые логи).
- **Правка:** описать карточку запуска: статус, чипы Outputs (отчёт открывается в Repository, таблицы — переход в Database, файлы скачиваются), сворачиваемые логи с текстом ошибки. Убрать «две вкладки» и «Copy button».

## Глава 22, раздел 22.2.1

### [ОШИБКА] Экспорт SPSS .sav «несёт метки переменных и значений»
- **В учебнике:** «SPSS | .sav | Carries variable and value labels with the data — the format to hand a colleague who works in SPSS.»
- **На самом деле:** экспорт из Database пишет .sav через `pyreadstat.write_sav(safe, path)` без каких-либо меток (variable/value labels не передаются) — /home/user/siamang_cloud/api/app/services/export_service.py:94-99. Метки в .sav умеет писать SPSSWriter движка (в аналитическом скрипте), но не кнопка Export.
- **Правка:** убрать утверждение про метки в экспортируемом .sav (оставить «формат для коллег в SPSS»), либо уточнить: labelled .sav получают аналитическим скриптом (SPSSWriter движка / db.export_table), а Database → Export выгружает данные без меток.

## Глава 22, раздел 22.3.2

### [НЕТОЧНОСТЬ] «Weight-функции возвращают Series, готовую для передачи в weight=»
- **В учебнике:** «The weight functions return a Series scaled to mean 1.0, ready to pass as the weight= argument to frequencies or crosstab.»
- **На самом деле:** параметр `weight` в `frequencies`/`crosstab` — это ИМЯ КОЛОНКИ (`weight: str | None`), а не Series: /home/user/siamang_cloud/sdk/siamang_cloud/analysis.py:21-23, :43-49. Series нужно сначала записать в DataFrame (`df["w"] = …`) и передать `weight="w"` — worked example учебника делает именно так, но фраза вводит в заблуждение (передача самой Series упадёт).
- **Правка:** «…возвращают Series со средним 1.0 — сохраните её колонкой (например, df["w"] = …) и передайте имя колонки в weight=».

### [НЕТОЧНОСТЬ] «Worked example — the same shape as the tables.py step in the example study»
- **В учебнике:** «This script — the same shape as the tables.py step in the example study — reads responses, cleans them, rakes the sample to census margins…»
- **На самом деле:** tables.py примера не делает взвешивания/raking (невзвешенные frequencies + crosstab + chi2 поверх clean_responses) — /home/user/siamang_cloud/api/app/services/example_project.py:441-481; дедуп/спидеры — в cleaning.py. Сам код примера учебника при этом корректен: импорт-поверхность и все вызовы проверены исполнением против sdk/ (worked example выполняется и сохраняет отчёт).
- **Правка:** смягчить: «расширенная версия пары cleaning.py + tables.py из примера (с добавленным raking)».

## Глава 22 — прочее (мелкое)

### [НЕТОЧНОСТЬ] «any additional packages your scripts need are declared in the runtime: section»
- **В учебнике (22.3.2):** «…the Python version and any additional packages your scripts need are declared in the runtime: section of siamang.yaml».
- **На самом деле:** в `runtime.packages` можно объявлять только пакеты из кураторского allowlist — валидация коммита отклоняет прочие: /home/user/siamang_cloud/worker/app/packages.py:1-10, /home/user/siamang_cloud/worker/app/tasks/validate.py:47-52 («packages not available in the sandbox … Use a package from the curated allowlist, or request it be added»); список — worker/app/allowed_packages.txt (numpy, pandas, scipy, statsmodels, scikit-learn, matplotlib, seaborn, pingouin, lifelines, openpyxl, pyreadstat, pyarrow, tabulate, PyYAML, factor-analyzer, prince, semopy, krippendorff).
- **Правка:** добавить оговорку про кураторский allowlist (произвольный пакет с PyPI поставить нельзя; валидация коммита сообщит о недоступном пакете).

---

## Глава 23, разделы 23.0 / 23.1 / Chapter Summary

### [ОШИБКА] Гейтинг коннекторов: «Pro или Corporate» — на самом деле поверхность открывается с Plus, тарификация по-таргетно
- **В учебнике:** «…connectors require Pro or Corporate» (Learning-контекст 23.0), «they are a Pro / Corporate feature» (23.1), «Connectors … are a Pro / Corporate feature» (Summary).
- **На самом деле:** флаг `FEATURE_CONNECTORS` входит уже в план Plus — /home/user/siamang_cloud/api/app/services/limits.py:51-57; каждый таргет имеет собственный минимальный план (`CONNECTOR_MIN_PLAN`, limits.py:106-127): Plus — sheets, excel365, supabase, github(mirror), airtable, dropbox; Pro — s3, gcs, azure, bigquery, snowflake, database, sftp, redcap, http, gitlab(mirror); Corporate — mcp. Это же зафиксировано в /home/user/siamang_cloud/docs/SUBSCRIPTION_TIERS.md:142-171.
- **Правка:** заменить на: «экран Connectors открывается с плана Plus; каждый таргет имеет свой минимальный план: повседневные (Sheets, Excel 365, Supabase, GitHub-зеркало) — Plus; object storage/хранилища (S3, GCS, Azure, BigQuery, Snowflake, свой Postgres, SFTP, REDCap, HTTP, GitLab-зеркало) — Pro; свои MCP-серверы — Corporate».

### [ОШИБКА] «В бете коннекторы — Coming soon и данные не передают»
- **В учебнике:** «During the current beta, connectors are marked Coming soon in the web app and do not transfer data yet. …until connectors go live, use Database → Export…» (и повтор в Summary и в FAQ гл. 24).
- **На самом деле:** живых (реально передающих данные) таргетов — двенадцать: s3, gcs, azure, sftp, sheets, excel365, supabase, database, bigquery, snowflake, redcap, http — /home/user/siamang_cloud/worker/app/connectors/adapters.py:1-8 (docstring), :986-991 (`live_targets()`), /home/user/siamang_cloud/api/app/routers/connectors.py:35-48 (TRANSFER_TARGETS). «Coming soon» отвечают только airtable, dropbox и mcp (409). Импорт живой для database и supabase (connectors.py:50 IMPORT_TARGETS). Экран Connectors группирует каталог на available / upgrade / soon (/home/user/siamang_cloud/web/components/screens/connectors.tsx:14-15, 228-233), там же есть мастер «Add connector» (skeleton.py:31-33).
- **Правка:** убрать блок «Coming soon» целиком; описать живой набор из 12 экспорт-таргетов + 2 импорт-таргетов, а «coming soon» оставить только для airtable/dropbox/mcp. Полезно добавить ограничения живых трансферов: замена содержимого при каждом запуске, все колонки как текст, кап 100 000 строк (Sheets 50 000, Excel 365 10 000), только ручной запуск (docs/SUBSCRIPTION_TIERS.md:163-165; adapters.py:34-36).

## Глава 23, раздел 23.1.1

### [ОШИБКА] Каталог таргетов неполон
- **В учебнике:** таблица каталога перечисляет 7 таргетов: s3, gcs, azure, database, sheets, bigquery, snowflake.
- **На самом деле:** зарегистрировано 15 адаптеров: s3, gcs, azure, database, sheets, excel365, supabase, bigquery, snowflake, airtable, dropbox, sftp, redcap, http, mcp — /home/user/siamang_cloud/worker/app/connectors/adapters.py:966-983. Отсутствуют в учебнике: excel365 (Excel на OneDrive/SharePoint), supabase (экспорт+импорт), sftp, redcap, http (кастомный endpoint), airtable/dropbox (soon), mcp (Corporate, soon). Кроме того, github/gitlab — тарифные ключи git-зеркал (limits.py:103-106).
- **Правка:** дополнить таблицу каталога до фактического списка (или явно оговорить, что приведена выборка, и назвать остальные).

### [ОШИБКА] database-коннектор: «Postgres / MySQL» и «dsn можно положить в config вместо секрета»
- **В учебнике:** «Your own SQL database (Postgres / MySQL)» и в таблице ключей: «database | — (a dsn may go in config instead of the secret) | DSN».
- **На самом деле:** только Postgres («MySQL support is tracked separately») — /home/user/siamang_cloud/worker/app/connectors/adapters.py:266-269; секрет обязателен и это и есть DSN: `if not spec.secret_key: raise ValueError("database: a `secret` (postgres:// DSN) is required")` (adapters.py:274-281). Возможности указать dsn в config нет; опциональные config-ключи — `table` и `schema` (adapters.py:276-291).
- **Правка:** «Your own Postgres (BYO database)»; в таблице: обязательных config-ключей нет (опционально table, schema), секрет — postgres:// DSN, обязателен.

### [ОШИБКА] snowflake: пропущен обязательный ключ warehouse
- **В учебнике:** «snowflake | database, schema, table | Connection parameters».
- **На самом деле:** обязательны `database, schema, table, warehouse` — /home/user/siamang_cloud/worker/app/connectors/adapters.py:659-663 (`_require(spec.config, ("database", "schema", "table", "warehouse"), …)`); секрет — JSON {account, user, private_key} (key-pair, без паролей), adapters.py:662-663, :704-712.
- **Правка:** добавить warehouse в обязательные ключи; секрет описать как JSON account/user/private_key (key-pair).

### [НЕТОЧНОСТЬ] s3: секрет «Optional (for private buckets)»
- **В учебнике:** «s3 | bucket, key | Optional (for private buckets)».
- **На самом деле:** при реальном трансфере секрет обязателен всегда — это JSON {access_key, secret_key, опц. endpoint, region}; без него `_parse_secret_json` падает: /home/user/siamang_cloud/worker/app/connectors/adapters.py:145-157. Секрет опционален только у таргета http (worker/app/tasks/run_connector.py:86-87 «The secret is required by most adapters; http export makes it optional»).
- **Правка:** для s3 указать секрет обязательным (JSON access_key/secret_key, для R2/MinIO — endpoint).

### [НЕТОЧНОСТЬ] Пример `key: digital-life/responses.parquet` — коннектор выгружает CSV
- **В учебнике:** пример s3-коннектора с `key: digital-life/responses.parquet`.
- **На самом деле:** все живые экспорт-адаптеры сериализуют таблицу в CSV (`rows_to_csv_bytes`, ContentType text/csv) — adapters.py:108-115, :148-157; формат выгрузки не настраивается (кроме http: csv|json, adapters.py:943-950). Файл с расширением .parquet на деле будет CSV.
- **Правка:** в примере использовать `key: digital-life/responses.csv` и упомянуть, что коннекторы выгружают CSV.

### [ОШИБКА] «Валидация коммита сообщит о пропущенном config-ключе»
- **В учебнике (Try it yourself):** «Validation runs automatically on the commit and will tell you if a required config key is missing — fix it, commit again, and watch the badge turn green.» (и в 23.1.1: «If a required key is missing … the configuration is reported as invalid so you can fix it before it runs».)
- **На самом деле:** валидация коммита проверяет у коннекторов только соответствие тарифу таргета («connector 'X' (target) needs the 'pro' plan to run») — /home/user/siamang_cloud/worker/app/tasks/validate.py:56-71; обязательные config-ключи проверяются `adapter.validate(spec)` лишь при запуске коннектора — /home/user/siamang_cloud/worker/app/tasks/run_connector.py:76. На коммите пропавший `bucket` бейдж не подсветит.
- **Правка:** переписать: на коммите ловится «таргет выше вашего плана»; отсутствие обязательного config-ключа обнаруживается при запуске коннектора (запуск падает с понятным сообщением «s3: missing config: …»). Try-it переориентировать соответственно.

### [НЕТОЧНОСТЬ] Git-зеркала: «то же тарифное право» и «GitHub или GitLab»
- **В учебнике:** «The same plan entitlement also covers Git mirrors (syncing the repository with GitHub or GitLab)…»
- **На самом деле:** зеркала тарифицируются по-провайдерно: GitHub — с Plus; GitLab и self-hosted remotes — с Pro — /home/user/siamang_cloud/api/app/services/limits.py:106-127 (github: plus, gitlab: pro; «"custom" self-hosted remotes ride the gitlab tier»), docs/SUBSCRIPTION_TIERS.md:50, :167-168.
- **Правка:** «GitHub-зеркало доступно с Plus; GitLab и self-hosted — с Pro; управляются в Repository → Remotes».

## Глава 23, раздел 23.3.1

### [НЕТОЧНОСТЬ] «Enabled — включить/выключить endpoint не удаляя»
- **В учебнике:** «Enabled — turn the endpoint on or off without deleting it.»
- **На самом деле:** поле `enabled` существует в модели и учитывается воркером (/home/user/siamang_cloud/worker/app/notify.py:85 — рассылка только по enabled), но у API есть лишь list / create / delete (/home/user/siamang_cloud/api/app/routers/orgs.py:422-524 — PATCH/toggle-эндпоинта нет), а в UI — только Add и Delete (/home/user/siamang_cloud/web/components/screens/org-settings.tsx:381-394). Выключить endpoint без удаления пользователь не может.
- **Правка:** убрать пункт Enabled из списка настроек (или заменить на «endpoint можно удалить; журнал доставок сохраняется»).

### [НЕ ПОДТВЕРЖДЕНО] «Slack incoming-webhook URL работает напрямую, без glue-кода»
- **В учебнике:** «A Slack incoming-webhook URL works directly, so you can get run and deploy notifications in a Slack channel with no extra glue code.»
- **На самом деле:** это утверждают комментарии кода и docs (/home/user/siamang_cloud/worker/app/notify.py:1, docs/SUBSCRIPTION_TIERS.md:134), но фактический payload — `{"event": …, "run_id": …}` без поля `text` (notify.py:124), а Slack incoming webhooks требуют `text`/`blocks` и отвечают 400 на прочее. Работоспособность «напрямую» кодом не подтверждается.
- **Правка:** либо смягчить («Slack-совместимые приёмники»/«через промежуточный обработчик»), либо оставить как в официальной документации, но пометить редакции, что claim стоит проверить на живом стенде.

### Примечание (не ошибка): «delivery log per endpoint» — журнал ведётся по-доставочно с привязкой к endpoint (webhook_deliveries.endpoint_id), но в UI показывается единым списком по организации с колонкой Endpoint (org-settings.tsx:397-427). Допустимо.

---

## Глава 24, раздел 24.1.1

### [ОШИБКА] Строка «Connectors & Git mirrors — Pro, Corporate» в таблицах планов, «Choosing a plan» и FAQ
- **В учебнике:** таблица планов: «Connectors & Git mirrors | — | — | Yes | Yes»; таблица premium-фич: «Connectors & Git mirrors | Pro, Corporate»; «Plus fits small teams … unlimited responses, plus webhooks and schedules»; «Pro is for teams needing scale and integrations: … plus connectors, Git mirrors, and SSO»; FAQ: «connectors, Git mirrors, and SSO need Pro»; Chapter Summary: «Pro adds connectors, Git mirrors, and SSO».
- **На самом деле:** Plus уже включает `FEATURE_CONNECTORS` и повседневные таргеты (Sheets, Excel 365, Supabase) + GitHub-зеркала; Pro добавляет полный каталог (S3/GCS/Azure/BigQuery/Snowflake/BYO Postgres/SFTP/REDCap/HTTP), GitLab/self-hosted зеркала и SSO; Corporate — mcp — /home/user/siamang_cloud/api/app/services/limits.py:51-57, :106-127; /home/user/siamang_cloud/docs/SUBSCRIPTION_TIERS.md:40-53, :98-122, :142-171.
- **Правка:** в таблице планов дать коннекторам две строки или сноску: Plus — «повседневный набор» (Sheets, Excel 365, Supabase; GitHub-зеркало), Pro — «все таргеты» + GitLab/self-hosted, Corporate — + MCP; поправить «Choosing a plan», premium-таблицу, FAQ и Summary.

### [ОШИБКА] «По окончании триала workspace становится read-only»
- **В учебнике:** «When the trial ends, the workspace becomes read-only: your data is preserved and exportable until paid plans (with Stripe) arrive at the official release.» (и повтор в FAQ и Chapter Summary).
- **На самом деле:** по окончании триала организация понижается до Free и продолжает работать в пределах Free-капов: `effective_plan()` схлопывает истёкший план в "free" (/home/user/siamang_cloud/api/app/services/invites.py:35-39), воркер `downgrade_expired_orgs` персистит понижение (/home/user/siamang_cloud/worker/app/tasks/cleanup.py:1-8, :32-38 «sweep lapsed plan clocks down to the free tier»). Read-only («frozen») — только явное действие оператора: invites.py:63-70 («A lapsed trial … is NOT frozen»), /home/user/siamang_cloud/api/app/deps.py:122-131.
- **Правка:** «когда триал заканчивается, организация переводится на Free: данные и проекты сохраняются, работа продолжается в пределах лимитов Free (2 проекта, 2 участника, 500 ответов), сверх-лимитные действия блокируются с предложением апгрейда».

### [НЕТОЧНОСТЬ] «Переключение планов выключено, ничего не списывается, Stripe появится в релизе»
- **В учебнике:** «Plan switching is turned off — other plans show “Available at the official release” — and nothing is ever charged.» / FAQ: «Can I change plans during the open beta? Not yet.»
- **На самом деле:** это верно только для беты БЕЗ платёжного провайдера: кнопки «Coming soon / Available at the official release» показываются при `IS_BETA && billing.provider !== "stripe"` (/home/user/siamang_cloud/web/components/screens/org-settings.tsx:338-345); Stripe-биллинг при этом полностью реализован (checkout, портал, вебхуки, promo pro_year) — /home/user/siamang_cloud/api/app/routers/billing.py, api/app/routers/webhooks_stripe.py, api/app/services/billing.py:19-35; docs/SUBSCRIPTION_TIERS.md:27-31 описывает самообслуживание Free/Plus/Pro как рабочее.
- **Правка:** сформулировать условно: «пока платёжный провайдер не подключён, остальные планы показываются как “Available at the official release” и ничего не списывается; после подключения Stripe апгрейды покупаются самообслуживанием (Corporate — через sales)».

## Глава 24, раздел 24.2.1

### [ОШИБКА] «Полный аннотированный конфиг примера-исследования» не совпадает с реальным siamang.yaml примера
- **В учебнике:** пример объявляет три analysis-задачи `cleaning` / `weights` (scripts/weights.py, «Rake to census margins…») / `tables` (report: outputs/key_tables.md).
- **На самом деле:** siamang.yaml примера-проекта объявляет две задачи: `cleaning` и `tables` (report: outputs/tables.md); задачи weights нет — /home/user/siamang_cloud/api/app/services/example_project.py:36-93. Кроме того, реальный файл содержит секции `database:` (backend: platform, schema: auto), `storage:` (outputs: outputs/, commit_outputs: false) и закомментированный блок `insights:` — example_project.py:82-105, skeleton.py:49-73 — которых нет ни в примере учебника, ни в списке ключей раздела.
- **Правка:** привести yaml к фактическому (две задачи; report: outputs/tables.md) и добавить в разбор ключей `insights:` (виджеты Dashboard, см. правку 22.3.1), а `database:`/`storage:` хотя бы упомянуть (в текущем коде платформа их не читает — служат заготовкой).

### [НЕТОЧНОСТЬ] runtime: «python задаёт версию интерпретатора», «добавляйте любые пакеты, которые импортирует ваш анализ»
- **В учебнике:** «python sets the interpreter version; packages lists what is available to your scripts — … you add any others your analysis imports.»
- **На самом деле:** (1) пакеты ограничены кураторским allowlist — валидация коммита отклоняет прочие (/home/user/siamang_cloud/worker/app/tasks/validate.py:47-52, worker/app/allowed_packages.txt); (2) `runtime.python` декларативен: все скрипты выполняются в едином sandbox-образе (`SANDBOX_IMAGE`, /home/user/siamang_cloud/worker/app/config.py:19), выбор версии не реализован — в Settings → Runtime версия показана неактивной кнопкой (/home/user/siamang_cloud/web/components/screens/settings.tsx:107, disabled).
- **Правка:** оговорить allowlist (список кураторских пакетов; новый пакет — по запросу) и что версия Python сейчас фиксирована образом песочницы (3.11), ключ python — информационный.

### [НЕТОЧНОСТЬ] reports: «dir (папка) … formats (md и html)»
- **В учебнике:** «reports — controls the combined document that Run all produces: dir (the folder), combined (the document’s path…), and formats (md and html…)».
- **На самом деле:** платформа читает только `reports.combined` (default reports/report.md) — /home/user/siamang_cloud/worker/app/tasks/run_all.py:91-93, worker/app/deploy_util.py:233; ключи `dir` и `formats` присутствуют в шаблонных yaml, но нигде не читаются.
- **Правка:** описывать действующим только `combined`; `dir`/`formats` пометить как зарезервированные/декларативные.

## Глава 24, раздел 24.3.1

### [ОШИБКА] FAQ «нельзя пригласить»: «the person already has a Siamang Cloud account»
- **В учебнике:** «You cannot invite someone — Check: the organization is cooperative; you are owner or admin; the person already has a Siamang Cloud account; your plan has member room.»
- **На самом деле:** приглашение по e-mail БЕЗ существующего аккаунта поддерживается: если пользователь не найден, создаётся pending-инвайт и письмо со ссылкой — /home/user/siamang_cloud/api/app/routers/orgs.py:259-262 («No account yet: create a pending invitation and email the link»), :302-330 (`_create_invite`; pending-инвайты считаются в кап участников).
- **Правка:** убрать пункт про существующий аккаунт; вместо него: «pending-инвайты тоже занимают место в лимите участников плана; инвайт действует ограниченный срок».

### [ОШИБКА] FAQ/Troubleshooting «Connectors are not moving data — Coming soon»
- **В учебнике:** «Connectors are marked Coming soon and do not transfer data yet; use Database → Export in the meantime.»
- **На самом деле:** см. находку по 23.1 — 12 таргетов передают данные; «coming soon» только airtable/dropbox/mcp (/home/user/siamang_cloud/worker/app/connectors/adapters.py:1-8, api/app/routers/connectors.py:35-50).
- **Правка:** заменить фикс на реальные причины: не задан project secret («this connector needs a `secret` (set it under Project → Secrets)» — worker/app/tasks/run_connector.py:50-58), таргет выше плана (402 с именем нужного плана), неверные config-ключи (ошибка при запуске), либо выбран airtable/dropbox/mcp (эти действительно «soon», 409).

---

## Проверено и корректно

- 22.1: деплой в именованные окружения из siamang.yaml; пример — pilot (max_responses: 50) и main (1200) (api/app/services/example_project.py:47-48); yaml-фрагмент environments совпадает дословно.
- 22.1: Preview собирает staging-версию, не принимает ответы и не пишет данные (worker/app/tasks/deploy.py: preview — «never wired to ingest (no responses are accepted)»); кнопка Preview справа сверху (deployments.tsx:217).
- 22.1: деплой требует роли member+ (require_role("developer"), ранг developer == member — api/app/deps.py:24-33, api/app/routers/deployments.py:72).
- 22.1: четыре статуса карточки Live/Building/Failed/Stopped (web/components/screens/deployments.tsx:10 DEP_LABEL); Stop сохраняет данные, Redeploy доступен для stopped/failed (deployments.tsx:166-167).
- 22.1: карточка-монитор: прогресс ответов против капа, quota-ячейки, codebook (deployments.tsx:45-88; api/app/routers/monitoring.py:74-83).
- 22.1: эффективный лимит ответов = min(кап плана, max_responses окружения); Free — 500/проект (api/app/services/limits.py:44-50, :171-176 response_cap).
- 22.2: Database — список таблиц слева (responses + таблицы скриптов), вкладки Data/Schema, сортировка кликом по колонке, фильтр строк, пагинация (database.tsx:11-16, 63-95); схема: name/type/nullable (+default) (sdk db.schema и database_service).
- 22.2: пять форматов экспорта в UI — CSV, Excel(.xlsx), SPSS(.sav), Parquet, SQLite (database.tsx:139; console commands.ts:180) — состав и назначение (кроме меток .sav, см. находку).
- 22.2: удаление одиночного ответа с подтверждением, GDPR, запись в аудит-лог (database.tsx:113-115; api/app/routers/database.py:87-105, action "response.delete").
- 22.2: Files — две группы «Repository outputs» и «Assets (uploads & exports)», Upload/Download/Delete, кап 50 MB на файл (files.tsx:33-56; api/app/routers/files.py:27 MAX_UPLOAD_BYTES).
- 22.3: analysis-задачи объявляются в siamang.yaml как type: analysis с entry/description/report/outputs (siamang_cloud_engine/project_config.py:28-73); на экране Analysis появляются только объявленные задачи.
- 22.3: Run / Run all; Run all выполняет шаги в порядке объявления и останавливается на первом упавшем (worker/app/tasks/run_all.py:58, :326-331); статусы запусков completed/failed.
- 22.3: таблица «куда попадает вывод»: Report→Repository+Outputs, db.write_table→Database, файлы outputs/→Files+Outputs (скачивание), print→Logs — подтверждено (run-карточка, files.py, run_script.py).
- 22.3: отчёты Markdown/HTML, PDF отложен/«planned» (report.py:171-183 NotImplementedError для .pdf; api/app/services/report_artifacts.py:12 «PDF rendering is deferred»); MD/HTML-кнопки скачивания у отчёта (report-doc.tsx:116-117); Run all собирает общий документ с TOC, секции озаглавлены description, путь по умолчанию reports/report.md (run_all.py:91-93, :128-171; Report.combine с toc=True).
- 22.3: расписания для скрипта/run-all доступны с Plus (limits.py FEATURE_SCHEDULES; schedules.py require_feature) и управляются из Console.
- 22.3.2 SDK: пакет siamang_cloud, преинсталлирован в песочнице (worker/app/packages.py:19 _PLATFORM); импорт-поверхность `from siamang_cloud import db, analysis, respondents, Report` (sdk/siamang_cloud/__init__.py) — проверено установкой и исполнением.
- 22.3.2 db: list_tables(), schema(), table().to_pandas() (responses разворачивается по-колоночно из JSONB data), write_table(name, df, if_exists="fail"|"replace"|"append"), as_survey_data(), export_table() с форматами csv/parquet/xlsx/sav/sqlite по расширению; свободного SQL нет — всё соответствует sdk/siamang_cloud/db.py.
- 22.3.2 analysis: frequencies (value/count/percent), crosstab (normalize="index"/"columns"/"all", проценты), chi2 (chi2, dof, p, cramers_v, n), cell_weights, rake_weights (IPF); targets — доли или счётчики, нормализуются; веса масштабируются к среднему 1.0 — sdk/siamang_cloud/analysis.py.
- 22.3.2 respondents: dedup_responses (по respondent_id, keep последнюю по submitted_at), completion_time (предпочитает duration_s, иначе timestamps), partial_flag (True при пустом обязательном поле) — sdk/siamang_cloud/respondents.py.
- 22.3.2 Report: chainable heading/markdown/note/value/divider/add(DataFrame|таблица|график, caption=)/image; save(.md|.html) — siamang_cloud_engine/report.py. Worked example учебника исполняется без ошибок (проверено на синтетических данных).
- 23.1: структура type: connector задачи — target, direction (out/in), table, secret (имя проектного секрета), вложенный config: (worker/app/connectors/base.py ConnectorSpec; api/app/routers/connectors.py:_connectors_from_yaml); настройки только внутри config:.
- 23.1: секреты — Project Settings → Secrets, write-only (list возвращает только имена), шифруются Fernet (api/app/routers/secrets.py); предупреждение «не коммитить креды» корректно.
- 23.1.1: обязательные config-ключи подтверждены для s3 (bucket, key), gcs (bucket, key + service-account JSON), azure (container, path + SAS-секрет), sheets (spreadsheet_id + service-account JSON), bigquery (dataset, table + service-account JSON) — adapters.py; примеры деклараций bigquery/sheets синтаксически корректны.
- 23.2: schedule запускает run_script (одна задача по имени) или run_all (api/app/routers/schedules.py:60-73); фича с Plus.
- 23.2.1: команды консоли — schedules, schedule add --cron "<expr>" --all, schedule add --cron "<expr>" --script <name>, schedule rm <id> (web/lib/console/commands.ts:430-495); консоль открывается кнопкой в топ-баре или бэктиком (console.tsx:5, app.tsx:273).
- 23.2.1: cron — стандартные 5 полей, валидируется croniter, исполняется в UTC (schedules.py:58; worker/app/tasks/scheduler.py:74 datetime.now(UTC)); новый schedule не «догоняет» пропущенные запуски (worker/app/scheduler_core.py:14 base = now − 1 мин); примеры cron-выражений арифметически верны (включая пример UTC+2 → 0 22 * * *); запуски по расписанию попадают в общий Run history.
- 23.3: четыре события — deploy.live, deploy.failed, run.completed, run.failed (worker/app/tasks/deploy.py:155-273, run_script.py:236-250, run_all.py:276-289); deploy.live несёт url, run.completed — run_id/script/status.
- 23.3: настройка per-organization в Organization settings → Integrations (org-settings.tsx:355+); пустой список events = все события (notify.py:89-92); журнал доставок с статусом/попытками; авто-ретраи с экспоненциальным бэкоффом до 5 попыток (notify.py:35, :77-79).
- 23.3.1: заголовки Content-Type: application/json, X-Siamang-Event (имя события), X-Siamang-Signature: sha256=<hex> только при заданном секрете; подпись — HMAC-SHA256 от сырого тела (notify.py:51-52, :99-105); код проверки подписи в учебнике в точности повторяет notify.sign + hmac.compare_digest — корректен (проверен исполнением); предупреждение про сырые байты тела — корректно.
- 24.1: четыре плана Free $0 / Plus $25 / Pro $200 / Corporate custom; self-serve для трёх, Corporate — contact sales (api/app/services/billing.py:19-27, :104-106); подписка per-organization, меняет только owner (billing.py checkout: 403 не-owner); планы и роли независимы.
- 24.1.1: лимиты Free 2/2/500, Plus 10/15/∞, Pro и Corporate ∞ (limits.py:43-80); Webhooks и Schedules с Plus; SSO с Pro; Self-hosted — Corporate; 402 + указание на Billing при достижении капа (limits.py, SUBSCRIPTION_TIERS.md:186-202).
- 24.1.1: 30-дневный Pro-триал для нового workspace в открытой бете, счётчик дней на Billing и в топ-баре (web/lib/auth.ts:193; app.tsx:266-268; org-settings.tsx:262-268).
- 24.2: siamang.yaml в корне репозитория; name/org; tasks — mapping (не список), имя задачи = ключ, используется как заголовок секции отчёта и script_name расписания; type: survey — entry (модуль с module-level `survey` и опциональным `options` с квотами — sandbox/_entry.py:27-50) + environments {name, max_responses}; type: analysis — entry/description/report/outputs, .md-outputs подхватываются Run all (run_all.py:104-127); version: "1.0" присутствует в реальных конфигах; Settings → Runtime читает python/packages из siamang.yaml (api/app/routers/analysis.py:189-207).
- 24.3.1: персональный токен — Profile → API keys; SSH-ключи — Profile → SSH keys; клонирование HTTPS/SSH из Repository → Remotes (profile.tsx:14; modals.tsx:622-626).
- 24.3.1: «Forgot password?» на экране входа (web/app/(auth)/login/page.tsx); вход через GitHub существует (OAuth-провайдеры google/github, web/lib/auth.ts:27-37).
- 24.3.1: Terms/Privacy — Profile → Support со ссылками на docs/cloud/ в open-source репозитории (profile.tsx:288-291; файлы /home/user/siamang/docs/cloud/{terms-of-use,privacy-policy}.md существуют).
- 24.3.1: personal/cooperative, конверсия в обе стороны (cooperative→personal оставляет только owner) (api/app/routers/orgs.py:124-145); приглашают owner/admin; billing — только owner.
- 24.3.1: Empty/Template/Example — Example с сэмпл-данными; Template — минимальный опрос + два стартовых скрипта (cleaning.py, final_tables.py); Empty — голый каркас (api/app/routers/projects.py:186-194; skeleton.py:146-176, :247).
- 24.3.1 Troubleshooting: параллельный билд того же окружения блокируется 409 («a deployment for this environment is already in progress», deployments.py:99-101); упавший запуск — читать Logs, guard tables-шага советует запустить cleaning или Run all (example_project.py:451-455); зависимость шагов и совет Run all корректны.
- 24.3.1 Privacy/Terms in brief: controller/processor-разделение, владение контентом, open beta «as is» без SLA, без рекламных трекеров, 16+, контакт info@siamang-team.org и GitHub issues, оператор Siamang Labs LLC — всё подтверждено текстами /home/user/siamang/docs/cloud/privacy-policy.md и terms-of-use.md.

---

# Ревью приложений A–C (сверка с движком siamang 0.5.0, editable-установка; все CLI-команды реально запускались)

## Приложение A, раздел A.1.3 (siamang deploy)

### [ОШИБКА] «--config: ~/.siamang.toml (already loaded)» — CLI НЕ загружает ~/.siamang.toml автоматически
- **В учебнике:** «--config | ~/.siamang.toml (already loaded) | Override the config path.» и «Resolution order: load --config if given (otherwise use the already-active config)»; пример: «$ siamang deploy my_survey.py --profile production → Deployed: …»
- **На самом деле:** в установленной версии 0.5.0 ни одна точка входа CLI не вызывает `load()` — ни `siamang/cli/entry.py`, ни `siamang/__main__.py`. `siamang/cli/deploy.py:20` начинает с `cfg = current()`, а `current()` (`siamang/config/loader.py:70-73`) возвращает ПУСТОЙ `Config`, если `load()` никто не вызывал. `load()` вызывается только при явном `--config` (`deploy.py:21-22`). Проверено экспериментально: при корректном `~/.siamang.toml` с блоком `[profiles.production]` команда `siamang deploy my_survey.py --profile production` падает с `ConfigError: Profile 'production' is not defined.` (трейсбек, exit 1). Без `--profile` деплой молча идёт в `local`/`local`, игнорируя `[defaults]` из `~/.siamang.toml`. Формулировка «already loaded» унаследована из wiki/CLI-Reference.md, но коду не соответствует.
- **Правка:** в колонке Default для `--config` написать «(не задан — конфиг не читается)» и добавить предупреждение: «В версии 0.5.0 CLI не читает ~/.siamang.toml автоматически; чтобы deploy видел профили и настройки по умолчанию, передавайте путь явно: `siamang deploy my_survey.py --config ~/.siamang.toml --profile production`». Пример вызова дополнить флагом `--config`.

## Приложение A, раздел A.2 (Configuration File)

### [ОШИБКА] Основной пример конфига дан в формате, который установленная версия не читает
- **В учебнике:** основной пример A.2 — `[profile.default]`, `[profile.default.backend_kwargs]`, `[profile.default.frontend_kwargs]`, `[profile.production]` … (по docs/reference/cli.md), с заметкой «Check which format your installed version reads … or simply generate it with siamang init.»
- **На самом деле:** загрузчик читает ровно четыре таблицы `defaults` / `backends` / `frontends` / `profiles` (`siamang/config/loader.py:118-125`, `_config_from_dict`); таблицы `[profile.*]` и `*.backend_kwargs` молча игнорируются (не попадают ни в одно поле `Config`). Формат из wiki/Configuration.md (он же в Appendix B) проверен экспериментально и работает: `load()` корректно разбирает `[defaults]` + `[profiles.production]`, `with_profile("production")` даёт `default_backend() == "supabase"`. Кроме того, `siamang init` пишет именно формат `[defaults]` (проверено запуском: файл содержит `[defaults]\nbackend = "local"\nfrontend = "local"`), то есть совет «сгенерируйте через siamang init» противоречит приведённому в A.2 примеру. Формат docs/reference/cli.md — устаревшая документация.
- **Правка:** сделать основным примером A.2 рабочий формат `[defaults]` / `[backends.<name>]` / `[frontends.<name>]` / `[profiles.<name>]` (как в Appendix B), а заметку переформулировать: «установленная версия 0.5.0 читает только этот формат (siamang/config/loader.py); формат `[profile.<name>]` из docs/reference/cli.md — устаревший и игнорируется загрузчиком».

### [НЕТОЧНОСТЬ] «Environment variables override backend kwargs» — про VERCEL_TOKEN это неверно
- **В учебнике:** таблица под заголовком «Environment variables override backend kwargs» включает строку «VERCEL_TOKEN | Forwarded to VercelFrontend.token.»
- **На самом деле:** `VERCEL_TOKEN` не проходит через загрузчик конфига и ничего не «переопределяет»: адаптер читает его сам и только когда kwargs `token` пуст — `self.token = self.token or os.environ.get("VERCEL_TOKEN", "")` (`siamang/deploy/frontends/vercel.py:79`). То есть это fallback, а не override (значение из конфига выигрывает у переменной). Приложение B описывает это корректно («Direct adapter reads … used when kwargs are blank»). Переопределяют же файл только префиксы `SIAMANG_*`/`SURVLIB_*` (`siamang/config/loader.py:128-160`), причём для frontend-ов существуют и `SIAMANG_VERCEL_*`/`SIAMANG_NETLIFY_*`, отсутствующие в таблице A (в B они есть).
- **Правка:** вынести `VERCEL_TOKEN` из-под заголовка «override» с пометкой «читается адаптером напрямую, только если token не задан в конфиге» либо дать ссылку на точную таблицу в B.1.1.

## Приложение A, раздел A.1.1 (siamang validate)

### [НЕТОЧНОСТЬ] Заметка о расхождении exit-кодов разрешима: установленная версия следует таблице wiki, а код 1 на практике недостижим
- **В учебнике:** «The two sources phrase the exit-code semantics differently. … If you rely on exit codes in CI, test against your installed version.»
- **На самом деле:** проверка выполнена. Код (`siamang/cli/validate.py:41-46`) возвращает 1 при любом lint-предупреждении с severity `error` независимо от `--strict` — то есть формально верна таблица wiki (и учебника), а вариант docs/reference/cli.md («only when --strict») неверен. Однако фактически exit 1 в 0.5.0 недостижим: все error-severity находки генерируются только на уровне strict (`siamang/core/questionnaire.py:298` — `severity="error" if level == "strict"`, и `:331` — `_strict_question_warnings` вызывается только при `level == "strict"`), а при `--strict` те же находки сначала роняют `validate(strict=True)` через `ValueError` (`questionnaire.py:99-104`) → exit 2. Экспериментально: валидный файл → «OK — no warnings.», exit 0; EMPTY_PAGE без --strict → warning, exit 0; с --strict → «validation error: Strict questionnaire validation failed: EMPTY_PAGE», exit 2; неизвестная переменная в show_if → «validation error: Page 'demographics' show_if references unknown variables: regon», exit 2 (все строки вывода из учебника совпали дословно). Отсутствующий атрибут → необработанный AttributeError с трейсбеком, exit 1 (интерпретаторный, не «lint»).
- **Правка:** заменить заметку на утверждение: «Установленная версия 0.5.0 реализует таблицу выше (exit 1 при error-severity независимо от --strict); формулировка docs/reference/cli.md устарела. На практике же ошибочные lint-находки появляются только в strict-режиме и приводят к exit 2 через validate(), так что реально наблюдаются коды 0 и 2.» То же уточнение стоит учесть в C.2.1 («1 = lint errors»).

### [НЕТОЧНОСТЬ] Не упомянута проверка module-level `options` (квоты)
- **В учебнике:** «It runs survey.validate(strict=...) and then survey.lint(), printing each finding…»
- **На самом деле:** между validate() и lint() команда дополнительно вызывает `validate_options(survey, options)` для module-level словаря `options` (квоты и пр.) — `siamang/cli/validate.py:20-27`; ошибка там тоже даёт «validation error: …» и exit 2. Для справочного приложения по CLI это заметное упущение (квоты валидируются ТОЛЬКО здесь: «nothing else ever checks them», комментарий в коде).
- **Правка:** добавить фразу: «Если модуль экспортирует словарь `options` (например, с `quota=[Quota(...)]`), validate также проверяет его через validate_options(); ошибки дают exit 2».

## Приложение A, раздел A.1.2 (siamang preview)

### [НЕТОЧНОСТЬ] Пример вывода preview не совпадает с реальным: URL 0.0.0.0 и dashboard: sqlite:///…
- **В учебнике:** «The survey is reachable at http://127.0.0.1:<port>»; пример: «Preview ready at http://127.0.0.1:8000 / survey_id: 42a1c0e9 / dashboard: None / [react] sucrase + esbuild minify available — fast path».
- **На самом деле:** реальный запуск `siamang preview my_survey.py --port 8123` печатает: «Preview ready at http://0.0.0.0:8123 / survey_id: 914ec3c70240 / dashboard: sqlite:///survey.db / [react] sucrase + esbuild minify available — fast path / Press Ctrl+C to stop.» Причины: `LocalFrontend.host = "0.0.0.0"` и URL формируется как `http://{self.host}:{self.port}` (`siamang/deploy/frontends/local.py:218, 186`); `LocalBackend.dashboard_url = f"sqlite:///{path}"` (`siamang/deploy/backends/local.py:68`) — никогда не None; survey_id — 12 hex-символов (`uuid.uuid4().hex[:12]`, `local.py:77`), а не 8. Сервер слушает все интерфейсы, поэтому утверждение «reachable at http://127.0.0.1:<port>» функционально верно — расходится именно печатаемая строка. Пример скопирован из wiki/CLI-Reference.md, которая здесь сама расходится с кодом.
- **Правка:** привести пример к реальному выводу (`http://0.0.0.0:8000`, `dashboard: sqlite:///survey.db`, 12-значный survey_id) или добавить оговорку, что сервер печатает адрес привязки 0.0.0.0, а открывать нужно http://127.0.0.1:<port>.

## Приложение A, раздел A.1.3 (пример вывода deploy)

### [НЕТОЧНОСТЬ] Формат dashboard-URL Supabase в примере не соответствует коду
- **В учебнике:** «dashboard: https://app.supabase.com/project/abcdef»
- **На самом деле:** формат строк вывода deploy подтверждён реальным запуском (`Deployed: … / survey_id: … / backend: … / frontend: … / dashboard: …`, причём dashboard печатается только если непуст — `siamang/cli/deploy.py:47-52`), но Supabase-бэкенд формирует dashboard как `f"{self.url.rstrip('/')}/project/_/editor"` (`siamang/deploy/backends/supabase.py:360`), т.е. «https://abcdef.supabase.co/project/_/editor», а не «https://app.supabase.com/project/abcdef».
- **Правка:** в примере заменить строку dashboard на «https://abcdef.supabase.co/project/_/editor» (или убрать конкретный URL).

## Приложение B, раздел B.1.1 (module functions / env overrides)

### [НЕТОЧНОСТЬ] Env-оверлеи применяются только при существующем файле конфига
- **В учебнике:** «load(path=…) — Read and parse the file, apply env overrides, set it as the active config. A missing file yields an empty Config (no error).» и далее «When load() parses the file, it overlays environment-variable values…»
- **На самом деле:** при отсутствующем файле `load()` возвращает пустой Config РАНЬШЕ применения оверлеев (`siamang/config/loader.py:80-85` — ранний `return` до `_apply_env_overrides`), так что переменные `SIAMANG_*`/`SURVLIB_*` через загрузчик в этом случае не попадают в конфиг вовсе. Для справочника это стоит сказать явно, иначе совет «env-переменные вместо файла — идеально для CI» вводит в заблуждение применительно к `SIAMANG_*` (работают без файла только «прямые» чтения адаптеров: VERCEL_TOKEN, NETLIFY_AUTH_TOKEN, SIAMANG_GSHEETS_*, SIAMANG_SUPABASE_* — их адаптеры читают из окружения сами). Сам механизм оверлеев проверен экспериментально: при существующем файле `SIAMANG_SUPABASE_URL` побеждает значение из файла, `SURVLIB_NETLIFY_TOKEN` создаёт `frontends.netlify["token"]` — всё как описано.
- **Правка:** добавить одно предложение: «Оверлеи применяются только когда файл существует; при отсутствующем файле load() возвращает пустой Config без применения переменных окружения (адаптеры при этом всё равно читают свои переменные напрямую)».

## Приложение C, раздел C.1.1 (глоссарий)

### [НЕТОЧНОСТЬ] Question — не абстрактный класс, инстанцирование кодом не запрещено
- **В учебнике:** «Question — Abstract base class of the seven question types; … Never instantiated directly.»
- **На самом деле:** `Question` — обычный dataclass без ABC и без запрета на инстанцирование (`siamang/core/question.py:14`); `Question("t?", var=v)` успешно создаётся (проверено). Утверждение «cannot be instantiated directly» есть в docs/reference/core.md:187, но кодом не подтверждается. Число типов верно: SingleChoice, MultiChoice, LikertScale, NumericInput, OpenText, Matrix, Ranking — ровно семь.
- **Правка:** заменить «Abstract base class … Never instantiated directly» на «Базовый класс семи типов вопросов; напрямую не используется (инстанцируйте подклассы)» — без слов «abstract/never», которые предполагают запрет на уровне кода.

## Проверено и корректно

- A: четыре подкоманды и их справки (`siamang --help`, `validate/preview/deploy/init --help`) — состав флагов, дефолты `--attribute survey`, `--port 8000`, `--db survey.db`, `--path ~/.siamang.toml` совпадают с entry.py; `python -m siamang validate` работает.
- A: текст AttributeError при отсутствующем атрибуте («Either set `survey = sg.Questionnaire(...)` or pass --attribute NAME») — дословно (cli/loader.py:41-44, cli/validate.py:12-15).
- A.1.1: формат вывода находок `[severity] [code] message (location)` и все четыре строки примеров validate воспроизведены дословно реальными запусками.
- A.1.2: FastAPI + uvicorn, LocalBackend + LocalFrontend, диагностическая строка `[react] …` (все три варианта — preview.py:12-42), ответы пишутся в `--db`, Ctrl+C останавливает; пример `LocalBackend(path="survey.db").get_responses(survey_id=...)` соответствует сигнатуре (backends/local.py:59, 155).
- A.1.3: порядок разрешения backend/frontend (`--backend/--frontend` → профиль → local/local) и «local не получает kwargs» — соответствуют cli/deploy.py:26-38; структура вывода Deployed/…/dashboard подтверждена запуском `deploy --config cfg.toml` (local/local).
- A.1.4: оба сценария init запущены; вывод «siamang init — interactive setup / Target: … / Default backend (local/supabase) [local]: …» и «Wrote … (chmod 600 applied).» / «Wrote … (defaults: local/local).» совпадают дословно; права файла -rw------- (0600); секреты — через getpass (url и team_id — открытым вводом, как в примере).
- A.2/B: канонические `SIAMANG_SUPABASE_URL/ANON_KEY/SERVICE_KEY` и legacy `SURVLIB_*` — подтверждены (_ENV_PREFIXES, loader.py:128-143; CHANGELOG.md:35-36).
- B.1.1: четыре таблицы файла, минимальный конфиг = вывод `init --non-interactive`, «профили переопределяют defaults, кредензии общие» — совпадают с кодом и проверены на живом load()/with_profile().
- B.1.1: dataclass `Config` (frozen, slots, пять полей) и все шесть методов с описанной семантикой ошибок ConfigError — точны (loader.py:22-63); use_profile/current/save — как описано; save() создаёт родительские каталоги и ставит 0o600 (loader.py:104-112).
- B.1.1: маппинг «префикс → adapter, остаток имени в lower → ключ kwargs», приоритет env над файлом — проверены экспериментально; таблица префиксов (SUPABASE/GSHEETS/VERCEL/NETLIFY + SURVLIB) полная.
- B.1.1: прямые чтения адаптеров VERCEL_TOKEN (vercel.py:79) и NETLIFY_AUTH_TOKEN (netlify.py:67) — верно; ссылки на MANUAL.md:575-577, README.md:176-177 и :207, CHANGELOG — верны.
- B.1.1: check_permissions — POSIX, биты 0o077, warning с советом chmod 600, возврат True/False (config/secrets.py:13-33) — верно; предупреждение реально наблюдалось на файле 644.
- C.1.1: определения Aggregate root, Backend (local/supabase/gsheets = list_backends()), Frontend (local/vercel/netlify = list_frontends()), BannerTable (tables.banner + export_csv/export_xlsx), Block, Codebook/VariableMap («VariableMap is your codebook», wiki/Variables-and-Measurement.md:251), CrossTable (χ²/Cramér's V), DeployResult (url + collect()), Expression (evaluate + to_surveyjs, компиляция в SurveyJS visibleIf — frontend/compiler/logic.py), FilterRule (Python-only, wiki/Visibility-and-Branching.md:251-253), FreqTable, FrontendBuilder (слой 2, runtime+UIConfig+BackendClientTemplate→SurveyBundle), GroupMeanTable (means(column, by=...)), Kish ESS ((Σw)²/Σw², analysis.py:248-256), LikertScale (points>=2, left/right_label, na_option), Matrix (list[Variable], позиционное сопоставление), Media (kind из расширения URL), MissingValue (code+label+kind; refusal/dont_know в _VALID_MISSING_KINDS), Option (show_if/hide_if + media, choices=), Page (уникальное имя, цели переходов), Questionnaire, Quota (variable/target_value/limit; деплой-время, бэкенд-энфорсмент — wiki/Quotas.md:54-62, quota_counters в LocalBackend), Ranking (drag-and-drop, max_ranked), Report, Script (7 триггеров onInit…onRandomize, sandbox=True), simulate(n=100, seed=42), SurveyBundle (files+manifest; index.html/style.css/env.js), SurveyData (5 аксессоров), SurveySchema (frozen), UIConfig (frozen; палитра/типографика/брендинг/i18n-строки/access code), Variable (4 шкалы) — все соответствуют коду.
- C.1.1 (Cloud): Connector (s3/database/sheets/bigquery/snowflake — подтверждено и в wiki/Cloud-Connectors.md, и в siamang_cloud/worker/app/connectors/adapters.py; задача в siamang.yaml), Organization (personal/cooperative; роли owner/admin/member), Webhook (исходящий POST c JSON; события deploy.live/failed, run.completed/failed — подтверждены в siamang_cloud/worker/app/tasks/deploy.py), siamang.yaml (tasks: survey с environments/max_responses, analysis, connector; runtime) — верно.
- C.2.1: конвенции (module-level `survey`, ~/.siamang.toml, survey.db; имя переменной = колонка данных = id вопроса = токен выражений; проверка соответствия зарегистрированным переменным — questionnaire.py:95-98; «validation runs automatically on every commit» — wiki/Cloud-Repository-and-Editing.md:5) — верно.
- C.2.1: ресурсы — оба имени репозитория действительно встречаются (Siamang-Labs — LICENSE-COMMERCIAL.md, wiki/_Footer.md; hanelias — pyproject.toml:47-49, LICENSE:9); Issues-URL из LICENSE-COMMERCIAL.md; состав docs/ и wiki/, examples/full_pipeline/ существуют; https://app.siamang.org/login — README.md:53.
- C.2.1: лицензия — PolyForm Noncommercial 1.0.0 (LICENSE), перечень некоммерческих пользователей — дословно README.md:295-299; коммерческая лицензия через LICENSE-COMMERCIAL.md и info@siamang-team.org; «до 0.5.0 включительно — MIT» — CHANGELOG.md:12-16.

---
