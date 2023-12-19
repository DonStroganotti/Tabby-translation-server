from pymongo import MongoClient, errors
from functions import *

## connect to mongodb ##
try:
    client = MongoClient("localhost", 6040)
except errors.ServerSelectionTimeoutError as err:
    print("pymongo ERROR:", err)

db = client["TSS-database"]  # tabby translation server

repository_paths = [
    "E:\Python Projects\Tabby-translation-server",
    "E:\Python Projects\Tree-Sitter",
    "E:\Python Projects\Image Captioning Tool\scripts",
]

languages = [
    {"name": "javascript", "ext": ".js"},
    {"name": "python", "ext": ".py"},
    {"name": "html", "ext": ".html"},
    {"name": "css", "ext": ".css"},
]

print("Clearing collections...")
db["python"].delete_many({})
db["javascript"].delete_many({})
db["html"].delete_many({})
db["css"].delete_many({})

# file_data = """
# def send_completion_request(text=""):
#     if text != "":
#         config = {
#             "prompt": "{}".format(text),
#             "max_tokens": 50,
#             "temperature": 0.7,
#             "top_p": 0.3,
#         }
#         config2 = {
#             "name":"potato"
#         }
#         # send_request()
#         #send_request(bar, car)
#         return send_request("127.0.0.1", 5000, config, potato, avocado)
#         return send_request2(ass)
#     return None
# """

# get_calls(file_data, "python")
# print("\ngetting function definitions\n")
# get_functions(file_data, "python")


print("Extracting data from .py files")
for path in repository_paths:
    for language in languages:
        name = language["name"]
        ext = language["ext"]
        _a, _f, _calls = extract_language_file_data(path, ext, name)
        insert_language_data_into_database(_a, _f, _calls, db[name])

print("Database population completed.")
