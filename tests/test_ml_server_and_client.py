import json
from typing import List, TypedDict
from unittest.mock import patch

import pytest
from flask.wrappers import Response

from flask_ml.flask_ml_client import MLClient
from flask_ml.flask_ml_server import MLServer
from flask_ml.flask_ml_server.models import *

from .constants import *


class MockResponse:
    def __init__(self, response: Response):
        self.status_code = response.status_code
        self.headers = {"Content-Type": "application/json"}
        self.response: Response = response

    def json(self):
        return self.response.get_json()


def create_response_model(results: BaseModel):
    return Response(response=results.model_dump_json(), status=200, mimetype="application/json")


def mock_post_request(url, json=None, **kwargs) -> MockResponse:
    data = RequestBody.model_validate(json)
    if url == "http://127.0.0.1:5000/process_text":
        return MockResponse(create_response_model(process_text(data.inputs["text_input"], data.parameters)))  # type: ignore
    elif url == "http://127.0.0.1:5000/process_file":
        return MockResponse(create_response_model(process_file(data.inputs["file_input"], data.parameters)))  # type: ignore
    elif url == "http://127.0.0.1:5000/process_texts":
        return MockResponse(create_response_model(process_texts(data.inputs["text_inputs"].root.texts, data.parameters)))  # type: ignore
    elif url == "http://127.0.0.1:5000/process_files":
        return MockResponse(create_response_model(process_files(data.inputs["file_inputs"].root.files, data.parameters)))  # type: ignore
    elif url == "http://127.0.0.1:5000/process_directory":
        return MockResponse(create_response_model(process_directory(data.inputs["dir_input"], data.parameters)))  # type: ignore
    assert False, "Never"


def process_text(inputs: TextInput, parameters):
    results = TextResponse(title=inputs.text, value="processed_text.txt")
    return results


def process_file(inputs: FileInput, parameters):
    results = FileResponse(title=inputs.path, path="processed_image.img", file_type=FileType.IMG)
    return results


def process_texts(inputs: List[TextInput], parameters):
    results = [TextResponse(title=inp.text, value="processed_text.txt") for inp in inputs]
    results = BatchTextResponse(texts=results)
    return results


def process_files(inputs: List[FileInput], parameters):
    results = [
        FileResponse(title=inp.path, path="processed_image.img", file_type=FileType.IMG) for inp in inputs
    ]
    results = BatchFileResponse(files=results)
    return results


def process_directory(inputs: DirectoryInput, parameters):
    results = DirectoryResponse(path="processed_images", title=inputs.path, subtitle="")
    return results


