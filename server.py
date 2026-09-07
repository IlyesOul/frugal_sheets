#!/usr/bin/env python3

import json
import mimetypes
import os

from wsgiref.simple_server import make_server

import sheet_api


LOCATION = os.path.realpath(os.path.dirname(__file__))


def parse_post(environ):
    try:
        body_size = int(environ.get("CONTENT_LENGTH", 0))
    except Exception:
        body_size = 0

    body = environ["wsgi.input"].read(body_size)
    try:
        return json.loads(body)
    except Exception:
        return {}


def application(environ, start_response):
    custom_headers = []
    path = (environ.get("PATH_INFO", "") or "").lstrip("/")
    if path in sheet_api.funcs:
        out = sheet_api.dispatch(path, parse_post(environ))
        body = json.dumps(out).encode("utf-8")
        status = "200 OK"
        type_ = "application/json"
    else:
        if path == "":
            path = "index.html"

        static_file = path

        if static_file.startswith("ui/"):
            static_file = static_file[3:]

        test_fname = os.path.join(LOCATION, "ui", static_file)
        try:
            status = "200 OK"
            with open(test_fname, "rb") as f:
                body = f.read()
            type_ = mimetypes.guess_type(test_fname)[0] or "text/plain"
        except FileNotFoundError:
            status = "404 FILE NOT FOUND"
            body = test_fname.encode("utf-8")
            type_ = "text/plain"

    len_ = str(len(body))
    headers = [("Content-type", type_), ("Content-length", len_), *custom_headers]
    start_response(status, headers)
    return [body]


if __name__ == "__main__":
    PORT = 6101
    print("starting server.")
    print(f"navigate to http://localhost:{PORT}/ to use the spreadsheet software")
    with make_server("", PORT, application) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down.")
            httpd.server_close()
