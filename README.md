# Email Management Agent (Open Source)

A fully local, intelligent AI agent that manages your emails, scans for bills/universities/promotions, finds deals, and sends reminders. Built with LangGraph, OpenAI, and Voyage AI.

## 🚀 Features

- 📧 **Intelligent Email Scanning**: Connects to Gmail to find bills, invoices, promotions, university admissions, orders, and more
- 🧠 **RAG Memory with Structured Storage**: Stores emails as searchable JSON in ChromaDB Vector Database
- 🔍 **Smart Query vs Scan**: Knows when to fetch new emails vs search existing data
- 📄 **PDF Intelligence**: Extracts text and tables from PDF attachments with OCR fallback
- 💰 **Deal Finder**: Uses Web Search to find cheaper alternatives for subscriptions
- 🔔 **Multi-Channel Reminders**: Sends alerts via WhatsApp, Telegram, or Email
- 💬 **Natural Language Chat**: Ask questions like "What emails did I get from Germany?" or "Scan for university admissions"

## 🆕 What's New

- ✅ **OpenAI Powered**: Uses GPT-4.1-nano for fast, cost-efficient processing
- ✅ **Agentic Workflow**: Automatically decides whether to scan Gmail or query the database
- ✅ **Structured Email Indexing**: Emails saved as JSON with metadata (sender, subject, category, date)
- ✅ **Multi-Type Support**: bills, promotions, universities, orders, shipping, banking, insurance, and more
- ✅ **Flexible Configuration**: Support for both .env and config.yaml with interactive setup wizard

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/email-management-agent.git
cd email-management-agent
```

### 2. Install Dependencies

Requires Python 3.10+

```bash
pip install -r requirements.txt
```

### 3. Configuration Setup

You have **three options** to configure the agent:

#### Option A: Interactive Setup Wizard (Recommended)

```bash
python main.py --setup
```

This will guide you through:
- API key configuration (OpenAI, Voyage AI)
- Email credentials setup
- Default settings customization

#### Option B: .env File (Secure)

Create a `.env` file in the root directory:

```env
# ===== AI & Embeddings (Required) =====
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
VOYAGE_API_KEY=pa-xxxxxxxxxxxxx

# Optional: Override default model (default is gpt-4o-mini)
OPENAI_MODEL=gpt-4o-mini

# ===== Gmail Scanning (Required for Email features) =====
ENABLE_EMAIL_SCANNING=true
GMAIL_CREDENTIALS_PATH=credentials.json
EMAIL_ADDRESS=your_email@gmail.com

# ===== Email Notifications (Optional) =====
EMAIL_PASSWORD=your_gmail_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# ===== WhatsApp Notifications (Optional) =====
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=whatsapp:+14155238886
TWILIO_TO_NUMBER=whatsapp:+1234567890

# ===== Telegram Notifications (Optional) =====
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# ===== Configuration =====
EMAIL_SCAN_MAX_RESULTS=50
DEFAULT_EMAIL_SCAN_TYPE=general
```

#### Option C: config.yaml File (Convenient)

Create a `config.yaml` file in the root directory:

```yaml
# LLM Configuration
llm:
  provider: "openai"
  model: "gpt-4o-mini"
  temperature: 0.1

# Embeddings Configuration
embeddings:
  provider: "voyage"
  model: "voyage-3-lite"

# Date/Time Defaults
scanning:
  default_days_back: 30      # How many days to scan by default
  date_format: "YYYY-MM-DD"
  max_results: 50

# API Keys (Optional - .env is more secure)
api_keys:
  openai_api_key: ""         # Leave empty to use .env
  voyage_api_key: ""         # Leave empty to use .env

# Email Credentials (Optional - .env is more secure)
credentials:
  email_address: ""
  email_password: ""

# Email Settings
email:
  gmail_credentials_path: "credentials.json"
  gmail_token_path: "token.json"
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  default_scan_type: "general"

# Storage Configuration
storage:
  base_dir: "./data"
  raw_data: "raw"
  processed_data: "processed"
  vector_store: "vector_store"

# Feature Flags
features:
  enable_email_scanning: true
  enable_rag: true
  enable_reminders: true
```

**Configuration Priority:** Session keys > .env > config.yaml > Defaults

**Security Note:** Use .env for API keys and credentials, use config.yaml for settings like model, days, etc.

### 4. Verify Configuration

```bash
# Check if everything is configured correctly
python diagnose_config.py

# Validate all settings
python main.py --validate

# Show current configuration
python main.py --show-config
```

### 5. Set Up Gmail API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Gmail API**
4. Go to **Credentials** → **Create Credentials** → **OAuth Client ID**
5. Choose **Desktop App**
6. Download the JSON file and save it as `credentials.json` in the project root
7. On first run, you'll be prompted to authorize the app in your browser

### 6. Get API Keys

**OpenAI API Key:**
- Sign up at [OpenAI Platform](https://platform.openai.com/)
- Go to API Keys section
- Create new secret key
- Format: `sk-proj-...`

**Voyage AI API Key (Required for indexing!):**
- Sign up at [Voyage AI](https://www.voyageai.com/)
- Get your API key from dashboard
- Format: `pa-v1-...`
- **⚠️ Without this key, emails won't be indexed to the database!**

## 🏃 How to Run

### Interactive Chat Mode

```bash
python main.py
```

Example conversation:
```
You: Scan my inbox for university emails from Germany
Agent: [Scans Gmail, indexes 5 emails] Found 5 university emails...

You: What did you get from Germany?
Agent: [Searches database] I found 5 emails from German institutions...

