# Задача: разделить проект и переписать на C++
Дата: 2026-05-19
Статус: завершено (порт написан, нужна сборка на машине с MSVC+OpenCV)

## План
- python/ — существующий Python-проект (перемещён целиком).
- cpp/ — новый порт на C++: OpenCV, CMake, Desktop Duplication API.
- Архитектура зеркалит Python: core/ (capture, input, timing, humanizer,
  watcher, debug_view, runner), mechanics/slider, profiles.

## Решения
- Зрение: OpenCV C++ (cv::inRange/cvtColor/imshow).
- Сборка: CMake, C++20.
- Захват: Desktop Duplication (DXGI). Один общий кадр на тик (Desktop
  синглтон), модули вырезают свой регион — captures экрана один раз/тик.
- C++-фишки: std::optional вместо |None, enum class Dir, виртуальные
  интерфейсы (IModule/IAction/IDelay/ICooldown), RAII (ComPtr, unique_ptr),
  std::chrono, designated initializers для конфигов.
- Профили компилируются в бинарь (нет importlib): profiles.cpp + find_profile.

## Прогресс
- Репозиторий разделён: python/ (весь старый код), cpp/ (новый).
- Написан весь C++-порт, 24 файла:
  core/ — random, geometry, hsv, timing, module, capture (Desktop Duplication),
  input (SendInput), humanizer (полный порт 6-стадийного пайплайна),
  watcher, debug_view, runner; mechanics/slider; profiles/ (3 профиля);
  CMakeLists.txt, README.md, main.cpp.
- Desktop — синглтон: один снимок экрана/тик, модули вырезают регион.
- Humanizer портирован 1:1 (стейджи как приватные методы с ранним выходом).

## НЕ проверено
- Компиляция: в текущей среде нет MSVC + OpenCV + Windows SDK. Нужна
  сборка на машине пользователя (vcpkg install opencv4 + cmake).

## Обнаруженные навыки
- нет
