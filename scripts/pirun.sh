#!/bin/bash

instruction_file="${1:-instructions.md}"

pi -p --no-session \
     --tools read,bash,edit,write \
     "$instruction_file"
