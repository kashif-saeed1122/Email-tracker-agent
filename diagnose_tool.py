#!/usr/bin/env python3
"""
Configuration Diagnostic Tool
Run this to troubleshoot configuration issues
"""

import sys
from pathlib import Path
import os

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("CONFIGURATION DIAGNOSTIC TOOL")
print("="*70)

# Check 1: Python environment
print("\n1. Python Environment:")
print(f"   Python version: {sys.version.split()[0]}")
print(f"   Working directory: {Path.cwd()}")

# Check 2: File locations
print("\n2. File Locations:")
config_paths = [
    Path.cwd() / "config.yaml",
    Path(__file__).parent / "config.yaml",
    Path.cwd() / ".env",
]

for path in config_paths:
    exists = "✅" if path.exists() else "❌"
    print(f"   {exists} {path}")

# Check 3: PyYAML
print("\n3. Dependencies:")
try:
    import yaml
    print(f"   ✅ PyYAML installed (version: {yaml.__version__})")
except ImportError:
    print(f"   ❌ PyYAML NOT installed - run: pip install PyYAML")

# Check 4: Load config.yaml
print("\n4. Loading config.yaml:")
config_file = None
for path in [Path.cwd() / "config.yaml", Path(__file__).parent / "config.yaml"]:
    if path.exists():
        config_file = path
        break

if config_file:
    print(f"   Found at: {config_file}")
    try:
        import yaml
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        print(f"   ✅ Valid YAML syntax")
        print(f"   Top-level keys: {list(data.keys())}")
        
        # Check API keys
        if "api_keys" in data:
            print(f"\n   API Keys section:")
            for key, value in data["api_keys"].items():
                has_value = "✅ SET" if value and value.strip() else "❌ EMPTY"
                masked = f"****{value[-4:]}" if value and len(value) > 4 else "(empty)"
                print(f"     {key}: {has_value} {masked}")
        
        # Check credentials
        if "credentials" in data:
            print(f"\n   Credentials section:")
            for key, value in data["credentials"].items():
                has_value = "✅ SET" if value and value.strip() else "❌ EMPTY"
                masked = f"****{value[-4:]}" if value and len(value) > 4 else "(empty)"
                print(f"     {key}: {has_value} {masked}")
                
    except Exception as e:
        print(f"   ❌ Error loading: {e}")
else:
    print(f"   ❌ config.yaml not found")

# Check 5: Load .env
print("\n5. Loading .env:")
env_file = Path.cwd() / ".env"
if env_file.exists():
    print(f"   Found at: {env_file}")
    from dotenv import load_dotenv
    load_dotenv()
    
    keys_to_check = [
        "OPENAI_API_KEY",
        "VOYAGE_API_KEY",
        "EMAIL_ADDRESS",
        "EMAIL_PASSWORD"
    ]
    
    for key in keys_to_check:
        value = os.getenv(key, "")
        has_value = "✅ SET" if value else "❌ EMPTY"
        masked = f"****{value[-4:]}" if value and len(value) > 4 else "(empty)"
        print(f"     {key}: {has_value} {masked}")
else:
    print(f"   ❌ .env file not found")

# Check 6: Try importing settings
print("\n6. Testing Settings Import:")
try:
    # Enable debug mode temporarily
    os.environ["CONFIG_DEBUG"] = "true"
    from src.config.settings import Settings
    
    print(f"   ✅ Settings imported successfully")
    
    # Test API key loading
    print(f"\n   Testing API key loading:")
    openai_key = Settings.get_openai_api_key()
    voyage_key = Settings.get_voyage_api_key()
    
    print(f"     OPENAI_API_KEY: {'✅ Found' if openai_key else '❌ Not found'}")
    print(f"     VOYAGE_API_KEY: {'✅ Found' if voyage_key else '❌ Not found'}")
    
    # Test email loading
    instance = Settings()
    print(f"     EMAIL_ADDRESS: {'✅ Found' if instance.EMAIL_ADDRESS else '❌ Not found'}")
    print(f"     EMAIL_PASSWORD: {'✅ Found' if instance.EMAIL_PASSWORD else '❌ Not found'}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)
print("\nRecommendations:")
print("1. If PyYAML is missing: pip install PyYAML")
print("2. If config.yaml not found: Copy it to project root")
print("3. If API keys empty: Set them in .env (recommended) or config.yaml")
print("4. Run setup wizard: python main.py --setup")
print("="*70)