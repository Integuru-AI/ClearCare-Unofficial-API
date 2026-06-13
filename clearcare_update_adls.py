from curl_cffi import requests

BASE_URL = globals().get("BASE_URL") or "https://<SUBDOMAIN>.clearcareonline.com"
APP_URL = globals().get("APP_URL") or "https://<SUBDOMAIN>.clearcareonline.com"


def run(headers, user_input):
    """Update ADLs (Activities of Daily Living) for a client.

    Can update:
    - Activity selection (selected: true/false)
    - Level of need (level_of_need: 0=Independent, 1=Requires Assistance, 2=Dependent)
    - Activity notes
    - Task activation (tasks[].is_active: true/false)
    - Create new tasks (new_tasks[])
    """
    base_url = BASE_URL

    client_id = user_input.get("client_id")
    if not client_id:
        return {"status_code": 400, "body": {"error": "client_id is required"}}

    activities = user_input.get("activities", [])
    if not activities:
        return {"status_code": 400, "body": {"error": "activities array is required"}}

    results = []
    errors = []

    for activity in activities:
        activity_id = activity.get("activity_id")
        if not activity_id:
            errors.append("Missing activity_id in activity update")
            continue

        # Update activity selection and notes
        if "selected" in activity or "notes" in activity:
            result = _update_activity_selection(base_url, headers, client_id, activity_id, activity)
            if result["success"]:
                results.append(result["data"])
            else:
                errors.append(result["error"])

        # Update level of need
        if "level_of_need" in activity:
            result = _update_level_of_need(base_url, headers, client_id, activity_id, activity)
            if result["success"]:
                results.append(result["data"])
            else:
                errors.append(result["error"])

        # Update task activations
        for task in activity.get("tasks", []):
            task_id = task.get("task_id")
            if not task_id:
                continue

            if "is_active" in task:
                result = _update_task_activation(base_url, headers, client_id, activity_id, task_id, task)
                if result["success"]:
                    results.append(result["data"])
                else:
                    errors.append(result["error"])

        # Create new tasks
        for new_task in activity.get("new_tasks", []):
            title = new_task.get("title")
            if not title:
                errors.append(f"Missing title in new_task for activity {activity_id}")
                continue

            result = _create_task(base_url, headers, client_id, activity_id, new_task)
            if result["success"]:
                results.append(result["data"])
            else:
                errors.append(result["error"])

    if errors and not results:
        return {"status_code": 400, "body": {"error": "All updates failed", "errors": errors}}

    return {
        "status_code": 200,
        "body": {
            "message": "ADLs updated",
            "updates": results,
            "errors": errors if errors else None,
        },
    }


# === PRIVATE ===


def _update_activity_selection(base_url, headers, client_id, activity_id, activity):
    """Update activity selection and notes."""
    params = {
        "client": client_id,
        "life_activity": activity_id,
        "notes": activity.get("notes", ""),
        "delete": "false" if activity.get("selected", True) else "true",
    }

    response = requests.post(
        f"{base_url}/assessment/client_activity/",
        data=params,
        headers={
            **headers,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "Referer": f"{base_url}/clients/{client_id}/assessment/",
        },
        impersonate="chrome131",
        timeout=30,
    )

    if response.status_code == 200:
        return {
            "success": True,
            "data": {
                "activity_id": activity_id,
                "action": "selection_updated",
                "selected": activity.get("selected", True),
            },
        }
    else:
        return {
            "success": False,
            "error": f"Failed to update activity {activity_id} selection: {response.status_code}",
        }


def _update_level_of_need(base_url, headers, client_id, activity_id, activity):
    """Update level of need for an activity."""
    params = {
        "client": client_id,
        "activity": activity_id,
        "score": str(activity["level_of_need"]),
    }

    response = requests.post(
        f"{base_url}/assessment/client_activity_benchmark/",
        data=params,
        headers={
            **headers,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "Referer": f"{base_url}/clients/{client_id}/assessment/",
        },
        impersonate="chrome131",
        timeout=30,
    )

    if response.status_code == 200:
        return {
            "success": True,
            "data": {
                "activity_id": activity_id,
                "action": "level_of_need_updated",
                "level_of_need": activity["level_of_need"],
            },
        }
    else:
        return {
            "success": False,
            "error": f"Failed to update activity {activity_id} level: {response.status_code}",
        }


def _update_task_activation(base_url, headers, client_id, activity_id, task_id, task):
    """Update task activation status."""
    params = {
        "client": client_id,
        "client_task": task_id,
        "life_activity": activity_id,
        "active": "checked" if task["is_active"] else "",
    }

    response = requests.post(
        f"{base_url}/assessment/activate_task/",
        data=params,
        headers={
            **headers,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "Referer": f"{base_url}/clients/{client_id}/assessment/",
        },
        impersonate="chrome131",
        timeout=30,
    )

    if response.status_code == 200:
        return {
            "success": True,
            "data": {
                "activity_id": activity_id,
                "task_id": task_id,
                "action": "task_updated",
                "is_active": task["is_active"],
            },
        }
    else:
        return {
            "success": False,
            "error": f"Failed to update task {task_id}: {response.status_code}",
        }


def _create_task(base_url, headers, client_id, activity_id, new_task):
    """Create a new task for an activity."""
    # Convert user-friendly time format (HH:MM 24h) to platform format (HH:MMam/pm)
    start_time = ""
    if new_task.get("start_time"):
        start_time = _convert_time_to_platform(new_task["start_time"])

    # Build days parameters
    days = new_task.get("days", [])
    days_display_string = "All days"

    # Build form data as a list of tuples to support repeated 'days' keys
    form_data = [
        ("title", new_task["title"]),
        ("caregiver_instruction", new_task.get("caregiver_instruction", "")),
        ("start_time", start_time),
        ("shift_range", str(new_task.get("shift_range", 0))),
    ]

    # Add days checkboxes (repeated field)
    for day in days:
        form_data.append(("days", str(day)))

    form_data.extend([
        ("days_display_string", days_display_string),
        ("client", client_id),
        ("life_activity_task", ""),
        ("life_activity", activity_id),
        ("active", "True"),
        ("client_task", ""),
        ("care_plan_highlight", ""),
        ("care_plan_highlight_iADLS", ""),
        ("submit", "submit"),
    ])

    response = requests.post(
        f"{base_url}/assessment/task_form/",
        data=form_data,
        headers={
            **headers,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "Origin": base_url,
            "Referer": f"{base_url}/clients/{client_id}/assessment/",
        },
        impersonate="chrome131",
        timeout=30,
    )

    if response.status_code == 200:
        return {
            "success": True,
            "data": {
                "activity_id": activity_id,
                "action": "task_created",
                "title": new_task["title"],
            },
        }
    else:
        return {
            "success": False,
            "error": f"Failed to create task '{new_task['title']}' for activity {activity_id}: {response.status_code}",
        }


def _convert_time_to_platform(time_str):
    """Convert HH:MM (24h) to HH:MMam/pm format expected by the platform."""
    try:
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        if hour == 0:
            return f"12:{minute:02d}am"
        elif hour < 12:
            return f"{hour:02d}:{minute:02d}am"
        elif hour == 12:
            return f"12:{minute:02d}pm"
        else:
            return f"{hour - 12:02d}:{minute:02d}pm"
    except (ValueError, IndexError):
        return time_str
