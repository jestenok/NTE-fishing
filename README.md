# vision-bot-python

Скрипт-бот, который смотрит на экран, ищет цветовые признаки в заданных областях и нажимает клавиши/мышь. Игра запускается отдельно — бот ничего не инжектит, только захватывает экран и эмулирует ввод.

## Возможности

- Профили под разные игры: каждая игра — отдельный файл в `src/profiles/` со списком модулей.
- Модули из коробки:
  - **Watcher** — «появилось что-то в области → нажать клавишу/кликнуть мышью». Подходит для всплывающих баннеров, реакции на цвет, иконок-промптов.
  - **Slider** — мини-игра «удерживай ползунок в центре зоны» (рыбалка, ковка, взлом). Детектит зону-цель и маркер по HSV, две клавиши удержания, гистерезис, гуманизатор.
- Окно отладки (`DebugView.WINDOW` / `OVERLAY`) — рисует рамки регионов и факт детекции поверх скриншота.
- GUI-инструменты в `tools.py`: пипетка цвета (HSV-диапазон по нескольким пробам), измерение региона по двум точкам курсора, калибровка слайдера со снимком экрана.

## Установка

Требуется Python 3.13+ и Windows (зависимости: `mss`, `opencv-python`, `numpy`, `pydirectinput`, `keyboard`).

```powershell
cd src
pip install -r requirements.txt
```

## Запуск

Активный профиль выбирается импортом в `src/bot.py`:

```python
from profiles.nte_fishing import PROFILE
```

Замени имя модуля на нужный профиль (`nte_fishing`, `reaction_test`, `cigame`, …) и запусти:

```powershell
cd src
python bot.py
```

Хоткеи задаются профилем. По умолчанию: **F8** — старт/пауза, **F9** — выход (у некоторых профилей переопределено на F3/F4 — смотри `PROFILE.hotkey_toggle` / `hotkey_quit`).

## Подготовка нового профиля

1. Скопируй `src/profiles/nte_fishing.py` в `src/profiles/<имя>.py`.
2. Запусти `python tools.py` и подбери параметры:
   - **Measure region** — F7 в левом-верхнем и правом-нижнем углах нужной области → `Region(x1, y1, x2, y2)` в долях экрана.
   - **Pick color** — F7 над целевым цветом несколько раз → накопительный `HSVRange(...)`.
   - **Calibrate slider** — снимок экрана + детекция полосы для проверки параметров `SliderConfig`.
3. В новом профиле собери `PROFILE = GameProfile(name=..., modules=[...], ...)`.
4. Поменяй импорт в `src/bot.py` на свой профиль.

## Структура проекта

```
src/
  bot.py                 — точка входа, импортирует активный профиль
  tools.py               — GUI: pick color / measure region / calibrate slider
  requirements.txt
  core/
    runner.py            — главный цикл GameBot, ограничитель FPS
    capture.py           — захват экрана через mss
    watcher.py           — Watcher-модуль (FSM: idle → scheduled → cooldown)
    actions.py           — KeyPress / MouseClick
    controller.py        — KeyHolder, удержание клавиш
    geometry.py          — Region в долях экрана
    hsv.py               — HSVRange, маски OpenCV
    humanizer.py         — рандомизация задержек/удержаний
    timing.py            — delay / cooldown генераторы
    debug_view.py        — окно отладки (OpenCV)
    overlay_view.py      — прозрачный оверлей поверх игры (WinAPI layered)
  mechanics/
    slider.py            — SliderConfig + детектор полосы
  profiles/
    base.py              — GameProfile, DebugView
    nte_fishing.py       — рыбалка (slider + 3 watcher-а)
    reaction_test.py     — тест на реакцию (зелёный круг → клик)
    cigame.py            — пример watcher-а с KeyPress(space)
```

## Заметки

- Регионы и координаты везде в долях экрана `[0..1]` — профили переносимы между разрешениями.
- `debug=True` в конфиге модуля включает строки `pixels=… thr=… st=…` в консоль — удобно при подборе порогов.
- Бот не работает с играми в эксклюзивном fullscreen — нужен borderless/оконный режим, чтобы экран был доступен `mss`.
