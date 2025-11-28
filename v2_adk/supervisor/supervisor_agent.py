from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import PythonTool

from v2_adk.supervisor.tools.discover_tool import discover_travel_app
from v2_adk.supervisor.tools.eval_tool import run_travel_eval
from v2_adk.supervisor.tools.metrics_tool import show_metrics
from v2_adk.supervisor.tools.planner_tool import propose_improvements
from v2_adk.supervisor.tools.compare_tool import compare_versions


supervisor_agent = Agent(
    name="proagentic_supervisor",
    model="gemini-2.0-flash",
    description="Supervisor that discovers, evaluates, and improves ADK apps.",
    instruction=(
        "You are the ProAgentic Supervisor for ADK applications.\n\n"
        "You can:\n"
        "- Discover the architecture and config of the travel planner app.\n"
        "- Run evaluations for travel_v1 and travel_v2.\n"
        "- Show metrics across versions.\n"
        "- Propose improvements (via planner + ChangeSet).\n"
        "- Compare configs between v1 and v2.\n\n"
        "When the user asks about the travel planner, decide which tools to call, "
        "then summarize what you found in clear, concise language."
    ),
    tools=[
        PythonTool(name="discover_travel_app", python_function=discover_travel_app),
        PythonTool(name="run_travel_eval", python_function=run_travel_eval),
        PythonTool(name="show_metrics", python_function=show_metrics),
        PythonTool(name="propose_improvements", python_function=propose_improvements),
        PythonTool(name="compare_versions", python_function=compare_versions),
    ],
)
