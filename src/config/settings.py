from dotenv import load_dotenv
import os
from pathlib import Path
import yaml
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import getpass

load_dotenv()

class Settings:
    """
    Multi-source configuration management.
    Priority: .env > config.yaml > runtime prompts
    """
    
    # Config file paths to check (in order)
    _config_paths = [
        Path.cwd() / "config.yaml",  # Current directory
        Path(__file__).parent.parent.parent / "config.yaml",  # Project root
        Path(__file__).parent / "config.yaml",  # Same dir as settings.py
    ]
    _config_file = None
    _config_data: Dict = {}
    _session_keys: Dict[str, str] = {}  # Runtime API keys
    _debug = os.getenv("CONFIG_DEBUG", "false").lower() == "true"
    
    @classmethod
    def _find_config_file(cls):
        """Find config.yaml in multiple locations"""
        for path in cls._config_paths:
            if path.exists():
                cls._config_file = path
                if cls._debug:
                    print(f"[DEBUG] Found config.yaml at: {path}")
                return path
        
        if cls._debug:
            print(f"[DEBUG] config.yaml not found. Searched:")
            for path in cls._config_paths:
                print(f"  - {path}")
        return None
    
    @classmethod
    def _load_yaml_config(cls):
        """Load configuration from YAML file"""
        if not cls._config_file:
            cls._find_config_file()
        
        if cls._config_file and cls._config_file.exists():
            try:
                with open(cls._config_file, 'r') as f:
                    cls._config_data = yaml.safe_load(f) or {}
                    if cls._debug:
                        print(f"[DEBUG] Loaded config.yaml: {len(cls._config_data)} top-level keys")
                    return True
            except Exception as e:
                print(f"⚠️  Warning: Could not load config.yaml: {e}")
                cls._config_data = {}
                return False
        else:
            if cls._debug:
                print(f"[DEBUG] No config.yaml found, using defaults")
            cls._config_data = {}
            return False
    
    @classmethod
    def _get_config_value(cls, *keys, default=None):
        """Navigate nested config dict safely"""
        value = cls._config_data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value
    
    @classmethod
    def set_session_api_key(cls, key_name: str, key_value: str):
        """Set API key for current session only"""
        cls._session_keys[key_name] = key_value
        print(f"✅ {key_name} set for this session")
    
    @classmethod
    def _get_api_key(cls, env_var: str, config_path: list, key_name: str) -> str:
        """
        Get API key with priority: session > .env > config.yaml
        """
        # 1. Check session keys (runtime)
        if key_name in cls._session_keys:
            return cls._session_keys[key_name]
        
        # 2. Check .env
        env_value = os.getenv(env_var, "")
        if env_value:
            return env_value
        
        # 3. Check config.yaml
        config_value = cls._get_config_value(*config_path, default="")
        if config_value:
            return config_value
        
        return ""
    
    @classmethod
    def prompt_for_api_key(cls, key_name: str, key_description: str) -> Optional[str]:
        """
        Interactive prompt for missing API key
        """
        print(f"\n⚠️  {key_name} not found!")
        print(f"   Required for: {key_description}")
        print("\nOptions:")
        print("  1) Enter key for this session only (not saved)")
        print("  2) Add to .env file (recommended - secure)")
        print("  3) Add to config.yaml (less secure)")
        print("  4) Skip (application may not work)")
        
        choice = input("\nChoice [1-4]: ").strip()
        
        if choice == "1":
            key = getpass.getpass(f"Enter {key_name}: ").strip()
            if key:
                cls.set_session_api_key(key_name, key)
                return key
        
        elif choice == "2":
            key = getpass.getpass(f"Enter {key_name}: ").strip()
            if key:
                cls._append_to_env_file(key_name, key)
                return key
        
        elif choice == "3":
            key = getpass.getpass(f"Enter {key_name}: ").strip()
            if key:
                cls._update_config_yaml(key_name, key)
                return key
        
        return None
    
    @classmethod
    def _append_to_env_file(cls, key_name: str, key_value: str):
        """Append API key to .env file"""
        env_path = Path(__file__).parent.parent.parent / ".env"
        try:
            with open(env_path, 'a') as f:
                f.write(f"\n{key_name}={key_value}\n")
            print(f"✅ {key_name} added to .env file")
            # Reload .env
            load_dotenv(override=True)
        except Exception as e:
            print(f"❌ Failed to write to .env: {e}")
    
    @classmethod
    def _update_config_yaml(cls, key_name: str, key_value: str):
        """Update API key in config.yaml"""
        if not cls._config_file:
            cls._find_config_file()
        
        if not cls._config_file:
            # Create in current directory if not found
            cls._config_file = Path.cwd() / "config.yaml"
            print(f"⚠️  config.yaml not found, creating at: {cls._config_file}")
            cls._config_data = {"api_keys": {}}
        
        if "api_keys" not in cls._config_data:
            cls._config_data["api_keys"] = {}
        
        # Convert OPENAI_API_KEY to openai_api_key for config
        yaml_key = key_name.lower()
        cls._config_data["api_keys"][yaml_key] = key_value
        
        try:
            with open(cls._config_file, 'w') as f:
                yaml.dump(cls._config_data, f, default_flow_style=False)
            print(f"✅ {key_name} added to config.yaml at {cls._config_file}")
        except Exception as e:
            print(f"❌ Failed to write to config.yaml: {e}")
    
    # ==================== Load Config ====================
    @classmethod
    def initialize(cls):
        """Initialize configuration from all sources"""
        cls._load_yaml_config()
    
    # ==================== LLM Configuration ====================
    
    @classmethod
    def get_openai_api_key(cls, interactive: bool = False) -> str:
        key = cls._get_api_key(
            "OPENAI_API_KEY",
            ["api_keys", "openai_api_key"],
            "OPENAI_API_KEY"
        )
        if not key and interactive:
            key = cls.prompt_for_api_key("OPENAI_API_KEY", "LLM completions and data extraction")
        return key or ""
    
    @property
    def OPENAI_API_KEY(self) -> str:
        return self.get_openai_api_key()
    
    @property
    def OPENAI_MODEL(self) -> str:
        return self._get_config_value("llm", "model", default="gpt-4.1-nano")
    
    @property
    def LLM_TEMPERATURE(self) -> float:
        return float(self._get_config_value("llm", "temperature", default=0.1))
    
    @property
    def LLM_MAX_TOKENS(self) -> int:
        return int(self._get_config_value("llm", "max_tokens", default=2000))
    
    # ==================== Embeddings Configuration ====================
    
    @classmethod
    def get_voyage_api_key(cls, interactive: bool = False) -> str:
        key = cls._get_api_key(
            "VOYAGE_API_KEY",
            ["api_keys", "voyage_api_key"],
            "VOYAGE_API_KEY"
        )
        if not key and interactive:
            key = cls.prompt_for_api_key("VOYAGE_API_KEY", "Vector embeddings and semantic search")
        return key or ""
    
    @property
    def VOYAGE_API_KEY(self) -> str:
        return self.get_voyage_api_key()
    
    @property
    def EMBEDDING_MODEL(self) -> str:
        return self._get_config_value("embeddings", "model", default="voyage-3-lite")
    
    # ==================== Email Configuration ====================
    
    @property
    def EMAIL_ADDRESS(self) -> str:
        # Priority: .env > config.yaml
        env_value = os.getenv("EMAIL_ADDRESS", "")
        if env_value:
            return env_value
        return self._get_config_value("credentials", "email_address", default="")
    
    @property
    def EMAIL_PASSWORD(self) -> str:
        # Priority: .env > config.yaml
        env_value = os.getenv("EMAIL_PASSWORD", "")
        if env_value:
            return env_value
        return self._get_config_value("credentials", "email_password", default="")
    
    @property
    def GMAIL_CREDENTIALS_PATH(self) -> str:
        return self._get_config_value("email", "gmail_credentials_path", default="credentials.json")
    
    @property
    def GMAIL_TOKEN_PATH(self) -> str:
        return self._get_config_value("email", "gmail_token_path", default="token.json")
    
    @property
    def SMTP_SERVER(self) -> str:
        return self._get_config_value("email", "smtp_server", default="smtp.gmail.com")
    
    @property
    def SMTP_PORT(self) -> int:
        return int(self._get_config_value("email", "smtp_port", default=587))
    
    @property
    def DEFAULT_EMAIL_SCAN_TYPE(self) -> str:
        return self._get_config_value("email", "default_scan_type", default="general")
    
    @property
    def EMAIL_SCAN_MAX_RESULTS(self) -> int:
        return int(self._get_config_value("scanning", "max_results", default=50))
    
    # ==================== Date/Time Configuration ====================
    
    @property
    def DEFAULT_DAYS_BACK(self) -> int:
        return int(self._get_config_value("scanning", "default_days_back", default=30))
    
    @property
    def DATE_FORMAT(self) -> str:
        return self._get_config_value("scanning", "date_format", default="YYYY-MM-DD")
    
    def get_default_date_from(self) -> str:
        """Get default start date based on configuration"""
        config_value = self._get_config_value("scanning", "default_date_from", default="auto")
        
        if config_value == "auto":
            date = datetime.now() - timedelta(days=self.DEFAULT_DAYS_BACK)
            return date.strftime("%Y-%m-%d")
        return config_value
    
    def get_default_date_to(self) -> str:
        """Get default end date based on configuration"""
        config_value = self._get_config_value("scanning", "default_date_to", default="today")
        
        if config_value == "today":
            return datetime.now().strftime("%Y-%m-%d")
        return config_value
    
    # ==================== Storage Configuration ====================
    
    @property
    def BASE_DIR(self) -> Path:
        base = self._get_config_value("storage", "base_dir", default="./data")
        return Path(__file__).parent.parent.parent / base
    
    @property
    def DATA_DIR(self) -> Path:
        return self.BASE_DIR
    
    @property
    def RAW_DATA_PATH(self) -> str:
        raw = self._get_config_value("storage", "raw_data", default="raw")
        return str(self.DATA_DIR / raw)
    
    @property
    def PROCESSED_DATA_PATH(self) -> str:
        processed = self._get_config_value("storage", "processed_data", default="processed")
        return str(self.DATA_DIR / processed)
    
    @property
    def VECTOR_STORE_PATH(self) -> str:
        vector = self._get_config_value("storage", "vector_store", default="vector_store")
        return str(self.DATA_DIR / vector)
    
    @classmethod
    def create_directories(cls):
        """Create all necessary directories"""
        instance = cls()
        os.makedirs(instance.RAW_DATA_PATH, exist_ok=True)
        os.makedirs(instance.PROCESSED_DATA_PATH, exist_ok=True)
        os.makedirs(instance.VECTOR_STORE_PATH, exist_ok=True)
    
    # ==================== Feature Flags ====================
    
    @property
    def ENABLE_EMAIL_SCANNING(self) -> bool:
        return bool(self._get_config_value("features", "enable_email_scanning", default=True))
    
    @property
    def ENABLE_RAG(self) -> bool:
        return bool(self._get_config_value("features", "enable_rag", default=True))
    
    @property
    def ENABLE_REMINDERS(self) -> bool:
        return bool(self._get_config_value("features", "enable_reminders", default=True))

    # ==================== Notification Configuration ====================

    @property
    def NOTIFICATION_CHANNEL(self) -> str:
        """Default notification channel: email, telegram, whatsapp, or console"""
        env_value = os.getenv("NOTIFICATION_CHANNEL", "")
        if env_value:
            return env_value
        return self._get_config_value("notifications", "default_channel", default="email")

    @property
    def REMINDER_CHECK_INTERVAL(self) -> int:
        """Interval in seconds between reminder checks (default: 300 = 5 min)"""
        env_value = os.getenv("REMINDER_CHECK_INTERVAL", "")
        if env_value:
            return int(env_value)
        return int(self._get_config_value("notifications", "check_interval", default=300))

    @property
    def DEFAULT_REMINDER_DAYS(self) -> list:
        """Default days before due date to send reminders"""
        return self._get_config_value("notifications", "reminder_days", default=[3, 1, 0])

    @property
    def REMINDER_DB_PATH(self) -> str:
        """Path to reminder SQLite database"""
        return str(self.DATA_DIR / "reminders.db")

    # Telegram Configuration
    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        env_value = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if env_value:
            return env_value
        return self._get_config_value("notifications", "telegram", "bot_token", default="")

    @property
    def TELEGRAM_CHAT_ID(self) -> str:
        env_value = os.getenv("TELEGRAM_CHAT_ID", "")
        if env_value:
            return env_value
        return self._get_config_value("notifications", "telegram", "chat_id", default="")

    # Twilio/WhatsApp Configuration
    @property
    def TWILIO_ACCOUNT_SID(self) -> str:
        env_value = os.getenv("TWILIO_ACCOUNT_SID", "")
        if env_value:
            return env_value
        return self._get_config_value("notifications", "twilio", "account_sid", default="")

    @property
    def TWILIO_AUTH_TOKEN(self) -> str:
        env_value = os.getenv("TWILIO_AUTH_TOKEN", "")
        if env_value:
            return env_value
        return self._get_config_value("notifications", "twilio", "auth_token", default="")

    @property
    def TWILIO_WHATSAPP_FROM(self) -> str:
        env_value = os.getenv("TWILIO_WHATSAPP_FROM", "")
        if env_value:
            return env_value
        return self._get_config_value("notifications", "twilio", "whatsapp_from", default="")

    @property
    def TWILIO_WHATSAPP_TO(self) -> str:
        env_value = os.getenv("TWILIO_WHATSAPP_TO", "")
        if env_value:
            return env_value
        return self._get_config_value("notifications", "twilio", "whatsapp_to", default="")

    # ==================== Validation ====================
    
    @classmethod
    def validate(cls, interactive: bool = False) -> Tuple[bool, list[str]]:
        """
        Validate configuration with optional interactive prompts
        """
        instance = cls()
        errors = []
        
        # Check OpenAI API Key
        openai_key = cls.get_openai_api_key(interactive=interactive)
        if not openai_key:
            errors.append("OPENAI_API_KEY is not set")
        
        # Check Voyage API Key
        voyage_key = cls.get_voyage_api_key(interactive=interactive)
        if not voyage_key:
            errors.append("VOYAGE_API_KEY is not set")
        
        # Check Gmail credentials if email scanning enabled
        if instance.ENABLE_EMAIL_SCANNING and not os.path.exists(instance.GMAIL_CREDENTIALS_PATH):
            errors.append(f"Gmail credentials not found: {instance.GMAIL_CREDENTIALS_PATH}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_config_summary(cls) -> str:
        """Get a summary of current configuration"""
        instance = cls()
        
        summary = "📋 Bill Tracker Agent Configuration:\n"
        summary += "="*60 + "\n"
        summary += f"  LLM: {instance.OPENAI_MODEL} (temp: {instance.LLM_TEMPERATURE})\n"
        summary += f"  Embeddings: {instance.EMBEDDING_MODEL}\n"
        summary += f"  Storage: {instance.VECTOR_STORE_PATH}\n"
        summary += f"  Default Scan: {instance.DEFAULT_DAYS_BACK} days back\n"
        summary += f"  Date Format: {instance.DATE_FORMAT}\n"
        summary += f"  Max Results: {instance.EMAIL_SCAN_MAX_RESULTS}\n"
        summary += "="*60 + "\n"
        summary += "  Features:\n"
        summary += f"    Email Scanning: {'✅' if instance.ENABLE_EMAIL_SCANNING else '❌'}\n"
        summary += f"    RAG Search: {'✅' if instance.ENABLE_RAG else '❌'}\n"
        summary += f"    Reminders: {'✅' if instance.ENABLE_REMINDERS else '❌'}\n"
        summary += "="*60 + "\n"
        summary += "  Notifications:\n"
        summary += f"    Default Channel: {instance.NOTIFICATION_CHANNEL}\n"
        summary += f"    Check Interval: {instance.REMINDER_CHECK_INTERVAL}s\n"
        summary += f"    Telegram: {'✅ Configured' if instance.TELEGRAM_BOT_TOKEN else '❌ Not configured'}\n"
        summary += f"    WhatsApp: {'✅ Configured' if instance.TWILIO_ACCOUNT_SID else '❌ Not configured'}\n"
        summary += "="*60

        return summary


Settings.initialize()

settings = Settings()
settings.create_directories()