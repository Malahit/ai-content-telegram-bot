# AI Content Telegram Bot - Refactoring Documentation

## Overview

This document describes the refactoring improvements made to the AI Content Telegram Bot codebase to enhance code quality, maintainability, security, and testability.

## Key Improvements

### 1. **Code Organization**

The monolithic `bot.py` has been modularized into specialized components:

- **`config.py`**: Configuration management with environment variable loading and validation
- **`logger_config.py`**: Centralized logging setup with security filters
- **`api_client.py`**: Perplexity API client with error handling and retry logic
- **`translation_service.py`**: Translation functionality with fallback mechanisms
- **`rag_service.py`**: RAG (Retrieval-Augmented Generation) functionality
- **`bot.py`**: Main bot logic, now clean and focused

### 2. **Error Handling**

Enhanced error handling throughout the codebase:

- **Retry Logic**: API calls automatically retry on temporary failures (up to 3 attempts)
- **Graceful Degradation**: Optional features (RAG, translation) fail gracefully when dependencies are missing
- **User-Friendly Messages**: Clear error messages for users when operations fail
- **Comprehensive Logging**: All errors are logged with context for debugging

### 3. **Security**

Implemented security best practices:

- **Sensitive Data Filter**: Automatic redaction of tokens, API keys, and passwords from logs
- **No Token Exposure**: Configuration values are never printed to console
- **Safe Logging**: `get_safe_config_info()` provides configuration status without exposing secrets
- **Environment Variable Validation**: Required credentials are validated at startup

### 4. **Logging and Debugging**

Structured logging system:

- **Log Levels**: Proper use of DEBUG, INFO, WARNING, and ERROR levels
- **Contextual Messages**: Each log entry includes relevant context
- **Security Filtering**: Sensitive data is automatically redacted
- **Consistent Format**: Timestamp, level, and message in every log entry

### 5. **Performance**

Optimized for efficiency:

- **Lazy Loading**: Optional modules (RAG, translation) only load when available
- **Async/Await**: Proper use of asynchronous operations
- **Connection Pooling**: Reusable API client instance
- **Configurable Timeouts**: Prevents hanging operations

### 6. **Testing**

Test infrastructure for quality assurance:

- **Unit Tests**: Comprehensive test coverage for all modules
- **Mocking**: External dependencies are mocked for isolated testing
- **Configuration Tests**: Validation of environment variable handling
- **Security Tests**: Verification of sensitive data filtering

### 7. **Documentation**

Complete documentation:

- **Module Docstrings**: Every module has a descriptive docstring
- **Function Docstrings**: All functions document parameters, returns, and behavior
- **Type Hints**: Clear type annotations for better IDE support
- **Inline Comments**: Complex logic is explained with comments

## Architecture

```
┌─────────────────┐
│     bot.py      │  Main bot logic and handlers
└────────┬────────┘
         │
         ├─────────► config.py           Configuration management
         ├─────────► logger_config.py    Logging setup
         ├─────────► api_client.py       Perplexity API client
         ├─────────► translation_service.py  Translation functionality
         └─────────► rag_service.py      RAG functionality
```

## Configuration

All configuration is managed through environment variables:

### Required Variables

- `BOT_TOKEN`: Telegram bot token
- `PPLX_API_KEY`: Perplexity API key

### Optional Variables

- `CHANNEL_ID`: Target channel for autoposts (default: @content_ai_helper_bot)
- `API_TIMEOUT`: API request timeout in seconds (default: 45)
- `MAX_TOKENS`: Maximum tokens for API responses (default: 800)
- `TEMPERATURE`: Response generation temperature (default: 0.8)
- `API_MODEL`: Perplexity model to use (default: sonar)
- `AUTOPOST_INTERVAL_HOURS`: Hours between autoposts (default: 6)
- `RAG_SEARCH_K`: Number of RAG documents to retrieve (default: 2)
- `RAG_CONTEXT_MAX_CHARS`: Max characters per RAG document (default: 400)

## Running Tests

```bash
# Run all tests
cd tests
python3 run_tests.py

# Run specific test module
python3 -m unittest tests.test_config

# Run with coverage (if pytest-cov is installed)
pytest tests/ --cov=. --cov-report=html
```

## Security Features

### 1. Sensitive Data Filter

The `SensitiveDataFilter` class automatically redacts:
- Tokens (BOT_TOKEN, etc.)
- API keys (PPLX_API_KEY, etc.)
- Bearer tokens in Authorization headers
- Passwords

Example:
```python
# Input: "Bot token: abc123xyz"
# Output: "Bot token: ***REDACTED***"
```

### 2. Safe Configuration Info

The `get_safe_config_info()` method provides status without exposing secrets:

```python
{
    "bot_token_configured": True,      # Status only
    "api_key_configured": True,        # Status only
    "channel_id": "@content_ai_helper_bot",  # Non-sensitive
    "api_model": "sonar",              # Non-sensitive
    ...
}
```

## Error Handling Examples

### API Errors

```python
# Automatic retry on timeout
try:
    content = api_client.generate_content(topic)
except PerplexityAPIError as e:
    # User sees friendly message
    return "❌ Не удалось сгенерировать контент. Попробуйте позже."
```

### Optional Features

```python
# RAG gracefully disabled when unavailable
if rag_service.is_enabled():
    context, info = rag_service.get_context(topic)
else:
    context, info = "", ""  # Continue without RAG
```

## Migration Guide

For users upgrading from the old code:

1. **No Changes Required**: The refactored code maintains backward compatibility
2. **Environment Variables**: Same `.env` file works
3. **New Features**: Optional configuration variables can be added to `.env`
4. **Testing**: New test suite can verify installation

## Future Enhancements

Potential improvements for future iterations:

1. **Database Integration**: Store generated posts for analytics
2. **Metrics Collection**: Track API usage and performance
3. **Rate Limiting**: Implement request rate limiting
4. **Caching**: Cache frequently requested topics
5. **CI/CD Pipeline**: Automated testing and deployment
6. **Docker Support**: Containerization for easier deployment

## Contributing

When contributing to the codebase:

1. Follow existing code style and patterns
2. Add docstrings to all functions and classes
3. Include type hints for better IDE support
4. Write unit tests for new functionality
5. Update documentation as needed
6. Ensure sensitive data is not logged

## Support

For issues or questions:

1. Check the logs for detailed error messages
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed
4. Review the test suite for usage examples
