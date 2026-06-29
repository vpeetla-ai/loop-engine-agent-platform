from __future__ import annotations

from dataclasses import dataclass

from loop_engine.mcp.bridge import MCPBridge
from loop_engine.models.llm import LLM
from loop_engine.rag.retriever import Chunk
from loop_engine.tracing import Trace


@dataclass
class ReActLoop:
    llm: LLM
    mcp: MCPBridge
    max_steps: int = 4

    def run(self, goal: str, context: str, trace: Trace) -> tuple[str, list[Chunk]]:
        observation = context
        tool_names = ", ".join(self.mcp.list_tools())

        for step in range(1, self.max_steps + 1):
            system = f"""You are a ReAct agent inside a self-improving harness (step {step}/{self.max_steps}).
Tools: {tool_names}
Format:
THOUGHT: <one sentence>
ACTION: <tool_name> | FINISH
INPUT: <tool input or final answer if FINISH>"""
            user = f"GOAL:\n{goal}\n\nCONTEXT:\n{observation}"
            raw = self.llm.complete(system, user)
            trace.add("decide", "react.step", step=step, raw=raw)

            action, tool_input = "FINISH", goal
            for line in raw.splitlines():
                upper = line.strip().upper()
                if upper.startswith("ACTION:"):
                    action = line.split(":", 1)[1].strip().split("|")[0].strip()
                elif upper.startswith("INPUT:"):
                    tool_input = line.split(":", 1)[1].strip()

            if action.upper() == "FINISH":
                trace.add("act", "react.finish", step=step, answer=tool_input)
                return tool_input, []

            if action in self.mcp.tools:
                result = self.mcp.call(action, tool_input)
                trace.add("act", "mcp.tool", step=step, tool=action, result=result[:500])
                observation = f"Tool {action}:\n{result[:2000]}"
            else:
                observation = f"Unknown action {action}; try FINISH or a listed tool."

        return observation, []
