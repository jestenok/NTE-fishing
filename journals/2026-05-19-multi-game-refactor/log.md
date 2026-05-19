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

## Дополнение: игра reaction-test (2026-05-19)
- Сначала сделал отдельной механикой (mechanics/reaction.py) — оказалось
  дублированием автомата RegionWatcher. Переделал.
- Действие сторожа вынесено в core/actions.py: Action (Protocol),
  KeyPress (клавиша), MouseClick (мышь).
- WatcherConfig: key → action; добавлен min_fill (порог как доля площади
  региона, альтернатива min_pixels); __post_init__ проверяет, что задан
  ровно один из двух.
- mechanics/reaction.py удалён. reaction-test — теперь WatcherConfig с
  action=MouseClick, min_fill=0.5, delay_s=(0.12,0.22), cooldown_s=None.
- Урок: «новая игра» != «новая механика». reaction по поведению — сторож,
  отдельная механика оправдана только при иной логике (как slider).

## Дополнение: тайминг-стратегии (2026-05-19)
- core/timing.py: Delay (NoDelay/RandomDelay) + Cooldown (UntilGone/
  TimerCooldown), фабрики make_delay/make_cooldown. Стратегия выбирается
  один раз на этапе билда — в tick() нет ветвлений по delay/cooldown.
- RegionWatcher переведён на _delay и _cooldown; убраны _instant,
  _cooldown_until и ветка `if cooldown_s is None` из горячего цикла.

## Обнаруженные навыки
- нет
