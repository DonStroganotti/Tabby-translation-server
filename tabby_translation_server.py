import json
import re
from flask import Flask, request
import asyncio
import requests
from pymongo import MongoClient, errors

RUN_WITH_DATABASE = True

if RUN_WITH_DATABASE == True:
    ## connect to mongodb ##
    try:
        client = MongoClient("localhost", 6040)
    except errors.ServerSelectionTimeoutError as err:
        print("pymongo ERROR:", err)

    db = client["TSS-database"]

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
            "top_p": 0.3,
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


# collection from mongodb
def query_database(search_string, collection):
    print("QUERY: ", search_string)
    query = {"name": {"$regex": f"{search_string}", "$options": "i"}}
    return collection.find(query).limit(10)


# better stay away from this
def radioactive_waste(a, b):
    return a * b


# this is a very dangerous function
def MUTANT_CREATOR(henry, scavy):
    mutant = radioactive_waste(henry, scavy)
    return mutant


def repl(m):
    return "\\" + m[0]


def escape_special_chars(s):
    return re.sub("[^a-zA-Z0-9]", repl, s)


def replace_special_chars(s):
    return re.sub("[^a-zA-Z0-9_]", " ", s)


def get_extra_context(prefix, language):
    # based on the last line in the prefix, split into space separated tokens and get database result from those
    prefix_lines = prefix.splitlines()
    prefix_lines = [s for s in prefix_lines if s.replace(" ", "")]
    # replace non valid variable name tokens with spaces
    tokens = replace_special_chars(prefix_lines[-1])
    # split string into multiple tokens to search for
    tokens = tokens.strip().split(" ")
    # only consider tokens that are at least 3 in length
    tokens = [t for t in tokens if len(t) >= 3]
    additional_context = []
    additional_names = []
    for token in tokens:
        # get collection from language
        results = query_database(f"{token}", db[language])
        for result in results:
            result_name = result["name"]
            result_txt = result["full"]
            additional_names.append(result_txt)
            # add in line comment at the start of all lines
            for line in result_txt.split("\n"):
                additional_context.append("# " + line)

    print("Adding the following to context:\n", "\n".join(additional_names))
    # return as a single string
    return "\n".join(additional_context)


async def delayed_response(delay, id, prefix, language):
    global last_id
    returnObj = {
        "id": "",
        "choices": [],
    }
    # delay in milliseconds
    await asyncio.sleep(delay / 1000)
    # if the id matches the last received request only then will a request be made to the LLM server
    if id >= last_id:
        if RUN_WITH_DATABASE == True:
            context = get_extra_context(prefix, language)
        else:
            context = ""
        # print("EXTRA CONTEXT:\n", context)

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
    response = await delayed_response(250, last_id, prefix, language)
    return response, 200


if __name__ == "__main__":
    app.run(debug=True, port=6027)
