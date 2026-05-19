# Задача: GUI-инструмент tools.py, объединяющий pick_color, measure, calibrate
Дата: 2026-05-20
Статус: завершено

## План
1. Создать src/tools.py — окно tkinter с тремя кнопками.
2. Кнопки переключают режим, статус и логи выводятся в Text widget.
3. Для pick_color и measure — фоновый поток с keyboard.add_hotkey("f7"), F9 — стоп.
4. Для calibrate — выбор профиля + delay, обратный отсчёт, снимок, сохранение debug-PNG.
5. Передача сообщений из потока в UI через queue + root.after().
6. Smoke-проверка: запуск приложения, окно открывается, кнопки кликаются.

## Прогресс
- (старт) три исходные утилиты разобраны: pick_color.py (F7 проба HSV / F9), measure.py (F7 точка / F9, 2 точки), calibrate.py (CLI screen|file, --profile, --delay).
- Пользователь выбрал GUI на tkinter с кнопками.
- Создан `src/tools.py`: класс `ToolsApp`, три кнопки + Stop, выбор профиля и delay, лог Text.
- Логика всех трёх режимов перенесена 1:1, вывод идёт через очередь сообщений в Text.
- Smoke: `python -c "import tools; ...; r.after(400, r.destroy); r.mainloop()"` → OK.
- `_list_profiles()` находит: cigame, nte_fishing, reaction_test.

## Решения и находки
- keyboard.unhook_all_hotkeys() в `_run_worker.finally` — гарантирует очистку даже при исключении.
- mss.MSS() создаётся внутри потока-режима (как в исходных скриптах) — объект не потокобезопасен.
- tkinter не любит обновления виджетов из чужого потока: используется queue.Queue + root.after(100, _pump).
- Прерываемый countdown в калибровке: self._stop_evt.wait(timeout=1.0) — реагирует на Stop сразу, без проверки is_set() после sleep.
- После завершения worker'a главный поток обнаружит !is_alive() в _pump и вернёт UI в idle.

## Артефакты
- src/tools.py — единая точка входа: `cd src; python tools.py`

## Что осталось
- ~~Старые pick_color.py / measure.py / calibrate.py можно удалить~~ → удалены по запросу пользователя.
- Подправлен docstring в profiles/nte_fishing.py: ссылка на measure.py/calibrate.py → tools.py.
- Устаревшие .pyc в __pycache__ удалены.

## Обнаруженные навыки
- (пока нет — паттерн «tk + worker thread + queue + after» стандартный, в SKILL.md выносить не стоит)
