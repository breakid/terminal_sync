"""Executes the terminal_sync server when the module is run"""

# Standard Libraries
from argparse import ArgumentParser

# Internal Libraries
from terminal_sync.api import run

parser = ArgumentParser()
parser.add_argument("--host", dest="host", default="127.0.0.1", help="The host address where the server will bind")
parser.add_argument("--port", dest="port", default=8000, type=int, help="The host port where the server will bind")
args = parser.parse_args()

run(host=args.host, port=args.port)
