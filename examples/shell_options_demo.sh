#!/usr/bin/env psh
# Demonstrate shell options: set -e, -u, -x, -o pipefail

echo "=== Shell Options Demo ==="
echo

# Test xtrace (-x)
echo "1. Testing xtrace (set -x):"
set -x
echo "This command is traced"
VAR="traced value"
echo "Variable is: $VAR"
set +x
echo "Tracing is now off"
echo

# Test nounset (-u)
echo "2. Testing nounset (set -u):"
echo "Before enabling nounset, undefined variable returns empty:"
echo "UNDEFINED_VAR='$UNDEFINED_VAR'"

set -u
echo "After set -u, trying to access undefined variable..."
# This should cause an error:
# echo "UNDEFINED_VAR='$UNDEFINED_VAR'"

# But default expansions should work:
echo "With default: '${UNDEFINED_VAR:-default value}'"
set +u
echo

# Test errexit (-e)
echo "3. Testing errexit (set -e):"
set -e
echo "With errexit enabled, false command would exit the script"
# false  # This would exit the script
echo "But commands in conditionals are exempt:"
if false; then
    echo "This won't print"
else
    echo "False in if statement doesn't trigger errexit"
fi

# Also && and || are exempt
false || echo "False with || doesn't trigger errexit"
true && echo "True with && works normally"
set +e
echo

# Test pipefail
echo "4. Testing pipefail (set -o pipefail):"
echo "Without pipefail:"
false | true
echo "Exit status: $?"

set -o pipefail
echo "With pipefail:"
false | true
echo "Exit status: $?"

# More complex pipeline
true | false | true
echo "Exit status of 'true | false | true': $?"
set +o pipefail
echo

# Combine options
echo "5. Combining options:"
set -eux
echo "All options enabled"
VAR="combined test"
echo "$VAR"
set +eux

echo
echo "=== Demo Complete ==="