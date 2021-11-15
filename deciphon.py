import io

import fasta_reader as fr
import xxhash
from flask import Flask, jsonify, request

app = Flask(__name__)


def missing_params_response(params):
    error = {"response": "invalid_request", "error": f"Missing parameters: {params}"}
    return jsonify(error)


def invalid_data_format_response(data_format):
    error = {
        "response": "invalid_data_format",
        "error": f"Invalid data format: {data_format}",
    }
    return jsonify(error)


def data_parsing_error_response(error):
    error = {
        "response": "data_parsing_error",
        "error": f"{error}",
    }
    return jsonify(error)


def stream_hash(stream):
    pass
    # xxhash


@app.post("/submit")
def submit():
    expected_params = ["db_name", "multi_hits", "hmmer3_compat"]
    missing = [p for p in expected_params if p not in request.form]
    if len(missing) > 0:
        return missing_params_response(missing)

    db_name = request.form["db_name"]
    multi_hits = request.form["multi_hits"]
    hmmer3_compat = request.form["hmmer3_compat"]
    data_format = request.form["data_format"]
    if data_format != "fasta":
        return invalid_data_format_response(data_format)

    with io.StringIO(request.form["data"]) as file:
        try:
            items = fr.read_fasta(file).read_items()
            with io.StringIO() as out:
                with fr.write_fasta(out) as ofile:
                    pass
        except fr.ParsingError as e:
            return data_parsing_error_response(str(e))

    return jsonify(request.form)
