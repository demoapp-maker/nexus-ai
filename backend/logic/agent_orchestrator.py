from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from logic.ai_service import ai_service
from logic.memory_manager import memory_manager


class AgentOrchestrator:
    """Bounded research and planning workflows built on the shared AI service."""

    def __init__(self) -> None:
        self.max_iterations = 6
        self.tools = self._get_available_tools()

    def _planner_model(self) -> str:
        config = ai_service._load_runtime_config()
        configured = str(config.get("model") or "auto")
        if configured in {"", "auto", "openrouter/free"}:
            return ai_service.get_fallback_chain(configured or "auto")[0]
        return configured

    @staticmethod
    def _parse_json_object(value: Optional[str], fallback: Dict[str, Any]) -> Dict[str, Any]:
        if not value:
            return fallback
        cleaned = value.strip()
        if "```" in cleaned:
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            cleaned = cleaned.removeprefix("json").strip()
        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else fallback
        except (TypeError, ValueError):
            return fallback

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information on a topic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "maxLength": 500},
                            "num_results": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "research_topic",
                    "description": "Perform bounded research on a topic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "maxLength": 500},
                            "depth": {"type": "string", "enum": ["shallow", "deep"]},
                        },
                        "required": ["topic"],
                    },
                },
            },
        ]

    async def _call_model(self, prompt: str, system_prompt: str) -> Optional[str]:
        return await asyncio.to_thread(
            ai_service.call_ai,
            prompt,
            system_prompt=system_prompt,
            model=self._planner_model(),
        )

    async def autonomous_research(
        self, query: str, session_id: str = "default"
    ) -> Dict[str, Any]:
        query = query.strip()[:2_000]
        if not query:
            return {"error": "Research query cannot be empty"}

        plan_prompt = f"""
You are a research planner. Create a bounded plan to research: {query!r}
Return JSON with objectives, search_queries, and expected_outcomes.
Use no more than five search queries.
"""
        plan = self._parse_json_object(
            await self._call_model(plan_prompt, "You are an expert research planner."),
            {
                "objectives": [f"Research {query}"],
                "search_queries": [query],
                "expected_outcomes": ["A source-backed summary"],
            },
        )
        plan["search_queries"] = [
            str(item)[:500] for item in (plan.get("search_queries") or [query])[:5]
        ]

        findings: List[Dict[str, Any]] = []
        iterations_used = 0
        for iteration in range(self.max_iterations):
            iterations_used = iteration + 1
            action_prompt = f"""
Based on this plan and the latest findings, choose the next action.
Plan: {json.dumps(plan, ensure_ascii=False)}
Findings: {json.dumps(findings[-3:], ensure_ascii=False)}
Return JSON: {{"action":"search|research|complete", "parameters":{{}}}}
"""
            action = self._parse_json_object(
                await self._call_model(
                    action_prompt,
                    "You are a bounded research executor. Return only JSON.",
                ),
                {"action": "complete", "parameters": {}},
            )
            action_name = str(action.get("action") or "complete").lower()
            parameters = action.get("parameters")
            if not isinstance(parameters, dict):
                parameters = {}

            if action_name == "complete":
                break
            if action_name == "search":
                try:
                    num_results = max(1, min(int(parameters.get("num_results", 5)), 10))
                except (TypeError, ValueError):
                    num_results = 5
                tool_call = {
                    "function": {
                        "name": "web_search",
                        "arguments": json.dumps(
                            {
                                "query": str(parameters.get("query") or query)[:500],
                                "num_results": num_results,
                            }
                        ),
                    }
                }
                result = await ai_service.execute_tool_call(tool_call)
                findings.append(
                    {
                        "iteration": iteration,
                        "action": "search",
                        "query": parameters.get("query") or query,
                        "result": result,
                    }
                )
            elif action_name == "research":
                tool_call = {
                    "function": {
                        "name": "research_topic",
                        "arguments": json.dumps(
                            {
                                "topic": str(parameters.get("topic") or query)[:500],
                                "depth": str(parameters.get("depth") or "shallow"),
                            }
                        ),
                    }
                }
                result = await ai_service.execute_tool_call(tool_call)
                findings.append(
                    {
                        "iteration": iteration,
                        "action": "research",
                        "topic": parameters.get("topic") or query,
                        "result": result,
                    }
                )
            else:
                break

        synthesis_prompt = f"""
Create a concise source-backed report about {query!r}.
Plan: {json.dumps(plan, ensure_ascii=False)}
Findings: {json.dumps(findings, ensure_ascii=False)}
Include executive summary, key findings, caveats, and source URLs.
"""
        final_report = await self._call_model(
            synthesis_prompt,
            "You are an expert researcher. Do not invent sources.",
        )
        final_report = final_report or "Research completed but synthesis was unavailable."
        memory_manager.mira_store(
            f"[research]\nQuery: {query}\nReport: {final_report[:20_000]}",
            room=memory_manager.session_room(session_id),
        )
        return {
            "query": query,
            "plan": plan,
            "findings": findings,
            "final_report": final_report,
            "iterations_used": iterations_used,
        }

    async def task_planning(self, goal: str) -> Dict[str, Any]:
        goal = goal.strip()[:2_000]
        if not goal:
            return {"error": "Task goal cannot be empty"}
        planning_prompt = f"""
Goal: {goal}
Return JSON with steps, resources_needed, and risks.
Each step must contain step_number, action, tool_needed, and success_criteria.
"""
        parsed = self._parse_json_object(
            await self._call_model(
                planning_prompt,
                "You are an expert task planner. Return only JSON.",
            ),
            {},
        )
        if not parsed:
            return {"error": "Failed to parse task plan"}
        return parsed
