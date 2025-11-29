"""Automatic instrumentation example.

This example demonstrates:
1. Using InstrumentedInterpreter for zero-code observability
2. Automatic collection of framework metrics
3. Wrapping any interpreter with instrumentation
4. Comparing metrics with and without instrumentation

Run this example:
    docker compose -f docker/docker-compose.yml exec effectful poetry run python examples/10_auto_instrumentation.py

SSoT References:
    - documents/core/observability_doctrine.md - Dual-layer metrics architecture
    - effectful/observability/instrumentation.py - InstrumentedInterpreter implementation
    - effectful/observability/framework_metrics.py - FRAMEWORK_METRICS registry
"""

import asyncio
from collections.abc import Generator
from uuid import UUID, uuid4

from effectful.adapters.in_memory_metrics import InMemoryMetricsCollector
from effectful.domain.user import User
from effectful.effects.database import GetUserById
from effectful.effects.system import GetCurrentTime
from effectful.effects.websocket import SendText
from effectful.interpreters.composite import CompositeInterpreter
from effectful.interpreters.database import DatabaseInterpreter
from effectful.interpreters.system import SystemInterpreter
from effectful.interpreters.websocket import WebSocketInterpreter
from effectful.observability.framework_metrics import FRAMEWORK_METRICS
from effectful.observability.instrumentation import create_instrumented_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_program
from effectful.testing import unwrap_ok
from effectful.testing.fake_db import FakeUserRepository
from effectful.testing.fake_websocket import FakeWebSocketConnection


# === Effect Programs ===


