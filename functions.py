import glob
import os
from tree_sitter import Language, Parser

JS_LANGUAGE = Language("build/my-languages.so", "javascript")
PY_LANGUAGE = Language("build/my-languages.so", "python")

parser = Parser()
parser.set_language(PY_LANGUAGE)


class FunctionDefinition:
    def __init__(self, config):
        self.name = config.get("name", "")
        self.parameters = config.get("parameters", "")
        self.body = config.get("body", "")
        self.full = config.get("full", "")


class AssignmentDefinition:
    def __init__(self, config):
        self.name = config.get("name", "")
        self.full = config.get("full", "")


def get_functions(text) -> [FunctionDefinition]:
    tree = parser.parse(
        bytes(
            text,
            "utf8",
        )
    )
    query = PY_LANGUAGE.query(
        """
    (function_definition name: (identifier) @function-name
    parameters: (parameters) @function-parameters
    body: (block) @function-body
    )
    """
    )
    matches = query.captures(tree.root_node)

    functions = []
    # the query is looking for 3 things
    for i in range(0, len(matches), 3):
        function_name = matches[i]
        function_parameters = matches[i + 1]
        function_body = matches[i + 2]
        fn_def = FunctionDefinition(
            {
                "name": text[function_name[0].start_byte : function_name[0].end_byte],
                "parameters": text[
                    function_parameters[0].start_byte : function_parameters[0].end_byte
                ],
                "body": text[function_body[0].start_byte : function_body[0].end_byte],
                "full": text[function_name[0].start_byte : function_body[0].end_byte],
            }
        )
        functions.append(fn_def)
    return functions


def get_top_level_assignments(text) -> [AssignmentDefinition]:
    tree = parser.parse(
        bytes(
            text,
            "utf8",
        )
    )
    query = PY_LANGUAGE.query(
        """
    (   
        assignment left: (identifier) @name)
    
    """
    )

    assignments = []
    # loop all top level children only
    for child in tree.root_node.children:
        if child.type == "expression_statement":
            name = query.captures(child)
            if name:
                name = name[0][0]
                # get the name
                name = text[name.start_byte : name.end_byte]
                full = text[child.start_byte : child.end_byte]
                a_def = AssignmentDefinition({"name": name, "full": full})
                assignments.append(a_def)
    return assignments


def read_files(directory, file_ext):
    py_files = glob.glob(os.path.join(directory, f"*{file_ext}"))
    file_contents = {}
    for file in py_files:
        with open(file, "r") as f:
            file_contents[file] = f.read()
    return file_contents


def extract_language_file_data(directory, file_ext):
    data = {"functions": [], "assignments": []}

    file_contents = read_files(directory,file_ext)

    assignments = []
    functions = []

    for file in file_contents:
        file_data = file_contents[file]
        # get assignments
        for _data in get_top_level_assignments(file_data):
            assignments.append(_data)
        # get functions
        for _data in get_functions(file_data):
            functions.append(_data)
    return assignments, functions


# collection is from mongodb
def insert_language_data_into_database(assignments, functions, collection):
    # variable assignments at top level of a document
    for data in assignments:
        post = {"name": data.name, "full": data.full}
        collection.insert_one(post)
    # function declarations
    for data in functions:
        post = {"name": data.name, "full": data.full}
        collection.insert_one(post)