@pytest.fixture
def app():
    server = MLServer(__name__)

    class SingleTextInput(TypedDict):
        text_input: TextInput

    class TextInputs(TypedDict):
        text_inputs: BatchTextInput

    class SingleFileInput(TypedDict):
        file_input: FileInput

    class FileInputs(TypedDict):
        file_inputs: BatchFileInput

    class DirInput(TypedDict):
        dir_input: DirectoryInput

    class TextParameters(TypedDict):
        param1: str

    class IntParameters(TypedDict):
        param1: int

    class FloatParameters(TypedDict):
        param1: float

    @server.route("/process_text")
    def server_process_text(inputs: SingleTextInput, parameters: TextParameters) -> ResponseBody:
        return ResponseBody(root=process_text(inputs["text_input"], parameters))

    @server.route("/process_file")
    def server_process_image(inputs: SingleFileInput, parameters: FloatParameters) -> ResponseBody:
        return ResponseBody(root=process_file(inputs["file_input"], parameters))

    @server.route("/process_texts")
    def server_process_texts(inputs: TextInputs, parameters: IntParameters) -> ResponseBody:
        return ResponseBody(root=process_texts(inputs["text_inputs"].texts, parameters))

    @server.route("/process_files")
    def server_process_images(inputs: FileInputs, parameters: FloatParameters) -> ResponseBody:
        return ResponseBody(root=process_files(inputs["file_inputs"].files, parameters))

    @server.route("/process_directory")
    def server_process_directory(inputs: DirInput, parameters: IntParameters) -> ResponseBody:
        return ResponseBody(root=process_directory(inputs["dir_input"], parameters))

    def get_task_schema(inputSchema: InputSchema, parameterSchema: ParameterSchema):
        return lambda: TaskSchema(
            inputs=[inputSchema],
            parameters=[parameterSchema],
        )

    @server.route("/process_text_with_schema", get_task_schema(TEXT_INPUT_SCHEMA, TEXT_PARAM_SCHEMA))
    def server_process_text_with_schema(inputs: SingleTextInput, parameters: TextParameters) -> ResponseBody:
        return ResponseBody(root=process_text(inputs["text_input"], parameters))

    @server.route("/process_textarea_with_schema", get_task_schema(TEXTAREA_INPUT_SCHEMA, ENUM_PARAM_SCHEMA))
    def server_process_textarea_with_schema(
        inputs: SingleTextInput, parameters: TextParameters
    ) -> ResponseBody:
        return ResponseBody(root=process_text(inputs["text_input"], parameters))

    @server.route("/process_file_with_schema", get_task_schema(FILE_INPUT_SCHEMA, FLOAT_PARAM_SCHEMA))
    def server_process_image_with_schema(
        inputs: SingleFileInput, parameters: FloatParameters
    ) -> ResponseBody:
        return ResponseBody(root=process_file(inputs["file_input"], parameters))

    @server.route("/process_texts_with_schema", get_task_schema(BATCHTEXT_INPUT_SCHEMA, INT_PARAM_SCHEMA))
    def server_process_texts_with_schema(inputs: TextInputs, parameters: IntParameters) -> ResponseBody:
        return ResponseBody(root=process_texts(inputs["text_inputs"].texts, parameters))

    @server.route(
        "/process_files_with_schema", get_task_schema(BATCHFILE_INPUT_SCHEMA, RANGED_FLOAT_PARAM_SCHEMA)
    )
    def server_process_images_with_schema(inputs: FileInputs, parameters: FloatParameters) -> ResponseBody:
        return ResponseBody(root=process_files(inputs["file_inputs"].files, parameters))

    @server.route(
        "/process_directory_with_schema", get_task_schema(DIRECTORY_INPUT_SCHEMA, RANGED_INT_PARAM_SCHEMA)
    )
    def server_process_directory_with_schema(inputs: DirInput, parameters: IntParameters) -> ResponseBody:
        return ResponseBody(root=process_directory(inputs["dir_input"], parameters))

    return server.app.test_client()


@pytest.fixture
def client():
    return MLClient("http://127.0.0.1:5000/predict")


