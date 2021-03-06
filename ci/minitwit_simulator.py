"""
Call me for example like:

$ python minitwit_simulator.py "http://localhost:5001"
"""

import traceback
import os
import csv
import sys
import json
import http
import socket
import base64
import requests
from time import sleep
from datetime import datetime
from contextlib import closing
import sqlite3

CSV_FILENAME = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "minitwit_scenario.csv")
USERNAME = "simulator"
PWD = "super_safe!"
CREDENTIALS = ":".join([USERNAME, PWD]).encode("ascii")
ENCODED_CREDENTIALS = base64.b64encode(CREDENTIALS).decode()
HEADERS = {
    "Connection": "close",
    "Content-Type": "application/json",
    f"Authorization": f"Basic {ENCODED_CREDENTIALS}",
}

# How many warnings do we tolerate before we consider the simulation as an error?
WARNING_THRESHOLD=10
# How many times should we check if the server is up before failing?
WAIT_SERVER_BOOT_ATTEMPTS=10
# How long should we wait between each up check?
WAIT_SERVER_BOOT_TIMEOUT_SEC=5

warningCounter = 0

def main(host):
    wait_for_server_bootup(host)
    perform_simulation(host)

def perform_simulation(host):
    global warningCounter, WARNING_THRESHOLD

    print("::group::Simulator Errors/Warnings")
    for action, delay in get_actions():
        if warningCounter > WARNING_THRESHOLD:
            report_error_ci(
                "Amount of warnings exceeded threshold of {}.".format(WARNING_THRESHOLD))
            sys.exit(1)

        try:
            # SWITCH ON TYPE
            command = action["post_type"]
            reponse = None

            if command == "register":

                # build url for request
                url = f"{host}/register"

                # Set parameters: latest
                params = {"latest": action["latest"]}
                # Set data: username, email, pwd
                data = {
                    "username": action["username"],
                    "email": action["email"],
                    "pwd": action["pwd"],
                }

                response = requests.post(
                    url,
                    data=json.dumps(data),
                    params=params,
                    headers=HEADERS,
                    timeout=1,
                )

                # error handling (204 success, 400 user exists)
                # 400 user exists already but not an error to log
                if not (response.status_code == 204) or (response.status_code == 400):
                    report_action_warning_ci(
                        host, command, action["latest"], response.status_code)

                response.close()

            elif command == "msgs":

                # LIST method. Not used atm.
                # build url for request
                url = f"{host}/msgs"

                # Set parameters: latest & no (amount)
                params = {"latest": action["latest"], "no": action["no"]}

                response = requests.post(
                    url, params=params, headers=HEADERS, timeout=0.3
                )

                # error handling (200 success, 403 failure (no headers))

                # 403 bad request
                if response.status_code != 200:
                    report_action_warning_ci(
                        host, command, action["latest"], response.status_code)

                response.close()

            elif command == "follow":

                # build url for request
                username = action["username"]
                url = f"{host}/fllws/{username}"

                # Set parameters: latest
                params = {"latest": action["latest"]}
                # Set data: content
                data = {"follow": action["follow"]}  # value for user to follow

                response = requests.post(
                    url,
                    data=json.dumps(data),
                    params=params,
                    headers=HEADERS,
                    timeout=0.3,
                )

                # error handling (204 success, 403 failure, 404 Not Found no user id)

                # 403 unauthorized or 404 Not Found
                if response.status_code != 204:
                    report_action_warning_ci(
                        host, command, action["latest"], response.status_code)

                response.close()

            elif command == "unfollow":

                # build url for request
                username = action["username"]
                url = f"{host}/fllws/{username}"
                # Set parameters: latest
                params = {"latest": action["latest"]}
                # Set data: content
                # value for user to follow
                data = {"unfollow": action["unfollow"]}

                response = requests.post(
                    url,
                    data=json.dumps(data),
                    params=params,
                    headers=HEADERS,
                    timeout=0.3,
                )

                # error handling (204 success, 403 failure, 404 Not Found no user id)

                # 403 unauthorized or 404 Not Found
                if response.status_code != 204:
                    report_action_warning_ci(
                        host, command, action["latest"], response.status_code)

                response.close()

            elif command == "tweet":

                # build url for request
                username = action["username"]
                url = f"{host}/msgs/{username}"
                # Set parameters: latest
                params = {"latest": action["latest"]}
                # Set data: content
                data = {"content": action["content"]}

                response = requests.post(
                    url,
                    data=json.dumps(data),
                    params=params,
                    headers=HEADERS,
                    timeout=0.3,
                )

                # error handling (204 success, 403 failure)
                # 403 unauthorized
                if response.status_code != 204:
                    report_action_warning_ci(
                        host, command, action["latest"], response.status_code)

                response.close()

            else:
                report_error_ci("FATAL: Unknown message type")

        except requests.exceptions.ConnectionError as e:
            report_error_ci("Connection error at action '{}' of type '{}'".format(
                action["latest"], command))

        except requests.exceptions.ReadTimeout as e:
            report_warning_ci("Timeout at action '{}' of type '{}'".format(
                action["latest"], command))

        except Exception as e:
            errorMsg = "Exception of type '{}' thrown.\n".format(
                type(e).__name__)
            errorMsg += "Action number '{}' of type '{}'.\n".format(
                action["latest"], command)
            errorMsg += "Stack trace:\n" + traceback.format_exc()

            report_error_ci(errorMsg)

    print("::endgroup::")

