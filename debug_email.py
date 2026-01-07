"""
Debug script to find exactly where email_scanner_node fails
"""

import os
import sys
from datetime import datetime, timedelta

# Add detailed logging
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

print("="*70)
print("DEBUGGING EMAIL SCANNER NODE")
print("="*70)

# Test 1: Check if the tool returns success
print("\n1. Testing scan_emails tool directly...")
print("-"*70)

try:
    from src.agent.tools import scan_emails
    
    date_from = (datetime.now() - timedelta(days=30)).isoformat()[:10]
    date_to = datetime.now().isoformat()[:10]
    
    print(f"Calling scan_emails:")
    print(f"  date_from: {date_from}")
    print(f"  date_to: {date_to}")
    
    result = scan_emails.invoke({
        "date_from": date_from,
        "date_to": date_to,
        "keywords": ["invoice", "bill", "statement", "payment"],
        "max_results": 50
    })
    
    print(f"\nTool result:")
    print(f"  success: {result.get('success')}")
    print(f"  error: {result.get('error', 'None')}")
    print(f"  emails_found: {result.get('emails_found', 0)}")
    print(f"  files_downloaded: {result.get('files_downloaded', 0)}")
    print(f"  results count: {len(result.get('results', []))}")
    
    if not result.get('success'):
        print(f"\n❌ PROBLEM FOUND: Tool returning success=False")
        print(f"   Error message: {result.get('error')}")
        if 'error_details' in result:
            print(f"\n   Full error details:")
            print(result['error_details'])
    else:
        print(f"\n✅ Tool executed successfully")
        
except Exception as e:
    print(f"❌ Exception during tool call: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Simulate what the node does
print("\n" + "="*70)
print("2. Simulating email_scanner_node execution...")
print("-"*70)

try:
    from src.agent.state import create_initial_state
    from src.agent.nodes import email_scanner_node
    
    # Create test state
    state = create_initial_state("Scan my email for bills", "test_user")
    state["intent"] = "scan_bills"
    state["entities"] = {}
    state["plan"] = ["email_scanner", "pdf_processor", "data_extractor"]
    
    print("Initial state:")
    print(f"  plan: {state['plan']}")
    print(f"  completed_steps: {state['completed_steps']}")
    print(f"  errors: {state['errors']}")
    
    print("\nCalling email_scanner_node...")
    print("-"*70)
    
    # Add try-catch INSIDE to see exactly where it fails
    try:
        result_state = email_scanner_node(state)
        
        print("\n" + "-"*70)
        print("Node returned successfully")
        print(f"  completed_steps: {result_state['completed_steps']}")
        print(f"  errors: {result_state['errors']}")
        print(f"  tools_used: {result_state['tools_used']}")
        print(f"  downloaded_files: {len(result_state['downloaded_files'])}")
        
        if "email_scanner" in result_state['completed_steps']:
            print("\n✅ SUCCESS: Node marked itself as completed")
        else:
            print("\n❌ PROBLEM: Node did NOT mark itself as completed")
            print("   This is why you're getting infinite loop!")
            
            # Check why
            if result_state['errors']:
                print(f"\n   Errors found: {result_state['errors']}")
            else:
                print("\n   No errors logged - check if tool returned success=False")
                
    except Exception as e:
        print(f"\n❌ Exception inside email_scanner_node: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"❌ Failed to test node: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Check credentials
print("\n" + "="*70)
print("3. Checking Gmail API credentials...")
print("-"*70)

creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")

print(f"Credentials path: {creds_path}")
print(f"Token path: {token_path}")

if os.path.exists(creds_path):
    print(f"✅ Credentials file exists")
else:
    print(f"❌ Credentials file NOT FOUND")
    print(f"   This will cause authentication to fail")
    print(f"   Download from: https://console.cloud.google.com/apis/credentials")

if os.path.exists(token_path):
    print(f"✅ Token file exists")
    import os.path
    size = os.path.getsize(token_path)
    print(f"   Size: {size} bytes")
else:
    print(f"⚠️  Token file not found (will be created on first authentication)")

# Test 4: Check the actual node code
print("\n" + "="*70)
print("4. Checking email_scanner_node code...")
print("-"*70)

try:
    import inspect
    from src.agent.nodes import email_scanner_node
    
    source = inspect.getsource(email_scanner_node)
    
    # Check if it has the correct completion line
    if 'state["completed_steps"].append("email_scanner")' in source:
        print("✅ Node has correct completion line: append('email_scanner')")
    elif 'state["completed_steps"].append("email_scanning")' in source:
        print("❌ Node has OLD completion line: append('email_scanning')")
        print("   You need to apply the nodes_fixed.py file!")
    else:
        print("⚠️  Cannot find completion line in node code")
        
    # Check if completion is inside if success block
    lines = source.split('\n')
    for i, line in enumerate(lines):
        if 'if result.get("success")' in line:
            # Check next few lines
            for j in range(i, min(i+15, len(lines))):
                if 'completed_steps.append' in lines[j]:
                    print(f"✅ Completion line is inside success block (good)")
                    break
            break
            
except Exception as e:
    print(f"⚠️  Could not inspect node code: {e}")

# Test 5: Check should_continue logic
print("\n" + "="*70)
print("5. Testing should_continue logic...")
print("-"*70)

try:
    from src.agent.nodes import should_continue
    
    # Test scenario 1: email_scanner not completed
    test_state_1 = {
        "plan": ["email_scanner", "pdf_processor", "data_extractor"],
        "completed_steps": [],  # Nothing completed yet
        "errors": [],
        "retry_count": 0,
        "max_retries": 3
    }
    
    next_step_1 = should_continue(test_state_1)
    print(f"Scenario 1: No steps completed")
    print(f"  should_continue returns: '{next_step_1}'")
    if next_step_1 == "email_scanner":
        print(f"  ✅ Correct - returns first step")
    else:
        print(f"  ❌ Wrong - should return 'email_scanner'")
    
    # Test scenario 2: email_scanner completed
    test_state_2 = {
        "plan": ["email_scanner", "pdf_processor", "data_extractor"],
        "completed_steps": ["email_scanner"],  # email_scanner done
        "errors": [],
        "retry_count": 0,
        "max_retries": 3
    }
    
    next_step_2 = should_continue(test_state_2)
    print(f"\nScenario 2: email_scanner completed")
    print(f"  should_continue returns: '{next_step_2}'")
    if next_step_2 == "pdf_processor":
        print(f"  ✅ Correct - returns next step")
    elif next_step_2 == "email_scanner":
        print(f"  ❌ PROBLEM - returns email_scanner again (infinite loop!)")
    else:
        print(f"  ⚠️  Unexpected result")
        
except Exception as e:
    print(f"❌ Error testing should_continue: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)

print("\n📊 SUMMARY:")
print("-"*70)
print("The infinite loop happens when:")
print("1. email_scanner_node runs but doesn't mark itself as completed")
print("2. should_continue() sees 'email_scanner' not in completed_steps")
print("3. Returns 'email_scanner' again")
print("4. Loop repeats until recursion limit")
print("\nMost likely causes:")
print("A. scan_emails tool returning success=False")
print("B. Exception inside email_scanner_node")
print("C. Gmail authentication failing")
print("D. Using old nodes.py without the fix")
print("\nCheck the test results above to see which one it is!")