def test_list_routes(app):
    response = app.get("/api/routes")
    assert response.status_code == 200
    assert response.json == [
        {
            "payload_schema": "/process_text/payload_schema",
            "run_task": "/process_text",
            "sample_payload": "/process_text/sample_payload",
        },
        {
            "payload_schema": "/process_file/payload_schema",
            "run_task": "/process_file",
            "sample_payload": "/process_file/sample_payload",
        },
        {
            "payload_schema": "/process_texts/payload_schema",
            "run_task": "/process_texts",
            "sample_payload": "/process_texts/sample_payload",
        },
        {
            "payload_schema": "/process_files/payload_schema",
            "run_task": "/process_files",
            "sample_payload": "/process_files/sample_payload",
        },
        {
            "payload_schema": "/process_directory/payload_schema",
            "run_task": "/process_directory",
            "sample_payload": "/process_directory/sample_payload",
        },
        {
            "order": 0,
            "payload_schema": "/process_text_with_schema/payload_schema",
            "run_task": "/process_text_with_schema",
            "sample_payload": "/process_text_with_schema/sample_payload",
            "short_title": "",
            "task_schema": "/process_text_with_schema/task_schema",
        },
        {
            "order": 0,
            "payload_schema": "/process_textarea_with_schema/payload_schema",
            "run_task": "/process_textarea_with_schema",
            "sample_payload": "/process_textarea_with_schema/sample_payload",
            "short_title": "",
            "task_schema": "/process_textarea_with_schema/task_schema",
        },
        {
            "order": 0,
            "payload_schema": "/process_file_with_schema/payload_schema",
            "run_task": "/process_file_with_schema",
            "sample_payload": "/process_file_with_schema/sample_payload",
            "short_title": "",
            "task_schema": "/process_file_with_schema/task_schema",
        },
        {
            "order": 0,
            "payload_schema": "/process_texts_with_schema/payload_schema",
            "run_task": "/process_texts_with_schema",
            "sample_payload": "/process_texts_with_schema/sample_payload",
            "short_title": "",
            "task_schema": "/process_texts_with_schema/task_schema",
        },
        {
            "order": 0,
            "payload_schema": "/process_files_with_schema/payload_schema",
            "run_task": "/process_files_with_schema",
            "sample_payload": "/process_files_with_schema/sample_payload",
            "short_title": "",
            "task_schema": "/process_files_with_schema/task_schema",
        },
        {
            "order": 0,
            "payload_schema": "/process_directory_with_schema/payload_schema",
            "run_task": "/process_directory_with_schema",
            "sample_payload": "/process_directory_with_schema/sample_payload",
            "short_title": "",
            "task_schema": "/process_directory_with_schema/task_schema",
        },
    ]


def test_empty_list_routes():
    server = MLServer(__name__)
    app = server.app.test_client()
    response = app.get("/api/routes")
    assert response.status_code == 200
    assert response.json == []


def test_payload_schema(app):
    response = app.get("/process_file/payload_schema")
    assert response.status_code == 200
    assert "$defs" in response.json


@pytest.mark.parametrize(
    "endpoint,expected_response",
    [
        (
            "/process_text",
            {
                "inputs": {"text_input": {"text": "A sample piece of text"}},
                "parameters": {"param1": "Sample value for parameter"},
            },
        ),
        (
            "/process_file",
            {"inputs": {"file_input": {"path": "/Users/path/to/file"}}, "parameters": {"param1": 1.0}},
        ),
        (
            "/process_texts",
            {
                "inputs": {
                    "text_inputs": {
                        "texts": [{"text": "A sample piece of text 1"}, {"text": "A sample piece of text 2"}]
                    }
                },
                "parameters": {"param1": 1},
            },
        ),
        (
            "/process_files",
            {
                "inputs": {
                    "file_inputs": {
                        "files": [{"path": "/Users/path/to/file1"}, {"path": "/Users/path/to/file2"}]
                    }
                },
                "parameters": {"param1": 1.0},
            },
        ),
        (
            "/process_directory",
            {"inputs": {"dir_input": {"path": "/Users/path/to/folder"}}, "parameters": {"param1": 1}},
        ),
    ],
)
def test_sample_payload(app, endpoint, expected_response):
    response = app.get(f"{endpoint}/sample_payload")
    assert response.status_code == 200
    assert response.json == expected_response


def test_payload_schema_with_task_schema(app):
    response = app.get("/process_files_with_schema/payload_schema")
    assert response.status_code == 200
    assert "$defs" in response.json


