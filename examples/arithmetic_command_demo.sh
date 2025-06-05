#!/bin/bash
# Demonstration of arithmetic command syntax ((expression))

echo "=== Arithmetic Command Syntax Demo ==="
echo

echo "1. Basic assignment and exit status:"
((x = 10))
echo "   ((x = 10)) - exit status: $? (0 = success)"
echo "   x = $x"

((y = 0))
echo "   ((y = 0)) - exit status: $? (1 = failure, because result is 0)"
echo "   y = $y"
echo

echo "2. Increment and decrement operations:"
i=5
echo "   Initial i = $i"
((i++))
echo "   After ((i++)): i = $i"
((++i))
echo "   After ((++i)): i = $i"
((i--))
echo "   After ((i--)): i = $i"
((--i))
echo "   After ((--i)): i = $i"
echo

echo "3. Conditional testing with ((...)):"
x=7
echo "   x = $x"
if ((x > 5)); then
    echo "   ((x > 5)) is true"
fi

if ((x % 2 == 1)); then
    echo "   ((x % 2 == 1)) is true - x is odd"
fi
echo

echo "4. Using ((...)) in a while loop:"
echo -n "   Counting: "
i=0
while ((i < 5)); do
    echo -n "$i "
    ((i++))
done
echo
echo

echo "5. Multiple expressions in one command:"
((a=2, b=3, c=a*b))
echo "   ((a=2, b=3, c=a*b))"
echo "   Result: a=$a, b=$b, c=$c"
echo

echo "6. Ternary operator:"
x=10
((result = x > 5 ? 100 : 50))
echo "   x=$x"
echo "   ((result = x > 5 ? 100 : 50))"
echo "   result = $result"
echo

echo "7. Compound assignments:"
x=10
echo "   Initial x = $x"
((x += 5))
echo "   After ((x += 5)): x = $x"
((x *= 2))
echo "   After ((x *= 2)): x = $x"
((x /= 3))
echo "   After ((x /= 3)): x = $x"
echo

echo "8. Exit status in conditional execution:"
echo -n "   ((5 > 3)) && echo 'true': "
((5 > 3)) && echo "true"
echo -n "   ((2 > 5)) || echo 'false': "
((2 > 5)) || echo "false"
echo

echo "9. Bitwise operations:"
((flags = 0x0F))
printf "   Initial flags = 0x%02X\n" $flags
((flags &= 0x03))
printf "   After ((flags &= 0x03)): flags = 0x%02X\n" $flags
((flags |= 0x10))
printf "   After ((flags |= 0x10)): flags = 0x%02X\n" $flags
echo

echo "10. Complex conditions:"
x=7
y=3
if ((x > 5 && y < 5)); then
    echo "   ((x > 5 && y < 5)) is true for x=$x, y=$y"
fi

if ((x > 10 || y > 2)); then
    echo "   ((x > 10 || y > 2)) is true for x=$x, y=$y"
fi
echo

echo "11. Function with arithmetic conditions:"
is_prime() {
    local n=$1
    local i
    
    ((n < 2)) && return 1
    
    for ((i=2; i*i<=n; i++)); do
        if ((n % i == 0)); then
            return 1
        fi
    done
    return 0
}

echo -n "   Prime numbers from 1 to 20: "
for ((i=1; i<=20; i++)); do
    if is_prime $i; then
        echo -n "$i "
    fi
done
echo
echo

echo "12. Demonstrating the difference between ((...)) and $((...)):"
x=5
echo "   x = $x"
echo "   ((x + 3)) produces no output, just sets exit status"
((x + 3))
echo "   Exit status: $?"
echo "   echo \$((x + 3)) outputs: $((x + 3))"
echo

echo "=== End of Demo ==="