from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json


SYSTEM_PROMPT = """
You are a Formula 1 race strategist.

You are given a structured snapshot of the current race state.
Use ONLY the provided data.
Do NOT assume missing information.
Do NOT invent tyre performance numbers.
Do NOT mention safety cars unless explicitly present.

You MUST return ONLY valid JSON.
Do NOT include markdown.
Do NOT include explanations outside JSON.
Your jo right now is to give probabilities if the given drivers can compete each other in undercut and overcut and what is best for them.
In undercut - The chasing car pits first, gains a lap or two on new, faster tires while the leader is still on old, slower tires, and then passes the leader when the leader pits.
In overcut - The leading car stays out longer, running in clean air on lighter fuel, potentially doing faster laps on their older tires than the undercut car on fresh tires, then pits and comes out ahead.
Keep the reasoning concise and dont give blind probabilities without considering if any driver has recently pitted or not because if they have pitted recently then an undercut or overcut is already in play depending on the situation.
If uncertain, return conservative probabilities and confidence LOW.
"""

USER_PROMPT = """
Race snapshot:
{snapshot_json}

Drivers to compare:
{driver_list}

IMPORTANT:
You MUST choose actors ONLY from the drivers listed above.
Do NOT reference or select any other driver as an actor.
If neither driver is suitable, choose the more plausible one with LOW probability.

Return JSON with this exact schema:
{{
  "comparison": ["driverA", "driverB"],
  "prediction": {{
    "driver_pit_windows": {{
      "driverA": [lap_start, lap_end] | null,
      "driverB": [lap_start, lap_end] | null
    }},
    "undercut_probability": {{
      "actor": "driverA | driverB",
      "value": number (0 to 1)
    }},
    "overcut_probability": {{
      "actor": "driverA | driverB",
      "value": number (0 to 1)
    }}
  }},
  "reasoning": [string, string, ...],
  "confidence": "LOW | MEDIUM | HIGH"
}}
"""


class StrategyEngine:
    def __init__(self, model_name: str, temperature: float = 0.2):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])

    def predict(
        self,
        snapshot: Dict[str, Any],
        driver_numbers: List[int],
    ) -> Dict[str, Any]:
        snapshot_drivers = {d["driver_number"] for d in snapshot["drivers"]}
        for d in driver_numbers:
            if d not in snapshot_drivers:
                raise ValueError(f"Driver {d} not present in snapshot")

        messages = self.prompt.format_messages(
            snapshot_json=json.dumps(snapshot, indent=2),
            driver_list=[str(d) for d in driver_numbers],
        )
        current_lap = snapshot["session"]["lap"]
        response = self.llm.invoke(messages)
        return self._parse_and_validate(response.content, current_lap, driver_numbers)

    def _parse_and_validate(
        self,
        raw: str,
        curr_lap: int,
        driver_numbers: List[int],
    ) -> Dict[str, Any]:
        raw = raw.strip()

        if raw.startswith("```"):
            raw = raw.split("```", 1)[1]
            raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid JSON from model:\n{raw}")

        # ---- Schema validation ----
        for key in ("comparison", "prediction", "reasoning", "confidence"):
            if key not in data:
                raise RuntimeError(f"Missing key: {key}")

        pred = data["prediction"]

        # Validate driver_pit_windows
        dpw = pred.get("driver_pit_windows")
        if not isinstance(dpw, dict):
            raise RuntimeError("driver_pit_windows must be a dict")

        for d in map(str, driver_numbers):
            if d not in dpw:
                dpw[d] = None
            if dpw[d] is not None:
                if (
                    not isinstance(dpw[d], list)
                    or len(dpw[d]) != 2
                    or not all(isinstance(x, int) for x in dpw[d])
                ):
                    raise RuntimeError(f"Invalid pit window for driver {d}")

        # --- Dropping unknown keys ---
        allowed = set(map(str, driver_numbers))
        pred["driver_pit_windows"] = {
            k: v for k, v in pred["driver_pit_windows"].items()
            if k in allowed
        }


        # Validate undercut / overcut blocks
        for k in ("undercut_probability", "overcut_probability"):
            block = pred.get(k)
            if not block or "actor" not in block or "value" not in block:
                raise RuntimeError(f"Invalid {k} block")
            if block["actor"] not in list(map(str, driver_numbers)):
                raise RuntimeError(f"{k}.actor must be one of the compared drivers")
            if not (0.0 <= block["value"] <= 1.0):
                raise RuntimeError(f"{k}.value out of range")
        
        u = pred["undercut_probability"]["value"]
        o = pred["overcut_probability"]["value"]

        if u + o > 1.0:
            scale = 1.0/(u+o)
            pred["undercut_probability"]["value"] = round(u * scale, 2)
            pred["overcut_probability"]["value"] = round(o * scale, 2)


        if data["confidence"] not in ("LOW", "MEDIUM", "HIGH"):
            raise RuntimeError("Invalid confidence value")

        return data