@pytest.mark.parametrize(
    "endpoint,expected_response",
    [
        (
            "/process_text_with_schema",
            {
                "inputs": {"text_input": {"text": "A sample piece of text"}},
                "parameters": {"param1": "default"},
            },
        ),
        (
            "/process_textarea_with_schema",
            {
                "inputs": {
                    "text_input": {
                        "text": "A sample piece of text of text that's long. A sample piece of text of text that's long. A sample piece of text of text that's long. A sample piece of text of text that's long. A sample piece of text of text that's long. A sample piece of text of text that's long. A sample piece of text of text that's long. A sample piece of text of text that's long."
                    }
                },
                "parameters": {"param1": "option_1"},
            },
        ),
        (
            "/process_file_with_schema",
            {"inputs": {"file_input": {"path": "/Users/path/to/file"}}, "parameters": {"param1": 0.0}},
        ),
        (
            "/process_texts_with_schema",
            {
                "inputs": {
                    "text_inputs": {
                        "texts": [{"text": "A sample piece of text 1"}, {"text": "A sample piece of text 2"}]
                    }
                },
                "parameters": {"param1": 1},
            },
        ),
        (
            "/process_files_with_schema",
            {
                "inputs": {
                    "file_inputs": {
                        "files": [{"path": "/Users/path/to/file1"}, {"path": "/Users/path/to/file2"}]
                    }
                },
                "parameters": {"param1": 0.0},
            },
        ),
        (
            "/process_directory_with_schema",
            {"inputs": {"dir_input": {"path": "/Users/path/to/folder"}}, "parameters": {"param1": 0}},
        ),
    ],
)
def test_sample_payload_with_task_schema(app, endpoint, expected_response):
    response = app.get(f"{endpoint}/sample_payload")
    assert response.status_code == 200
    assert response.json == expected_response


@pytest.mark.parametrize(
    "endpoint,expected_response",
    [
        (
            "/process_text_with_schema",
            {
                "inputs": [
                    {"input_type": "text", "key": "text_input", "label": "Text Input", "subtitle": ""}
                ],
                "parameters": [
                    {
                        "key": "param1",
                        "label": "Text Parameter",
                        "subtitle": "",
                        "value": {"parameter_type": "text", "default": "default"},
                    }
                ],
            },
        ),
        (
            "/process_textarea_with_schema",
            {
                "inputs": [
                    {
                        "input_type": "textarea",
                        "key": "text_input",
                        "label": "Text Area Input",
                        "subtitle": "",
                    }
                ],
                "parameters": [
                    {
                        "key": "param1",
                        "label": "Enum Parameter",
                        "subtitle": "",
                        "value": {
                            "parameter_type": "enum",
                            "enum_vals": [
                                {"label": "Option 1", "key": "option_1"},
                                {"label": "Option 2", "key": "option_2"},
                            ],
                            "message_when_empty": None,
                            "default": "option_1",
                        },
                    }
                ],
            },
        ),
        (
            "/process_file_with_schema",
            {
                "inputs": [
                    {"input_type": "file", "key": "file_input", "label": "File Input", "subtitle": ""}
                ],
                "parameters": [
                    {
                        "key": "param1",
                        "label": "Float Parameter",
                        "subtitle": "",
                        "value": {"parameter_type": "float", "default": 0.0},
                    }
                ],
            },
        ),
        (
            "/process_texts_with_schema",
            {
                "inputs": [
                    {
                        "input_type": "batchtext",
                        "key": "text_inputs",
                        "label": "Batch Text Inputs",
                        "subtitle": "",
                    }
                ],
                "parameters": [
                    {
                        "key": "param1",
                        "label": "Int Parameter",
                        "subtitle": "",
                        "value": {"parameter_type": "int", "default": 1},
                    }
                ],
            },
        ),
        (
            "/process_files_with_schema",
            {
                "inputs": [
                    {
                        "input_type": "batchfile",
                        "key": "file_inputs",
                        "label": "Batch File Inputs",
                        "subtitle": "",
                    }
                ],
                "parameters": [
                    {
                        "key": "param1",
                        "label": "Ranged Float Parameter",
                        "subtitle": "",
                        "value": {
                            "parameter_type": "ranged_float",
                            "default": 0.0,
                            "range": {"min": 0.0, "max": 1.0},
                        },
                    }
                ],
            },
        ),
        (
            "/process_directory_with_schema",
            {
                "inputs": [
                    {
                        "input_type": "directory",
                        "key": "dir_input",
                        "label": "Directory Input",
                        "subtitle": "",
                    }
                ],
                "parameters": [
                    {
                        "key": "param1",
                        "label": "Ranged Int Parameter",
                        "subtitle": "",
                        "value": {
                            "parameter_type": "ranged_int",
                            "default": 0,
                            "range": {"min": 0, "max": 10},
                        },
                    }
                ],
            },
        ),
    ],
)
def test_task_schema(app, endpoint, expected_response):
    response = app.get(f"{endpoint}/task_schema")
    assert response.status_code == 200
    assert response.json == expected_response


