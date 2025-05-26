from typing import Any, List
import os

import requests

nifi_base_url = "https://localhost:8443/nifi-api"


def login(username: str, password: str) -> str:
    data = {"username": username, "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(
        url=f"{nifi_base_url}/access/token",
        data=data,
        headers=headers,
        verify=False,
    )
    response.raise_for_status()
    return response.text


def get_root_pg(access_token: str) -> Any:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        url=f"{nifi_base_url}/process-groups/root",
        headers=headers,
        verify=False,
    )
    response.raise_for_status()
    return response.json()


def import_template(access_token: str, root_id: str, template_path: str) -> Any:
    headers = {"Authorization": f"Bearer {access_token}"}

    data = {
        "groupName": "flow",
        "positionX": "100",
        "positionY": "100",
        "clientId": "sabd",
    }
    with open(template_path, "rb") as f:
        files = {"file": (os.path.basename(template_path), f, "application/json")}
        response = requests.post(
            url=f"{nifi_base_url}/process-groups/{root_id}/process-groups/upload",
            headers=headers,
            data=data,
            files=files,
            verify=False,
        )
        response.raise_for_status()
        return response.json()


def set_process_group_state(access_token: str, root_id: str, state: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.put(
        url=f"{nifi_base_url}/flow/process-groups/{root_id}",
        headers=headers,
        json={"id": root_id, "state": state},
        verify=False,
    )
    response.raise_for_status()


def get_all_controller_services(access_token: str, root_id: str) -> List[Any]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    response = requests.get(
        url=f"{nifi_base_url}/flow/process-groups/{root_id}/controller-services",
        headers=headers,
        verify=False,
    )
    response.raise_for_status()
    return response.json()["controllerServices"]


def enable_controller_service(
    access_token: str,
    controller_service_id: str,
    service_revision: Any,
):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.put(
        url=f"{nifi_base_url}/controller-services/{controller_service_id}/run-status",
        headers=headers,
        json={"revision": service_revision, "state": "ENABLED"},
        verify=False,
    )
    response.raise_for_status()


def check_run_status(access_token: str, processor_id: str) -> int:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        url=f"{nifi_base_url}/processors/{processor_id}",
        headers=headers,
        verify=False,
    )
    response.raise_for_status()
    return int(response.json()["status"]["aggregateSnapshot"]["tasks"])

