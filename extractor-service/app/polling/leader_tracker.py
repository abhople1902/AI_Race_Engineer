def get_leader_lap_number(laps_data: list) -> int:
    if not laps_data:
        return None
    leader_laps = [lap for lap in laps_data if lap.get("position") == 1]
    if leader_laps:
        return leader_laps[-1]["lap_number"]
    return None
