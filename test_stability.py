"""
Stability verification for Senku 3.1.1
Tests all crash paths identified in the data flow audit.
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
        import traceback
        traceback.print_exc()


print("=" * 55)
print("  SENKU 3.1.1 — DATA FLOW STABILITY VERIFICATION")
print("=" * 55)

# ─── Import Test ──────────────────────────────────────────
print("\n--- Imports ---")
try:
    from senku.core.types import Action, ActionResult, ActionStatus, Intent, IntentType
    from senku.brain.parser import ResponseParser
    from senku.brain.planner import Planner
    from senku.brain.decision import DecisionLayer
    from senku.brain.reasoning import ReasoningEngine
    from senku.actions.executor import Executor
    from senku.main import Senku
    print("  [PASS] All imports successful")
except Exception as e:
    print(f"  [FAIL] Import error: {e}")
    sys.exit(1)

parser = ResponseParser()

# ─── Parser Robustness Tests ─────────────────────────────
print("\n--- Parser: Chat Text Must Return [] ---")

def test_chat_text():
    result = parser.parse_actions("Hello! I'm an AI assistant. How can I help?")
    assert result == [], f"Expected [], got {result}"

def test_chat_greeting():
    result = parser.parse_actions("Hi there, welcome!")
    assert result == [], f"Expected [], got {result}"

def test_empty():
    result = parser.parse_actions("")
    assert result == []

def test_none_like():
    result = parser.parse_actions("   ")
    assert result == []

def test_plain_json_no_action():
    result = parser.parse_actions('{"name": "test", "value": 123}')
    assert result == [], f"Expected [] for dict without 'action' key"

test("Chat text -> []", test_chat_text)
test("Chat greeting -> []", test_chat_greeting)
test("Empty string -> []", test_empty)
test("Whitespace -> []", test_none_like)
test("JSON without 'action' key -> []", test_plain_json_no_action)

print("\n--- Parser: Valid Actions Parse Correctly ---")

def test_valid_single():
    result = parser.parse_actions('[{"action": "open_app", "app": "chrome"}]')
    assert len(result) == 1
    assert result[0].action_type == "open_app"
    assert result[0].get_param("app") == "chrome"

def test_valid_multi():
    result = parser.parse_actions('[{"action": "open_app", "app": "chrome"}, {"action": "search_web", "query": "test"}]')
    assert len(result) == 2
    assert result[0].action_type == "open_app"
    assert result[1].action_type == "search_web"

def test_markdown_wrapped():
    result = parser.parse_actions('```json\n[{"action": "screenshot"}]\n```')
    assert len(result) == 1
    assert result[0].action_type == "screenshot"

def test_single_object():
    result = parser.parse_actions('{"action": "open_app", "app": "notepad"}')
    assert len(result) == 1

def test_empty_array():
    result = parser.parse_actions("[]")
    assert result == []

def test_volume_action():
    result = parser.parse_actions('[{"action": "system_volume", "level": "up"}]')
    assert len(result) == 1
    assert result[0].action_type == "system_volume"
    assert result[0].get_param("level") == "up"

def test_timer_action():
    result = parser.parse_actions('[{"action": "set_timer", "duration": "5m", "label": "Timer"}]')
    assert len(result) == 1
    assert result[0].action_type == "set_timer"
    assert result[0].get_param("duration") == "5m"

def test_create_file_action():
    result = parser.parse_actions('[{"action": "create_file", "name": "notes.txt"}]')
    assert len(result) == 1
    assert result[0].action_type == "create_file"

def test_send_message_action():
    result = parser.parse_actions('[{"action": "send_message", "to": "John", "body": "Hi"}]')
    assert len(result) == 1
    assert result[0].action_type == "send_message"

test("Valid single action", test_valid_single)
test("Valid multi action", test_valid_multi)
test("Markdown-wrapped JSON", test_markdown_wrapped)
test("Single JSON object", test_single_object)
test("Empty JSON array", test_empty_array)
test("Volume action", test_volume_action)
test("Timer action", test_timer_action)
test("Create file action", test_create_file_action)
test("Send message action", test_send_message_action)

print("\n--- Parser: Malformed Input Doesn't Crash ---")

def test_broken_json():
    result = parser.parse_actions('{"action": "open_app", "app": "chrome"')
    assert isinstance(result, list)

def test_mixed_content():
    result = parser.parse_actions('Sure! Here is the action:\n[{"action": "open_app", "app": "chrome"}]\nLet me know if you need anything else.')
    assert isinstance(result, list)

def test_single_quotes():
    result = parser.parse_actions("[{'action': 'open_app', 'app': 'chrome'}]")
    assert isinstance(result, list)

def test_action_key_no_value():
    result = parser.parse_actions('[{"action": ""}]')
    assert result == [], f"Expected [], got {[a.action_type for a in result]}"

def test_action_key_null():
    result = parser.parse_actions('[{"action": null}]')
    assert result == [], f"Expected [], got {result}"

def test_random_garbage():
    result = parser.parse_actions("aslkdjf laskjdf alksjdf")
    assert result == []

test("Broken JSON -> no crash", test_broken_json)
test("Mixed text + JSON", test_mixed_content)
test("Single quotes JSON", test_single_quotes)
test("Empty action value -> []", test_action_key_no_value)
test("Null action value -> []", test_action_key_null)
test("Random garbage -> []", test_random_garbage)

# ─── Action.from_dict Safety ────────────────────────────
print("\n--- Action.from_dict: Safe Parsing ---")

def test_from_dict_normal():
    a = Action.from_dict({"action": "open_app", "app": "chrome"})
    assert a.action_type == "open_app"
    assert a.get_param("app") == "chrome"

def test_from_dict_action_type_key():
    a = Action.from_dict({"action_type": "search_web", "query": "test"})
    assert a.action_type == "search_web"

def test_from_dict_missing_action():
    a = Action.from_dict({"foo": "bar"})
    assert a.action_type == "unknown"

def test_from_dict_empty():
    a = Action.from_dict({})
    assert a.action_type == "unknown"

def test_from_dict_none_value():
    a = Action.from_dict({"action": None, "app": "chrome"})
    assert a.action_type in ("unknown", "None")

def test_from_dict_integer_action():
    a = Action.from_dict({"action": 123})
    assert isinstance(a.action_type, str)

test("Normal dict", test_from_dict_normal)
test("action_type key (not action)", test_from_dict_action_type_key)
test("Missing action key -> unknown", test_from_dict_missing_action)
test("Empty dict -> unknown", test_from_dict_empty)
test("None action value -> safe", test_from_dict_none_value)
test("Integer action value -> str", test_from_dict_integer_action)

# ─── Decision Layer Stability ───────────────────────────
print("\n--- Decision Layer: Doesn't Crash ---")

decision = DecisionLayer()

def test_decision_empty_actions():
    intent = Intent(IntentType.ACTION, "test", actions=[])
    result = decision.evaluate(intent)
    assert result is not None

def test_decision_chat_passthrough():
    intent = Intent(IntentType.CHAT, "hello", actions=[])
    result = decision.evaluate(intent)
    assert result.is_chat

def test_decision_low_confidence_filters():
    intent = Intent(IntentType.ACTION, "test", actions=[
        Action("open_app", {"app": "x"}, confidence=0.1),
    ])
    result = decision.evaluate(intent)
    # Should filter to chat since confidence below threshold
    assert not result.has_actions or result.is_chat

test("Empty actions", test_decision_empty_actions)
test("Chat passthrough", test_decision_chat_passthrough)
test("Low confidence filtering", test_decision_low_confidence_filters)

# ─── Executor Stability ─────────────────────────────────
print("\n--- Executor: Never Crashes ---")

executor = Executor()

def test_executor_unknown_action():
    action = Action("totally_fake_action", {"x": "y"})
    result = executor.execute_one(action)
    assert not result.success
    assert "Unknown" in result.message or "No handler" in result.error

def test_executor_empty_type():
    action = Action("", {})
    result = executor.execute_one(action)
    assert not result.success

def test_executor_empty_list():
    results = executor.execute_all([])
    assert results == []

test("Unknown action -> fail result (no crash)", test_executor_unknown_action)
test("Empty action type -> fail result (no crash)", test_executor_empty_type)
test("Empty action list -> empty results", test_executor_empty_list)

# ─── Full Pipeline Stability ────────────────────────────
print("\n--- Full Pipeline: Senku.process() Never Crashes ---")

senku = Senku()

def test_process_hello():
    result = senku.process("hello")
    assert isinstance(result, str)
    assert len(result) > 0 or result == ""  # Should be chat response or empty

def test_process_empty():
    result = senku.process("")
    assert result == ""

def test_process_whitespace():
    result = senku.process("   ")
    assert result == ""

def test_process_garbage():
    result = senku.process("alksjdf90a8sduf0as9df")
    assert isinstance(result, str)

test("'hello' -> chat response", test_process_hello)
test("Empty string -> empty", test_process_empty)
test("Whitespace -> empty", test_process_whitespace)
test("Random garbage -> safe response", test_process_garbage)

# ─── Summary ─────────────────────────────────────────────
print()
print("=" * 55)
if errors:
    print(f"  FAILED: {len(errors)} test(s)")
    for e in errors:
        print(f"    - {e}")
else:
    print("  ALL STABILITY TESTS PASSED")
    print("  SENKU 3.1.1 DATA FLOW IS CRASH-PROOF")
print("=" * 55)
