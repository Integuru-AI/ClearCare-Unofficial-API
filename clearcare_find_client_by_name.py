from curl_cffi import requests
import re


def run(headers, user_input):
    """Find clients by name in ClearCare Online."""
    base_url = BASE_URL

    name = user_input.get("name")
    if not name:
        return {"status_code": 400, "body": {"error": "name is required"}}

    # DataTables parameters with search term
    params = {
        "sEcho": "1",
        "iColumns": "15",
        "sColumns": "",
        "iDisplayStart": "0",
        "iDisplayLength": "-1",  # -1 = all records
        "mDataProp_0": "name",
        "mDataProp_1": "home",
        "mDataProp_2": "mobile",
        "mDataProp_3": "work",
        "mDataProp_4": "location",
        "mDataProp_5": "caregivers",
        "mDataProp_6": "city",
        "mDataProp_7": "primary-manager",
        "mDataProp_8": "scheduler",
        "mDataProp_9": "marketer",
        "mDataProp_10": "last-visited",
        "mDataProp_11": "family-login",
        "mDataProp_12": "community",
        "mDataProp_13": "deactivation-reason",
        "mDataProp_14": "profile-id",
        "sSearch": name,  # Server-side search
        "bRegex": "false",
        "status_filter": "",
        "tags_filter": "",
        "employment_screening_filter": "",
        "column_filters": "",
    }

    response = requests.get(
        f"{base_url}/clients/json",
        params=params,
        headers={
            **headers,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        },
        impersonate="chrome131",
        timeout=30,
    )

    # Check for session expiration (HTML login page returned)
    content_type = response.headers.get("Content-Type", "")
    if "text/html" in content_type or response.status_code == 302:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if response.status_code != 200:
        return {"status_code": response.status_code, "body": {"error": response.text}}

    data = response.json()

    if not data.get("success", True):
        return {"status_code": 400, "body": {"error": data.get("message", "Unknown error")}}

    # Parse and clean the client data
    clients = []
    for item in data.get("data", []):
        # Extract client ID from the name link
        name_html = item.get("name", "")
        client_id_match = re.search(r"/clients/(\d+)/", name_html)
        client_id = client_id_match.group(1) if client_id_match else None

        # Extract clean name from HTML
        name_match = re.search(r">([^<]+)</a>", name_html)
        client_name = name_match.group(1) if name_match else name_html

        clients.append({
            "client_id": client_id,
            "profile_id": item.get("profile-id"),
            "name": client_name,
            "home_phone": item.get("home", ""),
            "mobile_phone": item.get("mobile", ""),
            "work_phone": item.get("work", ""),
            "location": item.get("location", ""),
            "city": item.get("city", ""),
            "primary_manager": item.get("primary-manager", "").replace("&nbsp;", " "),
            "scheduler": item.get("scheduler", "").replace("&nbsp;", " "),
            "marketer": item.get("marketer", "").replace("&nbsp;", " "),
            "last_visited": item.get("last-visited", ""),
            "community": item.get("community"),
            "deactivation_reason": item.get("deactivation-reason"),
        })

    return {
        "status_code": 200,
        "body": {
            "total": data.get("recordsFiltered", len(clients)),
            "clients": clients,
        },
    }
