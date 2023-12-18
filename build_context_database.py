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

print("Extracting data from .py files")
for path in repository_paths:
    for language in languages:
        name = language["name"]
        ext = language["ext"]
        _a, _f = extract_language_file_data(path, ext)
        insert_language_data_into_database(_a, _f, db[name])

print("Database population completed.")