@pytest.mark.parametrize(
    "endpoint,data,expected_response",
    [
        (
            "/process_text_with_schema",
            {"inputs": {"text_input": {"text": "Sample text"}}, "parameters": {"param1": "default"}},
            {"output_type": "text", "value": "processed_text.txt", "title": "Sample text", "subtitle": None},
        ),
        (
            "/process_textarea_with_schema",
            {"inputs": {"text_input": {"text": "Sample text"}}, "parameters": {"param1": "option_1"}},
            {"output_type": "text", "value": "processed_text.txt", "title": "Sample text", "subtitle": None},
        ),
        (
            "/process_file_with_schema",
            {"inputs": {"file_input": {"path": "/path/to/image.jpg"}}, "parameters": {"param1": 0.0}},
            {
                "output_type": "file",
                "file_type": "img",
                "path": "processed_image.img",
                "title": "/path/to/image.jpg",
                "subtitle": None,
            },
        ),
        (
            "/process_texts_with_schema",
            {"inputs": {"text_inputs": {"texts": [{"text": "Sample text"}]}}, "parameters": {"param1": 0}},
            {
                "output_type": "batchtext",
                "texts": [
                    {
                        "output_type": "text",
                        "value": "processed_text.txt",
                        "title": "Sample text",
                        "subtitle": None,
                    }
                ],
            },
        ),
        (
            "/process_files_with_schema",
            {
                "inputs": {"file_inputs": {"files": [{"path": "/path/to/image.jpg"}]}},
                "parameters": {"param1": 0.0},
            },
            {
                "output_type": "batchfile",
                "files": [
                    {
                        "output_type": "file",
                        "file_type": "img",
                        "path": "processed_image.img",
                        "title": "/path/to/image.jpg",
                        "subtitle": None,
                    }
                ],
            },
        ),
        (
            "/process_directory_with_schema",
            {"inputs": {"dir_input": {"path": "/path/to/directory"}}, "parameters": {"param1": 0}},
            {
                "output_type": "directory",
                "path": "processed_images",
                "title": "/path/to/directory",
                "subtitle": "",
            },
        ),
    ],
)
def test_valid_file_request_for_endpoint_with_task_schema(app, endpoint, data, expected_response):
    response = app.post(endpoint, json=data)
    assert response.status_code == 200
    assert response.json == expected_response


def test_bad_request_input_validation_error_for_endpoint_with_schema(app):
    data = {
        "inputs": {"file_inputs": {"files": [{"path": "/path/to/image.jpg"}]}},
        "parameters": {"INCORRECT KEY": 0.0},
    }

    response = app.post("/process_files_with_schema", json=data)
    assert response.status_code == 400
    assert "Keys mismatch." in response.json["error"]


def test_bad_request_param_validation_error_for_endpoint_with_schema(app):
    data = {
        "inputs": {"INCORRECT_KEY": {"files": [{"path": "/path/to/image.jpg"}]}},
        "parameters": {"param1": 0.0},
    }

    response = app.post("/process_files_with_schema", json=data)
    assert response.status_code == 400
    assert "Keys mismatch." in response.json["error"]


def test_invalid_request_param_validation_error_for_endpoint_with_schema(app):
    data = {
        "inputs": {"file_inputs": {"incorret_key": [{"path": "/path/to/image.jpg"}]}},
        "parameters": {"param1": 0.0},
    }

    response = app.post("/process_files_with_schema", json=data)
    assert response.status_code == 400
    assert "Field required" in response.json["error"][0]["msg"]


def test_set_url(client):
    new_url = "http://localhost:8000/sentimentanalysis"
    client.set_url(new_url)
    assert client.url == new_url


