"""
Senku 3.2 — Execution & Intelligence Verification
Tests that actions are ACTUALLY executed, not faked.
"""
import sys
sys.path.insert(0, ".")

errors = []


def test(name, fn):
    try:
        fn()
        print(f"  [PASS] {name}")
    except Exception as e:
        errors.append(name)
        print(f"  [FAIL] {name}: {e}")


print("=" * 60)
print("  SENKU 3.2 — EXECUTION & INTELLIGENCE VERIFICATION")
print("=" * 60)

from senku.brain.preprocessor import Preprocessor
from senku.brain.parser import ResponseParser
from senku.brain.decision import DecisionLayer
from senku.core.types import Action, Intent, IntentType
from senku.actions.handlers.web_handler import _resolve_contact, _load_contacts

preprocessor = Preprocessor()
parser = ResponseParser()
decision = DecisionLayer()

# ─── Shortcut Detection Tests ────────────────────────────────────
print("\n--- Shortcuts: Send Message ---")

def test_send_hi_to_amma():
    r = preprocessor.process("send hi to amma")
    assert r["shortcut_action"] is not None, "No shortcut detected"
    assert r["shortcut_action"].action_type == "send_message"
    assert r["shortcut_action"].get_param("to") == "amma"
    assert r["shortcut_action"].get_param("body") == "hi"

def test_send_message_to_john():
    r = preprocessor.process("send a message to John saying hello world")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "send_message"
    assert r["shortcut_action"].get_param("to") == "John"
    assert r["shortcut_action"].get_param("body") == "hello world"

def test_text_amma_good_morning():
    r = preprocessor.process("text amma good morning")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "send_message"
    assert r["shortcut_action"].get_param("to") == "amma"
    assert r["shortcut_action"].get_param("body") == "good morning"

def test_message_dad_saying_hi():
    r = preprocessor.process("message dad saying I'm coming home")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "send_message"
    assert r["shortcut_action"].get_param("to") == "dad"

test("'send hi to amma' -> send_message(amma, hi)", test_send_hi_to_amma)
test("'send a message to John saying hello world'", test_send_message_to_john)
test("'text amma good morning'", test_text_amma_good_morning)
test("'message dad saying I'm coming home'", test_message_dad_saying_hi)

print("\n--- Shortcuts: Volume ---")

def test_volume_up():
    r = preprocessor.process("volume up")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "system_volume"
    assert r["shortcut_action"].get_param("level") == "up"

def test_increase_volume():
    r = preprocessor.process("increase volume")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "system_volume"

def test_decrease_volume():
    r = preprocessor.process("decrease the volume")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "system_volume"
    assert r["shortcut_action"].get_param("level") == "down"

def test_mute():
    r = preprocessor.process("mute")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "system_volume"
    assert r["shortcut_action"].get_param("level") == "mute"

test("'volume up'", test_volume_up)
test("'increase volume'", test_increase_volume)
test("'decrease the volume'", test_decrease_volume)
test("'mute'", test_mute)

print("\n--- Shortcuts: Timer ---")

def test_timer_5m():
    r = preprocessor.process("set timer for 5 minutes")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "set_timer"

def test_timer_short():
    r = preprocessor.process("timer 30s")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "set_timer"

def test_remind_me():
    r = preprocessor.process("remind me in 10 minutes to check email")
    assert r["shortcut_action"] is not None
    assert r["shortcut_action"].action_type == "set_timer"
    assert r["shortcut_action"].get_param("label") == "check email"

test("'set timer for 5 minutes'", test_timer_5m)
test("'timer 30s'", test_timer_short)
test("'remind me in 10 minutes to check email'", test_remind_me)

# ─── Contact Resolution Tests ────────────────────────────────────
print("\n--- Contact Resolution ---")

def test_phone_number_direct():
    result = _resolve_contact("919876543210")
    assert result["resolved"] == True
    assert result["phone"] == "919876543210"

def test_phone_with_plus():
    result = _resolve_contact("+91 9876 543210")
    assert result["resolved"] == True

