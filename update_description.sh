#!/bin/bash

set -ex

LOC=$(wc -l bazoola/*.py | tail -1 | awk '{print $1}')
gh repo edit -d "A toy database in $LOC LOC"
