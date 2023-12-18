import glob
import os
from tree_sitter import Language, Parser

JS_LANGUAGE = Language(
    "E:/Python Projects/Tree-Sitter-Build/build/my-languages.so", "javascript"
)
PY_LANGUAGE = Language(
    "E:/Python Projects/Tree-Sitter-Build/build/my-languages.so", "python"
)
HTML_LANGUAGE = Language(
    "E:/Python Projects/Tree-Sitter-Build/build/my-languages.so", "html"
)
CSS_LANGUAGE = Language(
    "E:/Python Projects/Tree-Sitter-Build/build/my-languages.so", "css"
)

parser = Parser()
parser.set_language(PY_LANGUAGE)


class FunctionDefinition:
    def __init__(self, config):
        self.name = config.get("name", "")
        self.parameters = config.get("parameters", "")
        self.body = config.get("body", "")
        self.full = config.get("full", "")
        self.children = config.get("children", "")


class AssignmentDefinition:
    def __init__(self, config):
        self.name = config.get("name", "")
        self.full = config.get("full", "")


def get_language(language):
    if language == "python":
        return PY_LANGUAGE
    elif language == "javascript":
        return JS_LANGUAGE
    elif language == "html":
        return HTML_LANGUAGE
    elif language == "css":
        return CSS_LANGUAGE


def get_functions(text, language) -> [FunctionDefinition]:
    tree = parser.parse(
        bytes(
            text,
            "utf8",
        )
    )
    fn_def_query = get_language(language).query(
        """
    (function_definition name: (identifier) @function-name
    parameters: (parameters) @function-parameters
    body: (block) @function-body
    )
    """
    )
    function_definitions = fn_def_query.captures(tree.root_node)

    # query to get function calls
    fn_call_query = get_language(language).query(
        """
    (call function: (identifier) @function_call arguments: (argument_list) @arguments
     )
        """
    )
    functions = []
    # the query is looking for 3 things
    for i in range(0, len(function_definitions), 3):
        parent = function_definitions[i][0].parent
        function_name = function_definitions[i][0]
        function_parameters = function_definitions[i + 1][0]
        function_body = function_definitions[i + 2][0]

        fn_def = FunctionDefinition(
            {
                "name": text[function_name.start_byte : function_name.end_byte],
                "parameters": text[
                    function_parameters.start_byte : function_parameters.end_byte
                ],
                "body": text[function_body.start_byte : function_body.end_byte],
                "full": text[function_name.start_byte : function_body.end_byte],
                "children": [],
            }
        )

        # get function calls querying children of the function
        function_calls = fn_call_query.captures(parent)
        for j in range(0, len(function_calls), 2):
            call_name = function_calls[j][0]
            call_arguments = function_calls[j + 1][0]

            fn_def.children.append(
                {
                    "type": "call",
                    "name": text[call_name.start_byte : call_name.end_byte],
                    "arguments": text[
                        call_arguments.start_byte : call_arguments.end_byte
                    ],
                }
            )
            # print(text[fn_call.start_byte : fn_call.end_byte])

        # for child in fn_def.children:
        #     print(child["name"])
        #     print(child["arguments"])
        functions.append(fn_def)
    return functions


def get_top_level_assignments(text, language) -> [AssignmentDefinition]:
    tree = parser.parse(
        bytes(
            text,
            "utf8",
        )
    )

    query = get_language(language).query(
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


def extract_language_file_data(directory, file_ext, language):
    data = {"functions": [], "assignments": []}

    file_contents = read_files(directory, file_ext)

    assignments = []
    functions = []

    for file in file_contents:
        file_data = file_contents[file]
        # get assignments
        for _data in get_top_level_assignments(file_data, language):
            assignments.append(_data)
        # get functions
        for _data in get_functions(file_data, language):
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
        post = {"name": data.name, "full": data.full, "children": data.children}
        collection.insert_one(post)
