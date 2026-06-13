from curl_cffi import requests
import re
from html import unescape


def run(headers, user_input):
    """Read ADLs (Activities of Daily Living) and IADLs for a client."""
    client_id = user_input.get("client_id")
    if not client_id:
        return {"status_code": 400, "body": {"error": "client_id is required"}}

    adl_type = user_input.get("type", "1")  # 1=ADLs, 2=IADLs

    response = _fetch_activities_panel(headers, client_id, adl_type)

    if response.status_code == 302 or "login" in response.url:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if response.status_code != 200:
        return {"status_code": response.status_code, "body": {"error": "Failed to fetch ADLs"}}

    html = response.text

    if "login" in html.lower()[:500] and "password" in html.lower()[:1000]:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    # Parse activities from the activities_panel endpoint
    # Structure: <li class="activity selected" data-life_activity="ID">
    #   <div class="name_desc"><div class="name">...</div><div class="desc">...</div></div>
    #   <div class="panel"><div class="contents"><div class="activity_settings">
    #     <form class="need_level">... radio buttons ...</form>
    #     <ul class="tasks">... task items ...</ul>
    #     <form class="notes_form"><textarea class="activity_notes">...</textarea></form>
    #   </div></div></div>
    # </li>

    activities = []

    # Split HTML into activity blocks by finding the boundaries
    # Each activity starts with <li class="activity..." and ends before the next one or at </ul>
    activity_starts = [(m.start(), m) for m in re.finditer(r'<li\s+class="activity([^"]*?)"\s+data-life_activity="(\d+)"[^>]*>', html, re.DOTALL)]

    for idx, (start_pos, start_match) in enumerate(activity_starts):
        # Determine end boundary: next activity start or the closing </ul> of activities list
        if idx + 1 < len(activity_starts):
            end_pos = activity_starts[idx + 1][0]
        else:
            # Find the closing </ul> after the last activity
            end_pos = len(html)
        content = html[start_pos + len(start_match.group(0)):end_pos]
        classes = start_match.group(1)
        activity_id = start_match.group(2)
        is_selected = "selected" in classes

        # Extract activity name
        name_match = re.search(r'<div class="name">\s*(.*?)\s*</div>', content, re.DOTALL)
        name = unescape(name_match.group(1).strip()) if name_match else ""

        # Extract description
        desc_match = re.search(r'<div class="desc">(.*?)</div>', content, re.DOTALL)
        description = unescape(desc_match.group(1).strip()) if desc_match else ""

        # Extract level of need from radio buttons (0=Independent, 1=Requires Assistance, 2=Dependent)
        need_level = None
        need_match = re.search(r'<input\s+type="radio"[^>]*value="(\d+)"[^>]*checked', content)
        if need_match:
            need_level = int(need_match.group(1))

        need_labels = {0: "Independent", 1: "Requires Assistance", 2: "Dependent"}

        # Extract notes from textarea
        notes_match = re.search(r'<textarea[^>]*class="activity_notes"[^>]*>(.*?)</textarea>', content, re.DOTALL)
        notes = unescape(notes_match.group(1).strip()) if notes_match else ""

        # Extract tasks
        # Task <li> can have extra classes (e.g. "one_off"), and either data-client_task
        # or data-life_activity_task may hold the ID (the other can be empty)
        tasks = []
        task_pattern = r'<li\s+class="task([^"]*?)"\s*data-client_task="([^"]*)"\s*data-life_activity_task="([^"]*)"[^>]*>(.*?)</li>'
        for task_match in re.finditer(task_pattern, content, re.DOTALL):
            task_classes, client_task_id, life_activity_task_id, task_content = task_match.groups()

            # Use whichever ID is populated; prefer client_task_id
            task_id = client_task_id or life_activity_task_id or ""

            # Check if task is active (checkbox checked - may be adjacent without space)
            active_match = re.search(r'class="is_active"[^>]*checked', task_content)
            is_active = active_match is not None

            # Extract title
            title_match = re.search(r'<div class="title"[^>]*>(.*?)</div>', task_content, re.DOTALL)
            title = unescape(title_match.group(1).strip()) if title_match else ""

            # Extract shift range
            shift_match = re.search(r'<div class="shift_range"[^>]*>(.*?)</div>', task_content, re.DOTALL)
            shift_range = unescape(shift_match.group(1).strip()) if shift_match else ""

            # Extract days
            days_match = re.search(r'<div class="days_string"[^>]*>(.*?)</div>', task_content, re.DOTALL)
            days = unescape(days_match.group(1).strip()) if days_match else ""

            # Extract caregiver instructions
            instructions_match = re.search(r'<div class="caregiver_instruction"[^>]*>(.*?)</div>', task_content, re.DOTALL)
            instructions = unescape(instructions_match.group(1).strip()) if instructions_match else ""
            if instructions == "--":
                instructions = ""

            # Extract start time
            start_time_match = re.search(r'<div class="start_time"[^>]*>(.*?)</div>', task_content, re.DOTALL)
            start_time = unescape(start_time_match.group(1).strip()) if start_time_match else ""

            tasks.append({
                "task_id": task_id,
                "title": title,
                "is_active": is_active,
                "shift_range": shift_range,
                "days": days,
                "instructions": instructions,
                "start_time": start_time,
            })

        activity_entry = {
            "activity_id": activity_id,
            "name": name,
            "description": description,
            "selected": is_selected,
            "notes": notes,
            "tasks": tasks,
        }

        if need_level is not None:
            activity_entry["level_of_need"] = need_level
            activity_entry["level_of_need_label"] = need_labels.get(need_level, "Unknown")

        activities.append(activity_entry)

    type_label = "ADLs" if adl_type == "1" else "IADLs"

    return {
        "status_code": 200,
        "body": {
            "client_id": client_id,
            "type": type_label,
            "activities": activities,
        },
    }


# === PRIVATE ===

def _fetch_activities_panel(headers, client_id, adl_type):
    """Fetch the activities panel HTML from the API."""
    base_url = BASE_URL
    return requests.get(
        f"{base_url}/assessment/activities_panel/",
        params={"client": client_id, "type": adl_type},
        headers={
            **headers,
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
        },
        impersonate="chrome131",
        timeout=30,
    )
