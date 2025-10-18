#!/usr/bin/env python3
"""
WebSocket Event System Consistency Checker

Validates consistency between:
1. Python event definitions (myagent/ws/events.py)
2. TypeScript type definitions (docs/ws-protocol/stable/EVENT_TYPES.ts)
3. Payload documentation (docs/ws-protocol/stable/EVENT_PAYLOADS_DETAILED.md)
4. Validation rules (docs/ws-protocol/stable/PAYLOAD_VALIDATION_GUIDE.md)
5. Show content display text (events.py _derive_show_content)

Usage:
    python tools/event_consistency_checker.py [--report] [--fix]

Options:
    --report    Generate detailed report (default)
    --fix       Suggest fixes for inconsistencies
    --verbose   Show all events (default shows only issues)
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple


@dataclass
class EventDef:
    """Event definition info"""
    name: str
    category: str  # user, plan, solver, agent, system, error
    in_python: bool = False
    in_typescript: bool = False
    in_payload_docs: bool = False
    in_validation: bool = False
    has_show_content: bool = False
    python_line: int = 0


class EventConsistencyChecker:
    """Check consistency across all event definition sources"""

    def __init__(self, project_root: Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = project_root
        self.events: Dict[str, EventDef] = {}
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def run(self) -> Tuple[int, List[str]]:
        """Run all consistency checks. Returns (issues_count, all_findings)"""
        self.findings = []

        print("🔍 Checking WebSocket Event System Consistency...\n")

        # Collect event definitions from all sources
        self._check_python_events()
        self._check_typescript_types()
        self._check_payload_docs()
        self._check_validation_rules()
        self._check_show_content()

        # Analyze consistency
        self._analyze_consistency()

        return len(self.issues), self.findings

    def _check_python_events(self):
        """Extract event definitions from events.py"""
        print("📝 Checking events.py definitions...")
        events_file = self.project_root / "myagent" / "ws" / "events.py"

        if not events_file.exists():
            self.issues.append(f"❌ events.py not found: {events_file}")
            return

        with open(events_file) as f:
            content = f.read()
            lines = content.split('\n')

        # Find all event class definitions and extract constants
        current_class = None
        for i, line in enumerate(lines, 1):
            # Detect event class (e.g., class UserEvents:)
            if re.match(r'class \w+Events:', line):
                match = re.match(r'class (\w+)Events:', line)
                current_class = match.group(1).lower()
                continue

            # Extract event constants (e.g., MESSAGE = "user.message")
            if current_class and re.match(r'\s+\w+ = "[^"]+"', line):
                match = re.match(r'\s+(\w+) = "([^"]+)"', line)
                if match:
                    var_name, event_name = match.groups()
                    if event_name not in self.events:
                        self.events[event_name] = EventDef(
                            name=event_name,
                            category=event_name.split('.')[0]
                        )
                    self.events[event_name].in_python = True
                    self.events[event_name].python_line = i

    def _check_typescript_types(self):
        """Check for TypeScript type definitions"""
        print("📘 Checking EVENT_TYPES.ts definitions...")
        ts_file = self.project_root / "docs" / "ws-protocol" / "stable" / "EVENT_TYPES.ts"

        if not ts_file.exists():
            self.warnings.append(f"⚠️  EVENT_TYPES.ts not found: {ts_file}")
            return

        with open(ts_file) as f:
            content = f.read()

        # Check for event interface definitions
        for event_name in self.events:
            # Convert event.name to EventName interface pattern
            parts = event_name.split('.')
            interface_pattern = ''.join(p.capitalize() for p in parts)

            if interface_pattern in content or f'event: "{event_name}"' in content:
                self.events[event_name].in_typescript = True
            else:
                self.events[event_name].in_typescript = False

    def _check_payload_docs(self):
        """Check for payload documentation"""
        print("📄 Checking EVENT_PAYLOADS_DETAILED.md...")
        docs_file = self.project_root / "docs" / "ws-protocol" / "stable" / "EVENT_PAYLOADS_DETAILED.md"

        if not docs_file.exists():
            self.warnings.append(f"⚠️  EVENT_PAYLOADS_DETAILED.md not found: {docs_file}")
            return

        with open(docs_file) as f:
            content = f.read()

        for event_name in self.events:
            # Check if event is mentioned with its full name
            if f'"{event_name}"' in content or f"`{event_name}`" in content:
                self.events[event_name].in_payload_docs = True

    def _check_validation_rules(self):
        """Check for validation rules"""
        print("✓ Checking PAYLOAD_VALIDATION_GUIDE.md...")
        val_file = self.project_root / "docs" / "ws-protocol" / "stable" / "PAYLOAD_VALIDATION_GUIDE.md"

        if not val_file.exists():
            self.warnings.append(f"⚠️  PAYLOAD_VALIDATION_GUIDE.md not found: {val_file}")
            return

        with open(val_file) as f:
            content = f.read()

        for event_name in self.events:
            if f'"{event_name}"' in content or f"`{event_name}`" in content:
                self.events[event_name].in_validation = True

    def _check_show_content(self):
        """Check for show_content display text"""
        print("💬 Checking show_content display text...")
        events_file = self.project_root / "myagent" / "ws" / "events.py"

        with open(events_file) as f:
            content = f.read()

        # Find _derive_show_content function
        if '_derive_show_content' in content:
            derive_func = content[content.find('def _derive_show_content'):content.find('\ndef create_event')]

            for event_name in self.events:
                # Check if event has a case in the switch/if statement
                if f'et == ' in derive_func:
                    # Look for patterns like: if et == "event.name":
                    pattern = rf'et == ["\']({re.escape(event_name)})["\']'
                    if re.search(pattern, derive_func):
                        self.events[event_name].has_show_content = True

    def _analyze_consistency(self):
        """Analyze and report consistency issues"""
        print("\n📊 Analysis Results:\n")

        # Group events by category
        by_category: Dict[str, List[EventDef]] = {}
        for event in self.events.values():
            if event.category not in by_category:
                by_category[event.category] = []
            by_category[event.category].append(event)

        # Check for inconsistencies
        critical_issues = []
        warnings = []

        for category in sorted(by_category.keys()):
            events_in_cat = by_category[category]
            print(f"\n## {category.upper()} Events ({len(events_in_cat)} total)")
            print("-" * 70)

            for event in sorted(events_in_cat, key=lambda e: e.name):
                status_parts = []

                # Check Python (must have)
                if not event.in_python:
                    status_parts.append("❌ NO PYTHON")
                    critical_issues.append(f"{event.name}: Missing from events.py")
                else:
                    status_parts.append("✅ Python")

                # Check TypeScript
                if event.in_typescript:
                    status_parts.append("✅ TypeScript")
                else:
                    status_parts.append("⚠️  NO TypeScript")
                    warnings.append(f"{event.name}: Missing TypeScript type definition")

                # Check Docs
                if event.in_payload_docs:
                    status_parts.append("✅ Docs")
                else:
                    status_parts.append("⚠️  NO Docs")
                    warnings.append(f"{event.name}: Missing from EVENT_PAYLOADS_DETAILED.md")

                # Check Validation
                if event.in_validation:
                    status_parts.append("✅ Valid")
                else:
                    status_parts.append("⚠️  NO Valid")
                    warnings.append(f"{event.name}: Missing validation rules")

                # Check Show Content
                if event.has_show_content:
                    status_parts.append("✅ Display")
                else:
                    status_parts.append("⚠️  NO Display")

                status_line = " | ".join(status_parts)
                print(f"  {event.name:30} {status_line}")

        # Summary statistics
        print("\n" + "=" * 70)
        print("📈 SUMMARY STATISTICS")
        print("=" * 70)

        total = len(self.events)
        python_coverage = sum(1 for e in self.events.values() if e.in_python)
        ts_coverage = sum(1 for e in self.events.values() if e.in_typescript)
        docs_coverage = sum(1 for e in self.events.values() if e.in_payload_docs)
        val_coverage = sum(1 for e in self.events.values() if e.in_validation)
        display_coverage = sum(1 for e in self.events.values() if e.has_show_content)

        print(f"\nTotal Events:           {total:3d}")
        print(f"Python Coverage:        {python_coverage:3d} / {total} ({100*python_coverage//total}%)")
        print(f"TypeScript Coverage:    {ts_coverage:3d} / {total} ({100*ts_coverage//total}%)")
        print(f"Documentation Coverage: {docs_coverage:3d} / {total} ({100*docs_coverage//total}%)")
        print(f"Validation Coverage:    {val_coverage:3d} / {total} ({100*val_coverage//total}%)")
        print(f"Display Text Coverage:  {display_coverage:3d} / {total} ({100*display_coverage//total}%)")

        # Report issues and warnings
        if critical_issues:
            print("\n" + "=" * 70)
            print("🚨 CRITICAL ISSUES (must fix)")
            print("=" * 70)
            for issue in critical_issues:
                print(f"  • {issue}")

        if warnings:
            print("\n" + "=" * 70)
            print("⚠️  WARNINGS (should address)")
            print("=" * 70)
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")

        if not critical_issues and not warnings:
            print("\n✅ All checks passed! Event system is fully consistent.")

        return len(critical_issues)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Check WebSocket event system consistency")
    parser.add_argument("--report", action="store_true", default=True, help="Generate report")
    parser.add_argument("--fix", action="store_true", help="Suggest fixes")
    parser.add_argument("--verbose", action="store_true", help="Show all events")

    args = parser.parse_args()

    checker = EventConsistencyChecker()
    issue_count, findings = checker.run()

    if issue_count > 0:
        print(f"\n❌ Found {issue_count} issues that need attention.")
        sys.exit(1)
    else:
        print("\n✅ All consistency checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
