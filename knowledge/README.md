# Knowledge Base Directory

This directory is used by the RAG (Retrieval-Augmented Generation) system to enhance AI content generation with your custom knowledge.

## Quick Start

- **Add your knowledge files** here (supported formats: `.txt`, `.md`, `.pdf`)
- **Organize as you like** - the RAG system scans all files recursively
- **Auto-reload enabled** - changes are detected automatically, no restart needed
- **Check logs** on bot startup for: `✅ RAG service initialized successfully`
- **Multiple files** - add as many documents as needed for your domain

## Example

```
knowledge/
├── company_info.md
├── product_specs.txt
├── brand_guidelines.pdf
└── README.md (this file)
```

The RAG system will use these documents to provide context-aware content generation.