def greet_user_program(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Simple effect program that uses multiple effect types.

    This program demonstrates automatic framework metrics collection:
    - effectful_effects_total incremented for each effect
    - effectful_effect_duration_seconds observed for each effect
    - Metrics labeled by effect_type (GetUserById, GetCurrentTime, SendText)
    """
    # Effect 1: Database query
    user = yield GetUserById(user_id=user_id)
    assert isinstance(user, User)

    # Effect 2: System call
    timestamp = yield GetCurrentTime()

    # Effect 3: WebSocket message
    message = f"Hello {user.name}! Current time: {timestamp}"
    yield SendText(text=message)

    return message


# === Main Program ===


async def main() -> None:
    """Main program demonstrating automatic instrumentation."""
    print("=" * 60)
    print("Automatic Instrumentation Example")
    print("=" * 60)
    print()

    # Setup test data
    test_user_id = uuid4()
    test_user = User(id=test_user_id, email="alice@example.com", name="Alice")
    fake_repo = FakeUserRepository()
    fake_repo.add_user(test_user)
    fake_ws = FakeWebSocketConnection()

    # Create base interpreters
    db_interp = DatabaseInterpreter(user_repo=fake_repo)
    system_interp = SystemInterpreter()
    ws_interp = WebSocketInterpreter(websocket=fake_ws)

    # === Part 1: WITHOUT Instrumentation ===
    print("=" * 60)
    print("Part 1: Running WITHOUT Instrumentation")
    print("=" * 60)
    print()

    # Create composite interpreter WITHOUT instrumentation
    base_interpreter = CompositeInterpreter(
        interpreters=[db_interp, system_interp, ws_interp]
    )

    print("Running effect program...")
    program1 = greet_user_program(test_user_id)
    result1 = await run_program(program1, base_interpreter)
    message1 = unwrap_ok(result1)
    print(f"Result: {message1}")
    print()
    print("✅ Program completed successfully")
    print("❌ No framework metrics collected (no instrumentation)")
    print()

    # === Part 2: WITH Instrumentation ===
    print("=" * 60)
    print("Part 2: Running WITH Instrumentation")
    print("=" * 60)
    print()

    # Create metrics collector
    print("📊 Setting up PrometheusMetricsCollector...")
    collector = InMemoryMetricsCollector()

    # Register framework metrics
    print("📝 Registering FRAMEWORK_METRICS...")
    registration_result = collector.register_metrics(FRAMEWORK_METRICS)
    match registration_result:
        case {"registered_count": count}:
            print(f"✅ Registered {count} framework metrics:")
            print("   • effectful_effects_total (counter)")
            print("   • effectful_effect_duration_seconds (histogram)")
        case {"reason": reason}:
            print(f"❌ Failed to register metrics: {reason}")
            return

    print()

    # Wrap each interpreter with instrumentation
    print("🔧 Wrapping interpreters with instrumentation...")
    instrumented_db = create_instrumented_interpreter(
        wrapped=db_interp, metrics_collector=collector
    )
    instrumented_system = create_instrumented_interpreter(
        wrapped=system_interp, metrics_collector=collector
    )
    instrumented_ws = create_instrumented_interpreter(
        wrapped=ws_interp, metrics_collector=collector
    )

    # Create composite interpreter with instrumented interpreters
    instrumented_interpreter = CompositeInterpreter(
        interpreters=[instrumented_db, instrumented_system, instrumented_ws]
    )

    print("✅ Interpreters wrapped with InstrumentedInterpreter")
    print()

    # Run program with instrumentation
    print("Running effect program with instrumentation...")
    program2 = greet_user_program(test_user_id)
    result2 = await run_program(program2, instrumented_interpreter)
    message2 = unwrap_ok(result2)
    print(f"Result: {message2}")
    print()
    print("✅ Program completed successfully")
    print("✅ Framework metrics collected automatically!")
    print()

    # === Part 3: Analyze Collected Metrics ===
    print("=" * 60)
    print("Part 3: Framework Metrics Analysis")
    print("=" * 60)
    print()

    # Count total effect executions
    counter_metrics = [
        m
        for m in collector._metrics.values()
        if m["name"] == "effectful_effects_total" and m["type"] == "counter"
    ]

    print(f"📊 Effect Execution Counts (effectful_effects_total):")
    print("-" * 60)
    for metric in sorted(counter_metrics, key=lambda m: m["labels"].get("effect_type", "")):
        effect_type = metric["labels"].get("effect_type", "unknown")
        result = metric["labels"].get("result", "unknown")
        count = metric["value"]
        icon = "✅" if result == "ok" else "❌"
        print(f"  {icon} {effect_type} [{result}]: {int(count)} executions")

    print()

    # Analyze effect durations
    histogram_metrics = [
        m
        for m in collector._metrics.values()
        if m["name"] == "effectful_effect_duration_seconds" and m["type"] == "histogram"
    ]

    print(f"📊 Effect Durations (effectful_effect_duration_seconds):")
    print("-" * 60)
    for metric in sorted(histogram_metrics, key=lambda m: m["labels"].get("effect_type", "")):
        effect_type = metric["labels"].get("effect_type", "unknown")
        observations = metric["value"].get("observations", [])
        if observations:
            avg_duration = sum(observations) / len(observations)
            min_duration = min(observations)
            max_duration = max(observations)
            print(f"  {effect_type}:")
            print(f"    Observations: {len(observations)}")
            print(f"    Avg: {avg_duration*1000:.2f}ms")
            print(f"    Min: {min_duration*1000:.2f}ms")
            print(f"    Max: {max_duration*1000:.2f}ms")

    print()

    # === Part 4: Multiple Program Executions ===
    print("=" * 60)
    print("Part 4: Running Multiple Programs")
    print("=" * 60)
    print()

    print("Running 10 more program executions...")
    for i in range(10):
        program = greet_user_program(test_user_id)
        result = await run_program(program, instrumented_interpreter)
        unwrap_ok(result)

    print("✅ Completed 10 additional executions")
    print()

    # Show updated metrics
    print("📊 Updated Metrics:")
    print("-" * 60)

    counter_metrics = [
        m
        for m in collector._metrics.values()
        if m["name"] == "effectful_effects_total" and m["type"] == "counter"
    ]

    total_effects = sum(m["value"] for m in counter_metrics)
    print(f"Total effect executions: {int(total_effects)}")
    print()

    for metric in sorted(counter_metrics, key=lambda m: (m["labels"].get("effect_type", ""), m["labels"].get("result", ""))):
        effect_type = metric["labels"].get("effect_type", "unknown")
        result = metric["labels"].get("result", "unknown")
        count = metric["value"]
        percentage = (count / total_effects) * 100
        print(f"  {effect_type} [{result}]: {int(count)} ({percentage:.1f}%)")

    print()

    # === Summary ===
    print("=" * 60)
    print("✅ Automatic instrumentation example complete!")
    print()
    print("Key Takeaways:")
    print("  • InstrumentedInterpreter provides zero-code observability")
    print("  • Wraps any interpreter implementing the Interpreter protocol")
    print("  • Automatically collects framework metrics:")
    print("    - effectful_effects_total (execution counts)")
    print("    - effectful_effect_duration_seconds (latency)")
    print("  • Fire-and-forget pattern (metrics don't block execution)")
    print("  • No changes needed to effect programs or business logic")
    print()
    print("Production Usage:")
    print("  1. Register FRAMEWORK_METRICS on PrometheusMetricsCollector")
    print("  2. Wrap interpreters with create_instrumented_interpreter()")
    print("  3. Expose /metrics endpoint for Prometheus scraping")
    print("  4. View metrics in Grafana dashboards")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
