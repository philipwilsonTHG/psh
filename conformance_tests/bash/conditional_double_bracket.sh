#!/bin/bash
# Test the [[ ... ]] conditional expression for string comparison

VAR="hello"
if [[ "$VAR" == "hello" ]]; then
  echo "String comparison success"
fi

if [[ "abc" != "def" ]]; then
  echo "String inequality success"
fi

# Test pattern matching
if [[ "abcdef" == abc* ]]; then
    echo "Pattern matching success"
fi
