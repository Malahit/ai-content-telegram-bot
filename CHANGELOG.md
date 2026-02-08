# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-02-08

### Added
- RAG (Retrieval-Augmented Generation) support with configurable embeddings model
- Knowledge base directory structure for RAG document storage
- Support for .txt, .md, and .pdf document formats in RAG
- RAG_ENABLED environment variable for optional RAG functionality
- Graceful degradation when RAG dependencies are unavailable

### Changed
- RAG dependencies split into separate requirements-rag.txt file
- Default embeddings model set to sentence-transformers/all-MiniLM-L6-v2
- Enhanced documentation for RAG configuration and usage

### Fixed
- RAG service now creates knowledge directory even when disabled
- Improved error handling for missing RAG dependencies

## [0.1.0] - 2026-01-03

### Added
- Initial release of AI Content Telegram Bot
- AI-powered content generation using Perplexity Sonar API
- Text-only post generation (200-300 words)
- Image post generation with Pexels API integration (up to 3 images)
- Multi-language support (Russian/English) with automatic translation
- Admin-only statistics tracking
- Auto-posting functionality (every 6 hours)
- User and payment management system with SQLite database
- Subscription middleware and payment service
- Mobile React Native application for content browsing
- Instance locking to prevent multiple bot instances
- Graceful shutdown handling with cleanup
- Comprehensive test suite
- Modular architecture with separated services

[Unreleased]: https://github.com/Malahit/ai-content-telegram-bot/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/Malahit/ai-content-telegram-bot/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Malahit/ai-content-telegram-bot/releases/tag/v0.1.0
