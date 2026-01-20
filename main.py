import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent.graph import BillTrackerAgent, create_agent
from src.config.settings import settings, Settings
from src.config.email_scan_config import config as email_config
from src.modules.reminder_scheduler import ReminderScheduler
from src.modules.reminder_storage import ReminderStorage
from src.modules.reminder_system import ReminderSystem
from datetime import datetime
import argparse
import atexit

# Global scheduler instance
_scheduler: ReminderScheduler = None


def start_reminder_scheduler():
    """Initialize and start the background reminder scheduler"""
    global _scheduler

    if not settings.ENABLE_REMINDERS:
        print("   Reminders disabled in config")
        return None

    try:
        # Initialize storage
        storage = ReminderStorage(db_path=settings.REMINDER_DB_PATH)

        # Initialize sender with configured credentials
        sender = ReminderSystem(
            email_address=settings.EMAIL_ADDRESS,
            email_password=settings.EMAIL_PASSWORD,
            smtp_server=settings.SMTP_SERVER,
            smtp_port=settings.SMTP_PORT,
            telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
            telegram_chat_id=settings.TELEGRAM_CHAT_ID,
            twilio_account_sid=settings.TWILIO_ACCOUNT_SID,
            twilio_auth_token=settings.TWILIO_AUTH_TOKEN,
            twilio_whatsapp_from=settings.TWILIO_WHATSAPP_FROM,
            twilio_whatsapp_to=settings.TWILIO_WHATSAPP_TO
        )

        # Create scheduler
        _scheduler = ReminderScheduler(
            storage=storage,
            sender=sender,
            check_interval=settings.REMINDER_CHECK_INTERVAL
        )

        # Start background thread
        _scheduler.start()

        # Register cleanup on exit
        atexit.register(stop_reminder_scheduler)

        return _scheduler

    except Exception as e:
        print(f"   Failed to start scheduler: {e}")
        return None


