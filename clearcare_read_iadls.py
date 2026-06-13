from curl_cffi import requests
import re
from html import unescape


def run(headers, user_input):
    """Read iADLs (Instrumental Activities of Daily Living) for a client."""
    base_url = BASE_URL

    client_id = user_input.get("client_id")
    if not client_id:
        return {"status_code": 400, "body": {"error": "client_id is required"}}

    response = requests.get(
        f"{base_url}/assessment/activities_panel/",
        params={"client": client_id, "type": "2"},  # type=2 for iADLs
        headers={
            **headers,
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
        },
        impersonate="chrome131",
        timeout=30,
    )

    if response.status_code == 302 or "login" in response.text.lower()[:500]:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if response.status_code != 200:
        return {"status_code": response.status_code, "body": {"error": "Failed to fetch iADLs"}}

    html = response.text

    # Parse activities
    activities = []
    activity_pattern = r'<li class="activity([^"]*)"[^>]*data-life_activity="(\d+)"[^>]*>(.*?)</li>'

    for match in re.finditer(activity_pattern, html, re.DOTALL):
        classes, activity_id, content = match.groups()
        is_selected = "selected" in classes

        # Extract activity name
        name_match = re.search(r'<div class="name">\s*([^<]+?)\s*</div>', content)
        name = unescape(name_match.group(1).strip()) if name_match else ""

        # Extract description
        desc_match = re.search(r'<div class="desc">([^<]+)</div>', content)
        description = unescape(desc_match.group(1).strip()) if desc_match else ""

        # Extract level of need (0=Independent, 1=Requires Assistance, 2=Dependent)
        need_level = 0
        need_match = re.search(r'name="[^"]*"\s+value="(\d+)"[^>]*checked', content)
        if need_match:
            need_level = int(need_match.group(1))

        # Extract notes
        notes_match = re.search(r'<textarea[^>]*class="activity_notes"[^>]*>([^<]*)</textarea>', content)
        notes = unescape(notes_match.group(1).strip()) if notes_match else ""

        # Extract tasks
        tasks = []
        task_pattern = r'<li class="task[^"]*"[^>]*data-client_task="(\d+)"[^>]*>(.*?)</li>'
        for task_match in re.finditer(task_pattern, content, re.DOTALL):
            task_id, task_content = task_match.groups()

            is_active = 'checked="checked"' in task_content

            title_match = re.search(r'<div class="title"[^>]*>([^<]+)</div>', task_content)
            title = unescape(title_match.group(1).strip()) if title_match else ""

            shift_match = re.search(r'<div class="shift_range"[^>]*>([^<]+)</div>', task_content)
            shift_range = unescape(shift_match.group(1).strip()) if shift_match else ""

            days_match = re.search(r'<div class="days_string"[^>]*>([^<]+)</div>', task_content)
            days = unescape(days_match.group(1).strip()) if days_match else ""

            instructions_match = re.search(r'<div class="caregiver_instruction"[^>]*>([^<]*)</div>', task_content)
            instructions = unescape(instructions_match.group(1).strip()) if instructions_match else ""

            tasks.append({
                "task_id": task_id,
                "title": title,
                "is_active": is_active,
                "shift_range": shift_range,
                "days": days,
                "instructions": instructions,
            })

        activities.append({
            "activity_id": activity_id,
            "name": name,
            "description": description,
            "selected": is_selected,
            "level_of_need": need_level,
            "level_of_need_label": ["Independent", "Requires Assistance", "Dependent"][need_level],
            "notes": notes,
            "tasks": tasks,
        })

    return {
        "status_code": 200,
        "body": {
            "client_id": client_id,
            "type": "iADLs",
            "activities": activities,
        },
    }
