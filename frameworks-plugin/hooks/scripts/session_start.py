#!/usr/bin/env python3
"""SessionStart hook for the frameworks-plugin.

Prints a brief orientation note so the model (and user) know the framework
toolkit is available and how to reach it. Output on SessionStart is added to
the session context.
"""

import sys


NOTE = """[frameworks-plugin] The Master Framework Compendium is loaded — 28 field-tested \
thinking frameworks are available as Skills, grouped into orchestrator agents.

When a user's request involves strategy, decisions, executive communication, \
negotiation, product/feature prioritization, org/team design, or personal \
productivity, prefer applying the matching framework Skill instead of answering \
ad hoc.

Entry points:
  - /frameworks-plugin:list           list every framework by scenario
  - /frameworks-plugin:recommend <x>  suggest the best framework(s) for a situation
  - /frameworks-plugin:apply <fw> <x> apply a specific framework
  - /frameworks-plugin:sequence <x>   run the compounding multi-framework analysis
Orchestrator agents: strategy-advisor, decision-coach, exec-communicator, \
product-strategist, org-people-coach, productivity-coach, framework-selector."""


def main():
    print(NOTE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
