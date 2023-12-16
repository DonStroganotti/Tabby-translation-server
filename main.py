import json
from flask import Flask, request
from flask_restful import Resource, Api
import asyncio
import requests
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
api = Api(app)


class Health(Resource):
    def get(self):
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


class Events(Resource):
    def post(self):
        some_json = request.get_json()
        # print("Event: \n", some_json)
        return 200


class Completions(Resource):
    def __init__(self):
        self.waiting_for_response = False
        self.last_returnObj = {
            "id": "",
            "choices": [],
        }
        self.last_id = 0

    async def delayed_response(self, delay, id, response):
        # delay in milliseconds
        await asyncio.sleep(delay / 1000)
        if id >= self.last_id:
            pass

    def post(self):
        data = request.get_json()
        language = data["language"]
        prefix = data["segments"]["prefix"]
        suffix = data["segments"]["suffix"]

        if self.waiting_for_response:
            return self.last_returnObj, 200

        self.waiting_for_response = True
        response = self.send_completion_request(prefix)

        if response is not None:
            choices = response["choices"]

            if len(choices) > 0:
                self.last_returnObj["choices"].append(
                    {"index": choices[0]["index"], "text": choices[0]["text"]}
                )

        self.waiting_for_response = False
        return self.last_returnObj, 200

    def send_completion_request(self, text=""):
        if text != "":
            config = {
                "prompt": "{}".format(text),
                "max_tokens": 50,
                "temperature": 0.7,
                "top_p": 0.1,
            }

            return self.send_request("127.0.0.1", 5000, config)
        return None

    def send_request(self, ip, port, config):
        url = f"http://{ip}:{port}/v1/completions"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, headers=headers, data=json.dumps(config))

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None


api.add_resource(Health, "/v1/health")
api.add_resource(Events, "/v1/events")
api.add_resource(Completions, "/v1/completions")

if __name__ == "__main__":
    app.run(debug=True, port=6027)
