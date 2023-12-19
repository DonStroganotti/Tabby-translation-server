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


class FunctionDefinition:
    def __init__(self, config):
        self.name = config.get("name", "")
        self.parameters = config.get("parameters", "")
        self.body = config.get("body", "")
        self.full = config.get("full", "")
        self.children = config.get("children", "")


class CallDefinition:
    def __init__(self, config):
        self.name = config.get("name", "")
        self.arguments = config.get("arguments", "")
        self.assignments = config.get("assignments", "")
        self.full = config.get("full", "")


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


# parses text with the selected language parser and returns a syntax tree
def parse_text(source_text, language):
    parser.set_language(get_language(language))
    tree = parser.parse(
        bytes(
            source_text,
            "utf8",
        )
    )
    return tree


# does a .captures query on the source_text, creates a syntax tree
def captures_query_root(source_text, query_text, language):
    tree = parse_text(source_text, language)
    return captures_query_node(query_text, language, tree.root_node), tree


# does a .captures query on an already available syntax tree
def captures_query_node(query_text, language, start_node):
    query = get_language(language).query(query_text)
    return query.captures(start_node)


# extracts the text tuple returned by .captures
def extract_text(text, capture):
    if type(capture) is tuple:
        capture = capture[0]
        return text[capture.start_byte : capture.end_byte]
    else:
        return text[capture.start_byte : capture.end_byte]


def get_specific_parent(start_node, type_name):
    node = start_node
    while node.parent:
        # print("parent: ", node.parent)
        if node.type == type_name:
            return node
        node = node.parent
    return None


def get_calls(text, language) -> [CallDefinition]:
    fn_def_query = """
    (call function: (identifier) @function_call 
    )
    """

    call_captures, tree = captures_query_root(text, fn_def_query, language)

    assignment_query = "(assignment left: (identifier) @assignment)"

    arguments_query = """((argument_list (identifier) @argument))
    """

    calls = []

    for call in call_captures:
        parent = call[0].parent

        # function name
        fn_name = extract_text(text, call[0])
        # get arguments from function
        arg_capture = captures_query_node(arguments_query, language, parent)
        arguments = []
        for arg in arg_capture:
            arguments.append(extract_text(text, arg[0]))

        # print(arguments)
        # if there are arguments, find a function definition as parent
        # look for assignments with the same name as the variables used
        assignments = []
        if len(arguments) > 0:
            # look for a function definition node as a parent
            fn_def_node = get_specific_parent(parent, "function_definition")
            if fn_def_node:
                # get assignments in function
                assignment_captures = captures_query_node(
                    assignment_query, language, fn_def_node
                )
                for assignment in assignment_captures:
                    assignment_name = extract_text(text, assignment[0])
                    # only store assignments of variables used in function call
                    if assignment_name in arguments:
                        assignments.append(
                            AssignmentDefinition(
                                {
                                    "name": assignment_name,
                                    "full": extract_text(text, assignment[0].parent),
                                }
                            )
                        )
        calls.append(
            CallDefinition(
                {
                    "name": fn_name,
                    "full": extract_text(text, parent),
                    "arguments": arguments,
                    "assignments": assignments,
                }
            )
        )
        # print(calls[-1].full)
        # print(calls[-1].arguments)
        # for ass in calls[-1].assignments:
        #     print(ass.full)
    return calls


def get_functions(text, language) -> [FunctionDefinition]:
    fn_def_query = """
    (function_definition name: (identifier) @function-name
    parameters: (parameters) @function-parameters
    body: (block) @function-body
    )
    """

    function_definitions, tree = captures_query_root(text, fn_def_query, language)

    # query to get function calls
    fn_call_query = """
    (call function: (identifier) @function_call arguments: (argument_list) @arguments
     )
        """

    functions = []
    # the query is looking for 3 things
    for i in range(0, len(function_definitions), 3):
        parent = function_definitions[i][0].parent
        function_name = function_definitions[i][0]
        function_parameters = function_definitions[i + 1][0]
        function_body = function_definitions[i + 2][0]

        fn_def = FunctionDefinition(
            {
                "name": extract_text(text, function_name),
                "parameters": extract_text(text, function_parameters),
                "body": extract_text(text, function_body),
                "full": text[function_name.start_byte : function_body.end_byte],
                "children": [],
            }
        )

        # get function calls querying children of the function
        function_calls = captures_query_node(fn_call_query, language, parent)
        for j in range(0, len(function_calls), 2):
            call_name = function_calls[j][0]
            call_arguments = function_calls[j + 1][0]

            fn_def.children.append(
                {
                    "type": "fn_def_call",
                    "name": extract_text(text, call_name),
                    "arguments": extract_text(text, call_arguments),
                    "full": text[call_name.start_byte : call_arguments.end_byte],
                }
            )
            # print(text[fn_call.start_byte : fn_call.end_byte])

        # for child in fn_def.children:
        #     print(child["name"])
        #     print(child["arguments"])
        functions.append(fn_def)
    return functions


def get_top_level_assignments(text, language) -> [AssignmentDefinition]:
    tree = parse_text(text, language)
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
    file_contents = read_files(directory, file_ext)

    assignments = []
    functions = []
    calls = []

    for file in file_contents:
        file_data = file_contents[file]
        # get assignments
        for _data in get_top_level_assignments(file_data, language):
            assignments.append(_data)
        # get functions
        for _data in get_functions(file_data, language):
            functions.append(_data)
        # get calls
        for _data in get_calls(file_data, language):
            calls.append(_data)
    return assignments, functions, calls


# collection is from mongodb
def insert_language_data_into_database(assignments, functions, calls, collection):
    # variable assignments at top level of a document
    for data in assignments:
        post = {"name": data.name, "type": "assignment", "full": data.full}
        collection.insert_one(post)
    # function declarations
    for data in functions:
        post = {
            "name": data.name,
            "type": "function_definition",
            "full": data.full,
            "children": data.children,
        }
        collection.insert_one(post)
    # calls
    for data in calls:
        post = {
            "name": data.name,
            "type": "call",
            "full": data.full,
            "arguments": data.arguments,
            "assignments": [{"name": a.name, "full": a.full} for a in data.assignments],
        }
        collection.insert_one(post)
