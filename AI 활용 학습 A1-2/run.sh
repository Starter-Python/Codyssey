#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python travel_planner.py "$@"