def test_valid_text_request(app):
    data = {
        "inputs": {"text_inputs": {"texts": [{"text": "Sample text"}]}},
        "parameters": {"param1": 0},
    }

    response = app.post("/process_texts", json=data)
    assert response.status_code == 200
    assert response.json == {
        "output_type": "batchtext",
        "texts": [
            {"output_type": "text", "value": "processed_text.txt", "title": "Sample text", "subtitle": None}
        ],
    }


@patch("requests.post")
def test_valid_text_request_client(mock_post, client: MLClient):
    data = {
        "inputs": {"text_inputs": {"texts": [{"text": "Sample text"}]}},
        "parameters": {"param1": 0},
    }

    mock_post.return_value = mock_post_request("http://127.0.0.1:5000/process_texts", json=data)
    response = client.request(data["inputs"], data["parameters"])
    assert response == {
        "output_type": "batchtext",
        "texts": [
            {"output_type": "text", "value": "processed_text.txt", "title": "Sample text", "subtitle": None}
        ],
    }


def test_invalid_text_request(app):
    data = {
        "inputs": {"KEY_INVALID": {"texts": [{"text": "Sample text"}]}},
        "parameters": {"param1": "Sample value for parameter"},
    }
    response = app.post("/process_texts", json=data)
    assert response.status_code == 400
    assert "VALIDATION_ERROR" == response.json["status"]
    assert "Keys mismatch. The input schema has" in response.json["error"]


def test_valid_file_request(app):
    data = {
        "inputs": {"file_inputs": {"files": [{"path": "/path/to/image.jpg"}]}},
        "parameters": {"param1": 0.0},
    }

    response = app.post("/process_files", json=data)
    assert response.status_code == 200
    assert response.json == {
        "output_type": "batchfile",
        "files": [
            {
                "output_type": "file",
                "file_type": "img",
                "path": "processed_image.img",
                "title": "/path/to/image.jpg",
                "subtitle": None,
            }
        ],
    }


@patch("requests.post")
def test_valid_file_request_client(mock_post, client):
    data = {
        "inputs": {"file_inputs": {"files": [{"path": "/path/to/image.jpg"}]}},
        "parameters": {"param1": 0.0},
    }

    mock_post.return_value = mock_post_request("http://127.0.0.1:5000/process_files", json=data)
    response = client.request(data["inputs"], data["parameters"])

    assert response == {
        "output_type": "batchfile",
        "files": [
            {
                "output_type": "file",
                "file_type": "img",
                "path": "processed_image.img",
                "title": "/path/to/image.jpg",
                "subtitle": None,
            }
        ],
    }


@patch("requests.post")
def test_invalid_reponse_not_json(mock_post, client):
    data = {
        "inputs": {"file_inputs": {"files": [{"path": "/path/to/image.jpg"}]}},
        "parameters": {"param1": 0.0},
    }
    mock_post.return_value = mock_post_request("http://127.0.0.1:5000/process_files", json=data)
    mock_post.return_value.headers = {"Content-Type": "text/html"}
    response = client.request(data["inputs"], data["parameters"])
    assert "Unknown error" in response["status"]
    assert "errors" in response
    assert "Unknown error" in response["errors"][0]["msg"]


@patch("requests.post")
def test_non_200_reponse(mock_post, client):
    data = {
        "inputs": {"file_inputs": {"files": [{"path": "/path/to/image.jpg"}]}},
        "parameters": {"param1": 0.0},
    }
    mock_post.return_value = MockResponse(
        response=Response(response=json.dumps({"status": "failed"}), status=400, mimetype="application/json")
    )
    mock_post.return_value.status_code = 400
    response = client.request(data["inputs"], data["parameters"])
    assert {"status": "failed"} == response


def test_invalid_file_request(app):
    data = {
        "inputs": {"file_inputs": {"INVALID_KEY": [{"path": "/path/to/image.jpg"}]}},
        "parameters": {},
    }
    response = app.post("/process_files", json=data)

    assert response.status_code == 400
    assert "VALIDATION_ERROR" == response.json["status"]
    assert "Field required" == response.json["error"][0]["msg"]
