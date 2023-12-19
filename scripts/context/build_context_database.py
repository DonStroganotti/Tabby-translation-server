from pymongo import MongoClient, errors
from globals import *
from functions import *
from file_monitoring import *
import threading
import time

VERBOSE = False

## connect to mongodb ##
try:
    client = MongoClient("localhost", 6040)
except errors.ServerSelectionTimeoutError as err:
    print("pymongo ERROR:", err)

db = client["TSS-database"]  # tabby translation server

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
        _a, _f, _calls = extract_language_file_data_from_repository(path, ext, name)
        insert_language_data_into_database(_a, _f, _calls, db[name])

print("Database population completed.")


# callback when a file changes
def update_context(file_path):
    # sleep before updating because the file might not be fully written yet
    time.sleep(1)
    # get file extension from path
    file_ext = os.path.splitext(file_path)[1]
    language_name = get_language_from_ext(file_ext)

    with open(file_path, "r") as f:
        print("Updating database info for file: ", file_path)
        file_info = {"path": file_path, "content": f.read()}
        _a, _f, _calls = extract_language_file_data(file_info, language_name)
        # mongodb collection
        collection = db[language_name]
        delete_file_info(file_path, collection)
        # insert updated data into database
        insert_language_data_into_database(_a, _f, _calls, collection)


def file_modified(file_path):
    if not get_language_from_ext(get_ext_from_file_path(file_path)) == "unknown":
        if VERBOSE:
            print("modified: ", file_path)
        threading.Thread(target=update_context, args=(file_path,)).start()


def file_created(file_path):
    if not get_language_from_ext(get_ext_from_file_path(file_path)) == "unknown":
        if VERBOSE:
            print("created: ", file_path)
        threading.Thread(target=update_context, args=(file_path,)).start()


def file_deleted(file_path):
    file_ext = get_ext_from_file_path(file_path)
    language_name = get_language_from_ext(file_ext)
    if not language_name == "unknown":
        if VERBOSE:
            print("deleted: ", file_path)
        # get file extension from path
        collection = db[language_name]
        delete_file_info(file_path, collection)


# start watching folders for changes
WatchRepositories(repository_paths, file_modified, file_created, file_deleted)
