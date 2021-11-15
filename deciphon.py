import dataclasses
import io
import json
import sqlite3

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


def database_not_found_response(name):
    error = {
        "response": "database_not_found",
        "error": f"{name} was not found",
    }
    return jsonify(error)


def stream_hash(data):
    return xxhash.xxh64(data).intdigest()


def read_fasta(data):
    with io.StringIO(data) as file:
        return fr.read_fasta(file).read_items()


def standardize_fasta_data(raw):
    items = read_fasta(raw)
    with io.StringIO() as tmp:
        with fr.write_fasta(tmp, ncols=60) as file:
            for item in items:
                print(item.defline)
                print(item.sequence)
                file.write_item(item.defline, item.sequence)

            return tmp.getvalue()


@dataclasses.dataclass
class SubmitRequest:
    db_name: str
    multi_hits: str
    hmmer3_compat: str
    data_format: str
    data: str

    def __init__(
        self,
        db_name: str,
        multi_hits: str,
        hmmer3_compat: str,
        data_format: str,
        data: str,
    ):
        assert multi_hits in ["true", "false"]
        assert hmmer3_compat in ["true", "false"]
        assert data_format == "fasta"
        self.db_name = db_name
        self.multi_hits = multi_hits
        self.hmmer3_compat = hmmer3_compat
        self.data_format = data_format
        self.data = data

    def job_id(self) -> int:
        return stream_hash(json.dumps(dataclasses.asdict(self)))


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

    try:
        data = standardize_fasta_data(request.form["data"])
    except fr.ParsingError as e:
        return data_parsing_error_response(str(e))

    req = SubmitRequest(db_name, multi_hits, hmmer3_compat, data_format, data)
    job_id = req.job_id()
    print(job_id)
    con = sqlite3.connect("deciphon.sqlite3")
    cur = con.cursor()
    cur.execute("SELECT id FROM db WHERE name = ?", [db_name])
    rows = list(cur)
    if len(rows) < 1:
        return database_not_found_response(db_name)
    assert len(rows) == 1
    # con.execute("INSERT INTO job VALUES()")
    # id INTEGER PRIMARY KEY UNIQUE NOT NULL,
    # db_id INTEGER REFERENCES db (id) NOT NULL,
    # multi_hits INTEGER NOT NULL,
    # hmmer3_compat INTEGER NOT NULL,
    # state TEXT CHECK(state IN ('pend', 'run', 'done', 'fail')) NOT NULL,
    # error TEXT NOT NULL,
    # submission INTEGER NOT NULL,
    # exec_started INTEGER NOT NULL,
    # exec_ended INTEGER NOT NULL
    con.close()
    return jsonify({"response": "ok", "job_id": job_id})
