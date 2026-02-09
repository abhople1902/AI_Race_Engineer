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
If uncertain, return conservative probabilities and confidence LOW.
"""

USER_PROMPT = """
Race snapshot:
{snapshot_json}

Drivers to compare:
{driver_list}

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

        response = self.llm.invoke(messages)
        return self._parse_and_validate(response.content, driver_numbers)

    def _parse_and_validate(
        self,
        raw: str,
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

        # Validate undercut / overcut blocks
        for k in ("undercut_probability", "overcut_probability"):
            block = pred.get(k)
            if not block or "actor" not in block or "value" not in block:
                raise RuntimeError(f"Invalid {k} block")
            if block["actor"] not in list(map(str, driver_numbers)):
                raise RuntimeError(f"{k}.actor must be one of the compared drivers")
            if not (0.0 <= block["value"] <= 1.0):
                raise RuntimeError(f"{k}.value out of range")

        if data["confidence"] not in ("LOW", "MEDIUM", "HIGH"):
            raise RuntimeError("Invalid confidence value")

        return data
