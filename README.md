# 🤖 AI Content Telegram Bot

**AI-powered Telegram bot for automatic content generation** using Perplexity AI with RAG (Retrieval-Augmented Generation) support.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-latest-blue.svg)](https://core.telegram.org/bots/api)

## ✨ Features

- 📝 **AI Content Generation** - Generate 200-300 word posts with emojis and call-to-action
- 🔥 **RAG Support** - Upload your own knowledge base files for context-aware generation
- 🌐 **Multi-language** - Automatic RU/EN translation and language detection
- ⏰ **Auto-posting** - Schedule automatic posts to your Telegram channel (every 6 hours)
- 🎯 **Perplexity AI Integration** - Powered by Perplexity Sonar model
- 📊 **User-friendly Interface** - Interactive keyboard with buttons

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Perplexity API Key (from [Perplexity](https://www.perplexity.ai/))
- (Optional) Render.com account for deployment

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Malahit/ai-content-telegram-bot.git
   cd ai-content-telegram-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   For lightweight installation (without RAG):
   ```bash
   pip install -r requirements-lite.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   PPLX_API_KEY=your_perplexity_api_key
   CHANNEL_ID=@your_channel_username
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOT_TOKEN` | ✅ Yes | Telegram Bot Token from @BotFather | `1234567890:ABCdef...` |
| `PPLX_API_KEY` | ✅ Yes | Perplexity API Key | `pplx-...` |
| `CHANNEL_ID` | ⚠️ Optional | Channel username for auto-posting | `@my_channel` |

### RAG (Knowledge Base)

To enable RAG functionality:

1. Create a `knowledge/` directory in the project root
2. Add your `.txt` files with domain-specific content
3. Run the bot - RAG will automatically activate if files are detected

The bot will use your knowledge base to generate more accurate and context-aware content.

## 📖 Usage

### Bot Commands

- `/start` - Start the bot and see the welcome message

### Interactive Buttons

- **📝 Пост** - Generate a new post (prompts for topic)
- **❓ Помощь** - Show help information
- **ℹ️ Статус** - Check bot status and configuration

### Generating Content

1. Click **📝 Пост** or send any text message
2. Enter your topic (e.g., "SMM Москва", "фитнес", "завтрак")
3. Wait 10-20 seconds for generation
4. Receive a formatted post with emojis and structure

### Example Topics

```
SMM стратегии
фитнес и питание
мотивация на каждый день
бизнес идеи 2026
```

## 🌐 Deployment

### Deploy to Render.com

1. **Create a new Web Service** on [Render.com](https://render.com)
2. **Connect your GitHub repository**
3. **Configure Build & Start Commands:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
4. **Add Environment Variables:**
   - `BOT_TOKEN`
   - `PPLX_API_KEY`
   - `CHANNEL_ID` (optional)
5. **Deploy!** 🚀

### Current Deployment

- 🌐 **Live Instance**: [ai-content-telegram-bot.onrender.com](https://ai-content-telegram-bot.onrender.com)
- ✅ **Status**: Online and operational

## 📁 Project Structure

```
ai-content-telegram-bot/
│
├── bot.py                    # Main bot application
├── rag.py                    # RAG vectorstore creation
├── requirements.txt          # Full dependencies (with RAG)
├── requirements-lite.txt     # Minimal dependencies (no RAG)
├── knowledge/                # Knowledge base files for RAG
│   └── test_fitness.txt      # Example knowledge file
├── .env                      # Environment variables (create this)
├── .gitignore               # Git ignore file
├── LICENSE                  # MIT License
└── README.md                # This file
```

## 🛠️ Technical Stack

- **Framework**: [aiogram 3.23.0](https://docs.aiogram.dev/) - Modern Telegram Bot framework
- **AI Model**: [Perplexity Sonar](https://docs.perplexity.ai/) - Advanced language model
- **RAG**: [LangChain](https://python.langchain.com/) + [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- **Translation**: [deep-translator](https://github.com/nidhaloff/deep-translator) - Multi-language support
- **Scheduler**: [APScheduler](https://apscheduler.readthedocs.io/) - Auto-posting functionality

## 🗺️ Roadmap

| Feature | Priority | Status | Complexity |
|---------|----------|--------|------------|
| ✅ Basic content generation | High | Done | ⭐ |
| ✅ RAG integration | High | Done | ⭐⭐⭐ |
| ✅ Auto-posting scheduler | High | Done | ⭐⭐ |
| ✅ Multi-language support | Medium | Done | ⭐ |
| ⏳ Analytics dashboard | Medium | Planned | ⭐⭐ |
| ⏳ Custom domain | Low | Planned | ⭐ |
| ⏳ Web interface | Low | Planned | ⭐⭐⭐ |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Contact & Support

- **GitHub**: [@Malahit](https://github.com/Malahit)
- **Repository**: [ai-content-telegram-bot](https://github.com/Malahit/ai-content-telegram-bot)
- **Issues**: [Report a bug or request a feature](https://github.com/Malahit/ai-content-telegram-bot/issues)

## 🙏 Acknowledgments

- [Perplexity AI](https://www.perplexity.ai/) for the powerful API
- [Telegram](https://telegram.org/) for the Bot API
- [aiogram](https://github.com/aiogram/aiogram) community

---

**Made with ❤️ by Malahit** | **Status**: ✅ Online | **Version**: 2.1 Production
