import json
from flask import Flask, request
import asyncio
import requests

app = Flask(__name__)

global last_id
last_id = 0


@app.route("/v1/health", methods=["GET"])
async def health():
    return {
        "device": "device_name",
        "arch": "architecture",
        "cpu_info": "cpu_info",
        "cpu_count": 4,
        "cuda_devices": ["cuda_device1", "cuda_device2"],
        "version": {"model": "model_name", "chat_model": "chat_model_name"},
        "build_date": "build_date",
        "build_timestamp": "build_timestamp",
        "git_sha": "git_sha",
        "git_describe": "git_describe",
    }, 200


@app.route("/v1/events", methods=["POST"])
async def events():
    some_json = request.get_json()
    # print("Event: \n", some_json)
    return {}, 200


def send_completion_request(text=""):
    if text != "":
        config = {
            "prompt": "{}".format(text),
            "max_tokens": 50,
            "temperature": 0.7,
            "top_p": 0.1,
        }

        return send_request("127.0.0.1", 5000, config)
    return None


def send_request(ip, port, config):
    url = f"http://{ip}:{port}/v1/completions"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(config))

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


def get_extra_context(prefix):
    # get full file context up till the prefix
    with open("file.py", "r") as file:
        # read entire file into a string
        file_contents = file.read()
        return file_contents


async def delayed_response(delay, id, prefix):
    global last_id
    returnObj = {
        "id": "",
        "choices": [],
    }
    # delay in milliseconds
    await asyncio.sleep(delay / 1000)
    # if the id matches the last received request only then will a request be made to the LLM server
    if id >= last_id:
        context = ""  # get_extra_context(prefix)

        response = send_completion_request(context + prefix)
        if response is not None:
            print("id {} LLM request started".format(id))
            # pick the first choice
            choices = response["choices"]
            if len(choices) > 0:
                # update the returnObj data with the response from the LLM
                returnObj["choices"].append(
                    {"index": choices[0]["index"], "text": choices[0]["text"]}
                )

    return returnObj


@app.route("/v1/completions", methods=["POST"])
async def completions():
    global last_id

    data = request.get_json()
    language = data["language"]
    prefix = data["segments"]["prefix"]
    suffix = data["segments"]["suffix"]

    last_id = last_id + 1

    # By delaying the responses the function has time internally to prevent sending older messages
    # while the user is still typing
    response = await delayed_response(250, last_id, prefix)
    return response, 200


if __name__ == "__main__":
    app.run(debug=True, port=6027)
