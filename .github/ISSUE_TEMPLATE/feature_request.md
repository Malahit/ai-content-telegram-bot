name: Запрос функциональности
description: Предложить новую функцию или улучшение
title: "[ФУНКЦИЯ]: "
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: |
        Спасибо за предложение! Пожалуйста, заполните форму ниже.
  
  - type: textarea
    id: problem
    attributes:
      label: Проблема
      description: Какую проблему решает эта функция?
      placeholder: Опишите проблему, которую вы хотите решить...
    validations:
      required: true
  
  - type: textarea
    id: desired-outcome
    attributes:
      label: Желаемый результат
      description: Как должна работать новая функция?
      placeholder: Опишите желаемое поведение...
    validations:
      required: true
  
  - type: textarea
    id: alternatives
    attributes:
      label: Альтернативы
      description: Рассматривали ли вы альтернативные решения?
      placeholder: Опишите альтернативные решения, которые вы рассматривали...
    validations:
      required: false
  
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
      description: Скриншоты, макеты или другие файлы (при наличии)
      placeholder: Вставьте скриншоты или другую информацию...
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
