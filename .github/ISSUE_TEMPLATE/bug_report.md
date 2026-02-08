name: Сообщение об ошибке
description: Сообщить об ошибке или проблеме в работе бота
title: "[БАГ]: "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        Спасибо за сообщение об ошибке! Пожалуйста, заполните форму ниже.
  
  - type: textarea
    id: description
    attributes:
      label: Описание проблемы
      description: Краткое описание проблемы
      placeholder: Опишите проблему...
    validations:
      required: true
  
  - type: textarea
    id: reproduction
    attributes:
      label: Шаги для воспроизведения
      description: Как воспроизвести проблему?
      placeholder: |
        1. Перейти к '...'
        2. Нажать на '...'
        3. Увидеть ошибку
    validations:
      required: true
  
  - type: textarea
    id: expected
    attributes:
      label: Ожидаемое поведение
      description: Что должно было произойти?
      placeholder: Опишите ожидаемое поведение...
    validations:
      required: true
  
  - type: textarea
    id: actual
    attributes:
      label: Фактическое поведение
      description: Что произошло на самом деле?
      placeholder: Опишите фактическое поведение...
    validations:
      required: true
  
  - type: input
    id: version
    attributes:
      label: Версия приложения
      description: Какую версию вы используете?
      placeholder: например, v1.0.0
    validations:
      required: false
  
  - type: input
    id: commit
    attributes:
      label: Коммит
      description: SHA коммита (если известен)
      placeholder: например, abc123def
    validations:
      required: false
  
  - type: input
    id: platform
    attributes:
      label: Платформа
      description: На какой платформе вы запускаете бот?
      placeholder: например, Linux, Docker, Railway
    validations:
      required: false
  
  - type: textarea
    id: attachments
    attributes:
      label: Вложения
      description: Скриншоты, логи или другие файлы (при наличии)
      placeholder: Вставьте скриншоты или логи...
    validations:
      required: false
  
  - type: checkboxes
    id: checklist
    attributes:
      label: Чеклист
      description: Пожалуйста, подтвердите следующее
      options:
        - label: Я убедился, что в сообщении нет секретов (токены, API ключи и т.д.)
          required: true
        - label: Я проверил, что похожие issue не были созданы ранее
          required: true
