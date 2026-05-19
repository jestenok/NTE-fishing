# Задача: адаптировать проект под открытие vision-bot целиком в CLion
Дата: 2026-05-19
Статус: завершено

## План
CLion на cpp/src/core/input.cpp пишет "file does not belong to any project",
т.к. CMakeLists.txt лежит в cpp/, а пользователь открывает каталог vision-bot.

## Прогресс
- Проверена структура: cpp/CMakeLists.txt объявляет add_executable(vision_bot ...),
  input.cpp уже в списке исходников цели.
- Создан корневой W:\my_projects\vision-bot\CMakeLists.txt с add_subdirectory(cpp).
- Пользователю: открыть vision-bot, дать CLion перезагрузить CMake-проект.

## Решения и находки
- CLion определяет корень CMake-проекта по CMakeLists.txt в открытой папке.
  При вложенном CMakeLists нужен корневой с add_subdirectory(), либо
  правый клик по cpp/CMakeLists.txt -> Load CMake Project.
- .idea сейчас от PyCharm (PYTHON_MODULE NTE-fishing.iml); CLion добавит свой
  CMake-конфиг в тот же .idea — при совместном использовании PyCharm/CLion
  возможны конфликты workspace.xml.

## Обнаруженные навыки
- (нет)
