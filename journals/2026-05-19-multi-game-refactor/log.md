# Задача: разделить логику бота для работы с разными играми
Дата: 2026-05-19
Статус: завершено

## План
- core/ — движок (game-agnostic): capture, hsv, geometry, controller, humanizer,
  watcher, module, runner.
- mechanics/ — реализации мини-игр; slider.py (циан-зона + ползунок).
- profiles/ — профиль на игру, Python-файл с PROFILE = GameProfile(...).
- settings.py — ACTIVE_PROFILE.
- bot.py — точка входа: python bot.py [профиль].
- calibrate.py — обновить под профиль, починить дубль main().
- measure.py — поправить импорт io_utils.

## Решения
- Бот = список Module'ей. Module: name, tick(now)->str|None, on_stop().
- Слайдер-механика и 3 сторожа стали модулями. 3 почти одинаковых watcher'а
  слиты в один RegionWatcher (параметризуется cooldown_s: None=ждать пропадания,
  (a,b)=таймер).
- Профиль хранит список конфигов (SliderConfig/WatcherConfig), у каждого .build().

## Прогресс
- Создан core/ (geometry, hsv, io_utils, capture, controller, humanizer,
  module, watcher, runner), mechanics/slider.py, profiles/ (base.py, default.py),
  settings.py. bot.py и calibrate.py переписаны под профили, measure.py — импорт.
- Удалены config.py, vision.py, humanizer.py, controller.py, io_utils.py.
- Проверка: py_compile всех файлов — OK; load_profile('default') — 4 модуля;
  build_modules() — SliderMechanic + 3 RegionWatcher, все с tick/on_stop;
  import GameBot — OK; python calibrate.py (без арг) — OK.

## Итог
- Чтобы добавить игру: profiles/<имя>.py с PROFILE = GameProfile(...).
- Запуск: python bot.py [профиль]; калибровка: python calibrate.py [--profile N] screen|file.
- Багфикс попутно: убран дубль main() в calibrate.py (раньше парсинг
  аргументов не работал).

## Обнаруженные навыки
- нет