You: Show me the Constructor University email
Agent: [Searches by keyword] Here's the email from Constructor University...
```

### Single Command Mode

```bash
python main.py --query "What emails did I get about scholarships?"
```

### Targeted Scanning

```bash
# Scan for university admission emails (last 90 days)
python main.py --scan-type universities --days 90

# Scan for bills (last 30 days)
python main.py --scan-type bills --days 30

# Scan for promotions (last 7 days)
python main.py --scan-type promotions --days 7
```

### Configuration Commands

```bash
# Run interactive setup
python main.py --setup

# Show current configuration
python main.py --show-config

# Validate configuration
python main.py --validate

# Enable interactive prompts for missing keys
python main.py --interactive
```

## 💬 Example Commands

### Scan Commands (Fetch from Gmail)
| Query | What Happens |
|-------|--------------|
| "Scan my inbox for university emails" | Fetches new emails from Gmail, indexes them |
| "Check for admission emails from Germany" | Scans Gmail with LLM filtering |
| "Get bills from last month" | Fetches and indexes bill-related emails |
| "Find promotion emails" | Scans for marketing offers |

### Query Commands (Search Database)
| Query | What Happens |
|-------|--------------|
| "What emails did you find from Germany?" | Searches indexed emails (no Gmail scan) |
| "Show me university emails" | Queries Vector DB |
| "Is there anything about scholarships?" | Semantic search through stored emails |
| "Do I have emails from Constructor?" | Searches by keyword |

### Other Commands
| Query | What Happens |
|-------|--------------|
| "Find cheaper alternatives to Netflix" | Web search for deals |
| "Analyze my spending on subscriptions" | Queries database and analyzes |
| "Remind me to pay rent" | Creates reminders |

## 🏗️ Architecture

### Agentic Workflow

```
User Query → Intent Classifier → Planner → Execute Plan → Response
```

**Intent Classification:**
- `scan_emails`: Fetch NEW emails from Gmail
- `query_history`: Search EXISTING database (no Gmail scan)
- `analyze_spending`: Analyze financial data
- `find_alternatives`: Web search for deals
- `set_reminder`: Create reminders

### Email Processing Pipeline

```
Gmail API → LLM Filtering → PDF Extraction → Data Structuring → Vector DB
```

1. **Email Scanner**: Fetches emails, applies LLM-based relevance filtering
2. **PDF Processor**: Extracts text from attachments (PyPDF2 → pdfplumber → OCR)
3. **Data Extractor**: Uses OpenAI to extract structured data (vendor, amount, date)
4. **Database Saver**: Indexes emails as JSON with rich metadata using Voyage AI embeddings

### Email Storage Format

Each email is stored with structured metadata:

```json
{
  "type": "email",
  "category": "universities",
  "sender": "graduateadmission@constructor.university",
  "subject": "Welcome to Constructor University",
  "date": "2026-01-07",
  "body_preview": "Dear Malik...",
  "summary": "University admission welcome email",
  "has_attachments": false
}
```

### Tech Stack

- **LLM**: OpenAI GPT-4.1-mini/nano (default) or GPT-4o
- **Embeddings**: Voyage AI (voyage-3.5-lite)
- **Vector DB**: ChromaDB (local, persistent)
- **Orchestration**: LangGraph
- **Email**: Gmail API
- **PDF Parsing**: PyPDF2, pdfplumber, pytesseract (OCR)

## 📁 Project Structure

```
email-management-agent/
├── src/
│   ├── agent/
│   │   ├── graph.py          # LangGraph workflow
│   │   ├── nodes.py          # Workflow nodes
│   │   ├── state.py          # Agent state
│   │   └── tools.py          # LangChain tools
│   ├── modules/
│   │   ├── email_scanner.py  # Gmail integration
│   │   ├── llm_interface.py  # OpenAI wrapper
│   │   ├── pdf_parser.py     # PDF extraction
│   │   └── rag_system.py     # Vector DB operations
│   └── config/
│       └── settings.py       # Configuration loader
├── data/
│   ├── raw/                  # Downloaded attachments
│   └── vector_store/         # ChromaDB storage
├── config.yaml               # Configuration file (optional)
├── credentials.json          # Gmail OAuth
├── .env                      # API keys (recommended)
└── main.py                   # Entry point
```

## 🔧 Supported Email Types

The agent can scan and categorize:

- 📄 **bills**: Utility bills, invoices, statements
- 🎓 **universities**: Admission emails, offers, assessments
- 🎁 **promotions**: Marketing offers, discounts
- 🛍️ **orders**: Purchase confirmations, receipts
- 📦 **shipping**: Tracking, delivery notifications
- 💳 **banking**: Statements, transaction alerts
- 🏥 **insurance**: Policies, claims
- ✈️ **travel**: Bookings, itineraries
- 📋 **tax**: Tax documents, 1099s, W-2s
- 📝 **general**: Anything else

## 🤝 Contributing

This is an open-source project! Contributions welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes:
   - Add new tools in `src/agent/tools.py`
   - Improve prompts in `src/modules/llm_interface.py`
   - Add email types in `src/config/email_scan_config.py`
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request


## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [OpenAI](https://openai.com/) - Language models
- [Voyage AI](https://www.voyageai.com/) - Embeddings
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Gmail API](https://developers.google.com/gmail/api) - Email access

---

**⭐ Star this repo if you find it useful!**

For questions or issues, open an [Issue](https://github.com/your-username/email-management-agent/issues) or [Discussion](https://github.com/your-username/email-management-agent/discussions).