def stop_reminder_scheduler():
    """Stop the reminder scheduler gracefully"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


def get_scheduler_status() -> dict:
    """Get current scheduler status"""
    global _scheduler
    if _scheduler:
        return _scheduler.get_status()
    return {"running": False, "message": "Scheduler not initialized"}


def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║              📋 BILL TRACKER AGENT 🤖                         ║
    ║                                                               ║
    ║         Intelligent Bill Management with AI                   ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def setup_configuration():
    """
    Interactive configuration setup wizard
    """
    print_banner()
    print("\n🔧 Configuration Setup Wizard")
    print("="*70)
    
    print("\nThis will help you configure the Bill Tracker Agent.")
    print("You can set API keys and customize default settings.\n")
    
    # Check for existing config
    print("📁 Checking existing configuration...")
    
    config_file = Path(__file__).parent / "config.yaml"
    env_file = Path(__file__).parent / ".env"
    
    print(f"   config.yaml: {'✅ Found' if config_file.exists() else '❌ Not found'}")
    print(f"   .env file: {'✅ Found' if env_file.exists() else '❌ Not found'}")
    
    # API Key setup
    print("\n🔑 API Key Setup")
    print("-"*70)
    
    # OpenAI
    openai_key = Settings.get_openai_api_key()
    if openai_key:
        print(f"✅ OPENAI_API_KEY: Configured (****{openai_key[-4:]})")
    else:
        print("⚠️  OPENAI_API_KEY: Not configured")
        Settings.get_openai_api_key(interactive=True)
    
    # Voyage
    voyage_key = Settings.get_voyage_api_key()
    if voyage_key:
        print(f"✅ VOYAGE_API_KEY: Configured (****{voyage_key[-4:]})")
    else:
        print("⚠️  VOYAGE_API_KEY: Not configured")
        Settings.get_voyage_api_key(interactive=True)
    
    print("\n✅ Configuration setup complete!")
    print("\n💡 You can now run the agent with: python main.py")
    print("💡 Or start interactive mode: python main.py (no arguments)\n")


def validate_configuration(interactive: bool = False):
    """
    Validate configuration with optional interactive prompts
    """
    print("\n🔍 Validating configuration...")
    
    is_valid, errors = settings.validate(interactive=interactive)
    
    if not is_valid:
        print("\n❌ Configuration validation failed:")
        for error in errors:
            print(f"   - {error}")
        
        if not interactive:
            print("\n💡 Options:")
            print("   1. Run setup wizard: python main.py --setup")
            print("   2. Set keys in .env file")
            print("   3. Set keys in config.yaml")
            print("   4. Pass --interactive flag to enter keys now")
        
        return False
    
    print("✅ Configuration validated successfully!")
    print("\n" + settings.get_config_summary())
    return True


def interactive_mode(scan_type=None, scan_days=None):
    print_banner()

    if not validate_configuration(interactive=True):
        print("\n❌ Cannot start without valid configuration.")
        return
    if scan_type:
        print(f"📧 Default scan type: {scan_type}")
    if scan_days:
        print(f"📅 Default scan days: {scan_days}")
    else:
        print(f"📅 Default scan days: {settings.DEFAULT_DAYS_BACK}")

    print("\n⏰ Starting reminder scheduler...")
    scheduler = start_reminder_scheduler()
    if scheduler:
        print(f"   Scheduler running (checking every {settings.REMINDER_CHECK_INTERVAL}s)")
    else:
        print("   Scheduler not started (check configuration)")

    print("\n💡 Type 'help' for available commands, 'exit' to quit\n")

    try:
        agent = create_agent()
    except Exception as e:
        print(f"\n❌ Failed to initialize agent: {e}")
        return

    history = []

    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye! Have a great day!")
                break
            
            elif user_input.lower() == 'help':
                print_help()
                continue
            
            elif user_input.lower() == 'types':
                print(email_config.get_config_summary())
                continue
            
            elif user_input.lower() == 'history':
                print_history(history)
                continue
            
            elif user_input.lower() == 'clear':
                os.system('clear' if os.name == 'posix' else 'cls')
                print_banner()
                continue
            
            elif user_input.lower() == 'config':
                print("\n" + settings.get_config_summary())
                continue
            
            elif user_input.lower() == 'setup':
                setup_configuration()
                continue

            elif user_input.lower() == 'reminders':
                status = get_scheduler_status()
                print(f"\n⏰ Reminder Scheduler Status:")
                print(f"   Running: {'✅ Yes' if status.get('running') else '❌ No'}")
                if status.get('stats'):
                    stats = status['stats']
                    print(f"   Pending: {stats.get('pending', 0)}")
                    print(f"   Sent: {stats.get('sent', 0)}")
                    print(f"   Failed: {stats.get('failed', 0)}")
                if status.get('upcoming_24h', 0) > 0:
                    print(f"   Upcoming (24h): {status['upcoming_24h']}")
                    if status.get('next_reminders'):
                        print(f"   Next reminders:")
                        for rem in status['next_reminders'][:3]:
                            print(f"      - {rem.get('vendor', 'Unknown')}: {rem.get('reminder_date', 'N/A')}")
                continue

            elif user_input.lower() == 'check-reminders':
                if _scheduler:
                    print("\n⏰ Manually checking reminders...")
                    result = _scheduler.check_now()
                    print(f"   Checked: {result.get('checked', 0)}")
                    print(f"   Sent: {result.get('sent', 0)}")
                    print(f"   Failed: {result.get('failed', 0)}")
                else:
                    print("\n❌ Scheduler not running")
                continue

            history.append({
                "timestamp": datetime.now().isoformat(),
                "query": user_input
            })
            
            enriched_query = user_input
            if scan_type and "scan" in user_input.lower():
                enriched_query += f" [type:{scan_type}]"
            
            if scan_days:
                if "scan" in user_input.lower():
                    enriched_query += f" [days:{scan_days}]"
            elif "scan" in user_input.lower() and "days" not in user_input.lower():
                enriched_query += f" [days:{settings.DEFAULT_DAYS_BACK}]"
            
            result = agent.invoke(enriched_query, verbose=True)
            
            print(f"\n🤖 Agent: {result['response']}")
            
            if result.get('metadata'):
                meta = result['metadata']
                if meta.get('saved_bills', 0) > 0:
                    print(f"\n💾 Saved {meta['saved_bills']} bills")
                if meta.get('reminders_created', 0) > 0:
                    print(f"⏰ Created {meta['reminders_created']} reminders")
            
            if result.get('errors'):
                print(f"\n⚠️  Warnings/Errors:")
                for error in result['errors'][:3]:
                    print(f"   - {error}")
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted. Type 'exit' to quit or continue chatting.")
            continue
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue


def single_query_mode(query: str, user_id: str = "default", scan_type=None, scan_days=None):
    print_banner()
    
    if not validate_configuration():
        return
    
    if scan_type:
        query += f" [type:{scan_type}]"
    if scan_days:
        query += f" [days:{scan_days}]"
    elif "scan" in query.lower():
        query += f" [days:{settings.DEFAULT_DAYS_BACK}]"
    
    print(f"\n📝 Query: {query}\n")
    
    try:
        agent = create_agent()
        result = agent.invoke(query, user_id=user_id, verbose=True)
        
        print(f"\n🤖 Response:")
        print(result['response'])
        
        return result
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


def batch_mode(queries_file: str, scan_type=None, scan_days=None):
    print_banner()
    
    if not validate_configuration():
        return
    
    print(f"\n📂 Loading queries from: {queries_file}\n")
    
    try:
        with open(queries_file, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ File not found: {queries_file}")
        return
    
    print(f"📋 Found {len(queries)} queries\n")
    
    agent = create_agent()
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*70}")
        print(f"Query {i}/{len(queries)}: {query}")
        print(f"{'='*70}")
        
        enriched_query = query
        if scan_type:
            enriched_query += f" [type:{scan_type}]"
        if scan_days:
            enriched_query += f" [days:{scan_days}]"
        elif "scan" in query.lower():
            enriched_query += f" [days:{settings.DEFAULT_DAYS_BACK}]"
        
        result = agent.invoke(enriched_query, verbose=True)
        results.append(result)
        
        print(f"\n🤖 Response: {result['response']}\n")
    
    print(f"\n{'='*70}")
    print("BATCH EXECUTION SUMMARY")
    print(f"{'='*70}")
    print(f"Total Queries: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r['success'])}")
    print(f"Failed: {sum(1 for r in results if not r['success'])}")
    print(f"Average Time: {sum(r['execution_time'] for r in results) / len(results):.2f}s")
    print(f"{'='*70}\n")


def print_help():
    help_text = """
    📚 Available Commands:
    
    💬 Chat Commands:
       - Just type your question naturally!
       - Examples:
         * "Show me all my upcoming bills"
         * "Scan my email for new bills"
         * "Scan for promotions from last week"
         * "Find university emails from last 3 months"
         * "What did I spend on utilities last month?"
    
    🛠️ System Commands:
       help            - Show this help message
       types           - Show all available email scan types
       history         - Show query history
       config          - Show current configuration
       setup           - Run configuration setup wizard
       reminders       - Show reminder scheduler status
       check-reminders - Manually trigger reminder check
       clear           - Clear screen
       exit/quit       - Exit the application
    
    📧 Email Scan Types:
       bills, promotions, discounts, orders, shipping,
       receipts, subscriptions, universities, tax,
       travel, insurance, banking
    
    💡 Tips:
       - Be specific in your queries for better results
       - You can ask follow-up questions
       - Use natural language for date ranges
       - Default scan period: {days} days (configurable in config.yaml)
    """.format(days=settings.DEFAULT_DAYS_BACK)
    print(help_text)


def print_history(history):
    if not history:
        print("\n📝 No history yet!")
        return
    
    print(f"\n📚 Query History ({len(history)} queries):\n")
    for i, item in enumerate(history[-10:], 1):
        print(f"{i}. [{item['timestamp']}] {item['query']}")


def list_email_types():
    print_banner()
    print(email_config.get_config_summary())
    print("\n💡 Use with: python main.py --scan-type <type> --query \"scan my email\"")


def show_config_info():
    """Show configuration file locations and status"""
    print_banner()
    print("\n📋 Configuration Information")
    print("="*70)
    
    config_file = Path(__file__).parent / "config.yaml"
    env_file = Path(__file__).parent / ".env"
    
    print("\n📁 Configuration Files:")
    print(f"   config.yaml: {config_file}")
    print(f"   Status: {'✅ Found' if config_file.exists() else '❌ Not found'}")
    print(f"\n   .env file: {env_file}")
    print(f"   Status: {'✅ Found' if env_file.exists() else '❌ Not found'}")
    
    print("\n⚙️  Configuration Priority:")
    print("   1. Session keys (set during runtime)")
    print("   2. .env file (recommended for security)")
    print("   3. config.yaml (convenient but less secure)")
    
    print("\n" + settings.get_config_summary())
    
    print("\n💡 To setup configuration: python main.py --setup")


def main():
    parser = argparse.ArgumentParser(
        description="Bill Tracker Agent - Intelligent Bill Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --setup
  python main.py --query "scan my email for bills"
  python main.py --scan-type promotions --days 7 --query "scan my email"
  python main.py --scan-type universities --days 90
  python main.py --batch queries.txt --scan-type orders
  python main.py --show-config
        """
    )
    
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="Run a single query and exit"
    )
    
    parser.add_argument(
        "-b", "--batch",
        type=str,
        help="Run queries from a file (one per line)"
    )
    
    parser.add_argument(
        "-u", "--user",
        type=str,
        default="default",
        help="User ID for personalization"
    )
    
    parser.add_argument(
        "-t", "--scan-type",
        type=str,
        choices=email_config.get_all_types(),
        help="Email scan type (bills, promotions, orders, etc.)"
    )
    
    parser.add_argument(
        "-d", "--days",
        type=int,
        help=f"Number of days to scan back (default: from config.yaml)"
    )
    
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="List all available email scan types"
    )
    
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive configuration setup wizard"
    )
    
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show configuration file locations and current settings"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and exit"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive API key prompts during validation"
    )
    
    args = parser.parse_args()
    
    # Handle special commands first
    if args.setup:
        setup_configuration()
        return
    
    if args.show_config:
        show_config_info()
        return
    
    if args.list_types:
        list_email_types()
        return
    
    if args.validate:
        print_banner()
        validate_configuration(interactive=args.interactive)
        return
    
    # Normal execution modes
    if args.query:
        single_query_mode(args.query, args.user, args.scan_type, args.days)
        return
    
    if args.batch:
        batch_mode(args.batch, args.scan_type, args.days)
        return
    
    # Default: Interactive mode
    interactive_mode(args.scan_type, args.days)


if __name__ == "__main__":
    main()