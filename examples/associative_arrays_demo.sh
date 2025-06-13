#!/usr/bin/env psh
# Associative Arrays Demo for PSH
# This script demonstrates the associative array functionality

echo "=== PSH Associative Arrays Demo ==="
echo

# Test 1: Basic associative array creation
echo "1. Creating associative array with declare -A"
declare -A colors
echo "✓ Created associative array 'colors'"

# Test 2: Setting values with simple keys
echo
echo "2. Setting values with simple keys"
colors[red]="#FF0000"
colors[green]="#00FF00"
colors[blue]="#0000FF"
echo "✓ Set colors[red], colors[green], colors[blue]"

# Test 3: Accessing values
echo
echo "3. Accessing values"
echo "colors[red] = ${colors[red]}"
echo "colors[green] = ${colors[green]}"
echo "colors[blue] = ${colors[blue]}"

# Test 4: Keys with spaces (quoted keys)
echo
echo "4. Using keys with spaces"
colors["light blue"]="#ADD8E6"
colors['dark red']="#8B0000"
echo "colors[\"light blue\"] = ${colors[light blue]}"
echo "colors['dark red'] = ${colors[dark red]}"

# Test 5: Variable keys
echo
echo "5. Using variable keys"
key_var="purple"
colors[$key_var]="#800080"
echo "key_var = $key_var"
echo "colors[\$key_var] = ${colors[$key_var]}"

# Test 6: Array initialization syntax
echo
echo "6. Array initialization syntax"
declare -A fruits=([apple]="red" [banana]="yellow" [grape]="purple")
echo "fruits[apple] = ${fruits[apple]}"
echo "fruits[banana] = ${fruits[banana]}"
echo "fruits[grape] = ${fruits[grape]}"

# Test 7: Arithmetic in keys (treated as strings)
echo
echo "7. Arithmetic expressions as keys (treated as strings)"
declare -A calc
calc[2+2]="not four"
calc[3*3]="not nine"
echo "calc[2+2] = ${calc[2+2]}"
echo "calc[3*3] = ${calc[3*3]}"

# Test 8: Compound keys
echo
echo "8. Compound keys with variable expansion"
prefix="color"
suffix="code"
colors[${prefix}_${suffix}]="#123456"
echo "colors[\${prefix}_\${suffix}] = ${colors[color_code]}"

echo
echo "=== Demo Complete ==="
echo "Associative arrays in PSH support:"
echo "  ✓ declare -A array_name"
echo "  ✓ array[key]=value assignments"
echo "  ✓ \${array[key]} access"
echo "  ✓ Quoted keys with spaces"
echo "  ✓ Variable keys"
echo "  ✓ Initialization syntax"
echo "  ✓ Complex key expressions"