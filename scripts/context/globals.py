# monitor - when set to true monitors the folder for changes and updates context database automatically
# recursive_search - when set to true, it will search for files recursively in the directory
import os


repository_paths = [
    {
        "path": "E:\\Python Projects\\Tabby-translation-server\\scripts",
        "monitor": True,
        "recursive_search": True,
    },
    {
        "path": "E:\\Python Projects\\Image Captioning Tool\\scripts",
        "monitor": True,
        "recursive_search": True,
    },
]

languages = [
    {"name": "javascript", "ext": ".js"},
    {"name": "python", "ext": ".py"},
    {"name": "html", "ext": ".html"},
    {"name": "css", "ext": ".css"},
]


def get_ext_from_language(language):
    for lang in languages:
        if lang["name"] == language:
            return lang["ext"]
    return "unknown"


def get_language_from_ext(file_ext):
    # find object that contains string in object
    for language in languages:
        if file_ext == language["ext"]:
            return language["name"]
    return "unknown"


def get_ext_from_file_path(file_path):
    return os.path.splitext(file_path)[1]