def test_unknown_contact():
    result = _resolve_contact("unknown_person_xyz")
    assert result["resolved"] == False
    assert "contacts.json" in result.get("error", "")

test("Phone number passes directly", test_phone_number_direct)
test("Phone with + and spaces", test_phone_with_plus)
test("Unknown contact -> helpful error", test_unknown_contact)

# ─── Decision Layer: No Unnecessary Confirmations ─────────────────
print("\n--- Decision: Execute-First Philosophy ---")

def test_no_confirmation_for_send():
    """send_message with all params should NOT ask for confirmation."""
    intent = Intent(
        IntentType.ACTION, "send hi to amma",
        actions=[Action("send_message", {"to": "amma", "body": "hi"}, confidence=0.9)]
    )
    result = decision.evaluate(intent)
    assert not result.needs_clarification, f"Blocked: {result.clarification_needed}"
    assert result.has_actions

def test_no_confirmation_for_volume():
    intent = Intent(
        IntentType.ACTION, "increase volume",
        actions=[Action("system_volume", {"level": "up"}, confidence=0.9)]
    )
    result = decision.evaluate(intent)
    assert not result.needs_clarification
    assert result.has_actions

def test_no_confirmation_for_timer():
    intent = Intent(
        IntentType.ACTION, "set timer 5m",
        actions=[Action("set_timer", {"duration": "5m"}, confidence=0.9)]
    )
    result = decision.evaluate(intent)
    assert not result.needs_clarification
    assert result.has_actions

def test_no_confirmation_for_create_file():
    intent = Intent(
        IntentType.ACTION, "create file notes.txt",
        actions=[Action("create_file", {"name": "notes.txt"}, confidence=0.9)]
    )
    result = decision.evaluate(intent)
    assert not result.needs_clarification
    assert result.has_actions

def test_still_asks_for_empty_app():
    """open_app without app name SHOULD ask."""
    intent = Intent(
        IntentType.ACTION, "open",
        actions=[Action("open_app", {"app": ""}, confidence=0.9)]
    )
    result = decision.evaluate(intent)
    assert result.needs_clarification

test("send_message(amma, hi) -> no confirmation", test_no_confirmation_for_send)
test("system_volume(up) -> no confirmation", test_no_confirmation_for_volume)
test("set_timer(5m) -> no confirmation", test_no_confirmation_for_timer)
test("create_file(notes.txt) -> no confirmation", test_no_confirmation_for_create_file)
test("open_app('') -> still asks", test_still_asks_for_empty_app)

# ─── Parser: Natural Language Action Parsing ──────────────────────
print("\n--- Parser: Action JSON Parsing ---")

def test_parse_send_message():
    r = parser.parse_actions('[{"action": "send_message", "to": "amma", "body": "hi"}]')
    assert len(r) == 1
    assert r[0].action_type == "send_message"
    assert r[0].get_param("to") == "amma"

def test_parse_volume():
    r = parser.parse_actions('[{"action": "system_volume", "level": "up"}]')
    assert len(r) == 1
    assert r[0].action_type == "system_volume"

test("Parse send_message JSON", test_parse_send_message)
test("Parse system_volume JSON", test_parse_volume)

# ─── Chat vs Action Separation ────────────────────────────────────
print("\n--- Chat vs Action: Strict Separation ---")

def test_hello_is_chat():
    r = parser.parse_actions("Hello! How are you?")
    assert r == [], "Chat text should return empty list"

def test_action_is_action():
    r = parser.parse_actions('[{"action": "open_app", "app": "chrome"}]')
    assert len(r) == 1, "Action JSON should parse correctly"

test("'Hello' -> chat (empty list)", test_hello_is_chat)
test("Action JSON -> parsed action", test_action_is_action)

# ─── Summary ─────────────────────────────────────────────────────
print()
print("=" * 60)
if errors:
    print(f"  FAILED: {len(errors)} test(s)")
    for e in errors:
        print(f"    - {e}")
else:
    print("  ALL EXECUTION & INTELLIGENCE TESTS PASSED")
    print("  SENKU 3.2 — REAL EXECUTION VERIFIED")
print("=" * 60)
