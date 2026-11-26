#!/usr/bin/env python3
"""Local stand-in for the S3-style bucket, for trying the chat on one machine.

    python3 mock-bucket.py            # then open http://localhost:8000/ephemeral-room.html
    python3 mock-bucket.py 9000       # different port
    python3 mock-bucket.py --read-only   # refuse writes, to see the invite-code fallback

Serves the files in this folder, and answers list / read / write / delete the
way the chat page expects. Written objects live in memory only and vanish when
you stop the server. Listens on localhost only. Not for production use.
"""
import datetime, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
READ_ONLY = "--read-only" in sys.argv
PORT = next((int(a) for a in sys.argv[1:] if a.isdigit()), 8000)
TYPES = {".html": "text/html; charset=utf-8", ".json": "application/json", ".md": "text/plain; charset=utf-8"}
objects = {}  # key -> (bytes, modified time)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path.split("?")[0]))

    def reply(self, code, body=b"", ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def key(self):
        return unquote(urlsplit(self.path).path).lstrip("/")

    def do_GET(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        key = self.key()
        if key == "" and "list-type" in query:  # S3 ListObjectsV2
            prefix = query.get("prefix", [""])[0]
            xml = ['<?xml version="1.0" encoding="UTF-8"?>',
                   '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>false</IsTruncated>']
            for k in sorted(objects):
                if k.startswith(prefix):
                    stamp = datetime.datetime.fromtimestamp(objects[k][1], datetime.timezone.utc)
                    xml.append("<Contents><Key>%s</Key><LastModified>%s</LastModified></Contents>"
                               % (escape(k), stamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"))
            xml.append("</ListBucketResult>")
            return self.reply(200, "".join(xml).encode(), "application/xml")
        if key in objects:
            return self.reply(200, objects[key][0])
        # Otherwise a static file from this folder (never outside it).
        path = os.path.realpath(os.path.join(HERE, key))
        if path.startswith(HERE + os.sep) and os.path.isfile(path) and os.path.splitext(path)[1] in TYPES:
            with open(path, "rb") as f:
                return self.reply(200, f.read(), TYPES[os.path.splitext(path)[1]])
        self.reply(404, b"<Error><Code>NoSuchKey</Code></Error>", "application/xml")

    def do_PUT(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if READ_ONLY:
            return self.reply(403, b"<Error><Code>AccessDenied</Code></Error>", "application/xml")
        objects[self.key()] = (body, time.time())
        self.reply(200)

    def do_DELETE(self):
        if READ_ONLY:
            return self.reply(403, b"<Error><Code>AccessDenied</Code></Error>", "application/xml")
        objects.pop(self.key(), None)
        self.reply(204)


if __name__ == "__main__":
    print("Mock bucket on http://localhost:%d/ephemeral-room.html%s (Ctrl+C to stop)"
          % (PORT, "  [read-only]" if READ_ONLY else ""))
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
