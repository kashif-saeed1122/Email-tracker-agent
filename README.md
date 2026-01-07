📋 Bill Tracker Agent (Open Source)A fully local, intelligent AI agent that manages your bills, scans emails, finds deals, and sends reminders via WhatsApp, Telegram, or Email. Built with LangGraph, Gemini, and Voyage AI.🚀 Features📧 Intelligent Email Scanning: Connects to Gmail to find bills, invoices, promotions, and orders.🧠 RAG Memory: Stores all your bill data in a local Vector Database (ChromaDB) for semantic search.📄 PDF Intelligence: Extracts text and tables from PDF attachments using OCR if needed.💰 Deal Finder: Uses Web Search to find cheaper alternatives for your subscriptions.🔔 Multi-Channel Reminders: Sends alerts via WhatsApp, Telegram, or Email.💬 Natural Language Chat: Talk to your agent like a human (e.g., "How much did I spend on Uber?").🛠️ Installation Guide1. Clone the Projectgit clone [https://github.com/your-username/bill-tracker-agent.git](https://github.com/your-username/bill-tracker-agent.git)
cd bill-tracker-agent
2. Install DependenciesMake sure you have Python 3.10+ installed.pip install -r requirements.txt
3. Set Up Credentials (.env)Create a file named .env in the root directory and add your keys:# --- AI & Embeddings (Required) ---
GOOGLE_API_KEY=your_gemini_key
VOYAGE_API_KEY=your_voyage_key

# --- Gmail Scanning (Required for Email features) ---
ENABLE_EMAIL_SCANNING=true
GMAIL_CREDENTIALS_PATH=credentials.json

# --- WhatsApp Notifications (Optional) ---
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=whatsapp:+14155238886
TWILIO_TO_NUMBER=whatsapp:+1234567890

# --- Telegram Notifications (Optional) ---
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# --- Email Notifications (Optional) ---
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
🔑 How to get credentials.json for Gmail:Go to Google Cloud Console.Create a project & enable Gmail API.Go to Credentials -> Create OAuth Client ID (Desktop App).Download the JSON file and save it as credentials.json in the project root.🏃 How to RunInteractive Chat ModeThis is the main mode where you can talk to the agent.python main.py
Single Command ModeGreat for quick checks or automation scripts.python main.py --query "Scan for internet bills"
Targeted ScanningScan specifically for certain types of emails.# Scan for University offers
python main.py --scan-type universities --days 90

# Scan for Tax documents
python main.py --scan-type tax --days 365
📚 Example CommandsIntentQuery ExampleScan Bills"Scan my email for new bills"Find Deals"Find me a cheaper alternative to Netflix"History"How much did I pay for electricity last summer?"Reminders"Remind me to pay the rent on WhatsApp"Spending"Analyze my spending on food apps"🏗️ ArchitectureScanner Node: Connects to Gmail, filters emails based on intent (Bill vs Promo), and downloads PDFs.PDF Processor: Extracts raw text and tables from documents.Data Extractor: Uses Gemini 2.5 to convert raw text into structured JSON (Vendor, Amount, Due Date).RAG System: Saves the data into ChromaDB using Voyage AI embeddings.Planner: The agent decides which tools to use based on your request.🤝 ContributingThis is an open-source project! Feel free to:Fork the repo.Add new tools in src/agent/tools.py.Improve the prompts in src/modules/llm_interface.py.Submit a Pull Request.License: MIT