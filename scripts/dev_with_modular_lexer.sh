#!/bin/bash
# Development script to run psh with ModularLexer enabled

echo "Starting PSH with ModularLexer enabled..."
echo "To disable, unset PSH_USE_MODULAR_LEXER"
echo ""

export PSH_USE_MODULAR_LEXER=true
python -m psh "$@"