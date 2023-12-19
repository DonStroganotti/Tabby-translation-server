import json
import random
import re
from flask import Flask, request
import asyncio
import requests
from pymongo import MongoClient, errors

RUN_WITH_DATABASE = True
VERBOSE = False

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


def count_elements(lst, element):
    count = 0
    for dic in lst:
        if dic["name"] == element:
            count += 1
    return count


# collection from mongodb
def query_database(search_string, collection):
    if VERBOSE:
        print("QUERY: ", search_string)
    query = {"name": {"$regex": f"{search_string}", "$options": "i"}}
    results = collection.find(query)
    list = []
    for result in results:
        name = result["name"]

        # add children to query results
        if "children" in result:
            for child in result["children"]:
                element_count = count_elements(list, child["name"])
                # print(child["name"])
                if element_count < 3:
                    list.append(child)

        # only add up to 3 of the same name element to the list
        element_count = count_elements(list, name)
        if element_count < 3:
            list.append(result)
    # limit results to 5 randomized
    if len(list) > 5:
        list = random.sample(list, len(list))[:5]
    return list


def replace_special_chars(s):
    return re.sub("[^a-zA-Z0-9_]", " ", s)


# tomorrow, use reges to parse some more tokens from the prefix
# for example any function definitions and variable assignments
def get_prefix_context(prefix, language):
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
            if VERBOSE:
                print("Prefix Query result:", result_name)
            result_txt = result["full"]
            additional_names.append(result_txt)
            # add in line comment at the start of all lines
            for line in result_txt.split("\n"):
                additional_context.append("# " + line)
    return additional_context


def get_suffix_context(suffix, language):
    additional_context = []
    # based on the last line in the prefix, split into space separated tokens and get database result from those
    suffix_lines = suffix.splitlines()
    suffix_lines = [s for s in suffix_lines if s.replace(" ", "")]
    if len(suffix_lines) == 0:
        return []
    # replace non valid variable name tokens with spaces
    # get the first line from suffix
    tokens = replace_special_chars(suffix_lines[0])
    # split string into multiple tokens to search for
    tokens = tokens.strip().split(" ")
    # only consider tokens that are at least 3 in length
    tokens = [t for t in tokens if len(t) >= 3]
    for token in tokens:
        # get mongodb collection from language as index
        results = query_database(f"{token}", db[language])
        for result in results:
            result_name = result["name"]
            result_txt = result["full"]
            if VERBOSE:
                print("Suffix Query result:", result_name)
            # if the returned result is a function call, try to get additional variable information
            if result["type"] == "call":
                for assignment in result["assignments"]:
                    for line in assignment["full"].split("\n"):
                        additional_context.append("# " + line)
            # add in line comment at the start of all lines
            for line in result_txt.split("\n"):
                additional_context.append("# " + line)
    return additional_context


def get_extra_context(prefix, suffix, language):
    prefix_context = get_prefix_context(prefix, language)
    suffix_context = get_suffix_context(suffix, language)

    # print("Adding the following to context:\n", "\n".join(additional_names))
    # return as a single string
    return "\n".join(prefix_context + suffix_context)


async def delayed_response(delay, id, prefix, suffix, language):
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
            context = get_extra_context(prefix, suffix, language)
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
    response = await delayed_response(250, last_id, prefix, suffix, language)
    return response, 200


if __name__ == "__main__":
    app.run(debug=True, port=6027)
