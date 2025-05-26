import time
import os

import urllib3
from dotenv import load_dotenv

from nifi_api import (
    check_run_status,
    enable_controller_service,
    get_all_controller_services,
    get_root_pg,
    import_template,
    login,
    set_process_group_state,
)


def main():
    # load env vars
    username = os.environ.get("NIFI_USERNAME")
    password = os.environ.get("NIFI_PASSWORD")
    template_path = os.environ.get("NIFI_TEMPLATE_PATH")
    if username is None or password is None or template_path is None:
        raise KeyError("Environment variables for NiFi not set")

    print("NiFi: logging in")
    access_token = login(username, password)
    root_id = get_root_pg(access_token)["id"]
    print("NiFi: importing template")
    template = import_template(access_token, root_id, template_path)
    services = get_all_controller_services(access_token, template["component"]["id"])
    print("NiFi: activating services")
    for service in services:
        enable_controller_service(
            access_token,
            service["id"],
            service["revision"],
        )
    # waiting for all controller services to start
    time.sleep(5)
    print("NiFi: scheduling process group")
    set_process_group_state(access_token, root_id, "RUNNING")
    components_ids = [
        x["id"]
        # search for processors
        for x in template["component"]["contents"]["processors"]
        # if the type of the processor is PutHDFS
        if x["type"] == "org.apache.nifi.processors.hadoop.PutHDFS"
    ]
    put_hdfs_id = components_ids[0]
    tasks = 0
    while tasks < 6:
        print(f"NiFi: PutHDFS not completed (ran {tasks} times)")
        time.sleep(15)  # wait 15 secs
        tasks = check_run_status(access_token, put_hdfs_id)
    set_process_group_state(access_token, root_id, "STOPPED")


if __name__ == "__main__":
    load_dotenv()
    # NiFi is running on a not secure HTTPS connection; requests will warn on this
    urllib3.disable_warnings()

    main()

