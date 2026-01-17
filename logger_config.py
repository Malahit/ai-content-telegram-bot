def filter(self, record: logging.LogRecord) -> bool:
    message = record.getMessage()
    
    # Сначала стандартные паттерны
    for pattern, replacement in self.PATTERNS:
        message = pattern.sub(replacement, message)
    
    # Затем специфичные маскировки
    message = self.mask_sensitive_data(message)  # ← Добавить эту строку
    
    record.msg = message
    record.args = ()
    return True