def get_actions():

    # read scenario .csv and parse to a list of lists
    with open(CSV_FILENAME, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t", quotechar=None)

        # for each line in .csv
        for line in reader:
            # we know that the command string is always the fourth element
            command = line[3]

            command_id = int(line[0])
            delay = int(line[1])
            user = line[4]
            if command == "register":
                email = line[5]
                user_pwd = line[-1]

                item = {
                    "latest": command_id,
                    "post_type": command,
                    "username": user,
                    "email": email,
                    "pwd": user_pwd,
                }

                yield item, delay

            elif command == "tweet":
                tweet_content = line[5]
                item = {
                    "latest": command_id,
                    "post_type": command,
                    "username": user,
                    "content": tweet_content,
                }

                yield item, delay

            elif command == "follow":
                user_to_follow = line[5]
                item = {
                    "latest": command_id,
                    "post_type": command,
                    "username": user,
                    "follow": user_to_follow,
                }
                yield item, delay

            elif command == "unfollow":
                user_to_unfollow = line[5]

                item = {
                    "latest": command_id,
                    "post_type": command,
                    "username": user,
                    "unfollow": user_to_unfollow,
                }
                yield item, delay

            else:
                # This should never happen and can likely be removed to
                # make parsing for plot generation later easier
                report_error_ci("Unknown type found: (" + command + ")")

def wait_for_server_bootup(host):
    response = None
    for i in range(WAIT_SERVER_BOOT_ATTEMPTS):
        print("Checking if server is alive (attempt {})".format(i+1))

        try:
            response = requests.get(
                host + "/latest",
                headers=HEADERS,
                timeout=0.1,
            )

            response.close()

            if response.status_code == 200:
                return True

            print("Server did not return status code 200. Retrying...")

        except requests.exceptions.ReadTimeout as e:
            print("Request to server timed out. Retrying...")
        except requests.exceptions.ConnectionError as e:
            print("Connection refused. Retrying...")

        sleep(WAIT_SERVER_BOOT_TIMEOUT_SEC)
    
    report_error_ci("Could not contact server on host '{}' after {} attempts (total timeout: {} seconds)".format(
        host, WAIT_SERVER_BOOT_ATTEMPTS, WAIT_SERVER_BOOT_TIMEOUT_SEC*WAIT_SERVER_BOOT_ATTEMPTS))
    sys.exit(1)

def report_action_warning_ci(host, command, latestAction, statusCode):
    report_warning_ci("Action '{}' failed with status code {}. Command was '{}'.".format(latestAction, statusCode, command))

def report_warning_ci(msg):
    global warningCounter
    warningCounter+=1
    print("::warning ::Warning: {}".format(msg))

def report_error_ci(msg):
    print("::error ::Error: {}".format(msg))

if __name__ == "__main__":
    host = sys.argv[1]

    main(host)
