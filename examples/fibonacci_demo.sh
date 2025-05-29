#!/usr/bin/env psh
# Fibonacci demonstration using arithmetic expansion
# This works with psh's current implementation

echo "=== Fibonacci Calculator using Arithmetic Expansion ==="
echo

# Calculate F(10) step by step
echo "Calculating F(10) step by step:"
n=10
a=0
b=1

echo "F(0) = $a"
echo "F(1) = $b"

# Calculate F(2)
c=$((a + b))
echo "F(2) = $((0 + 1)) = $c"
a=$b
b=$c

# Calculate F(3)
c=$((a + b))
echo "F(3) = $((1 + 1)) = $c"
a=$b
b=$c

# Calculate F(4)
c=$((a + b))
echo "F(4) = $((1 + 2)) = $c"
a=$b
b=$c

# Calculate F(5)
c=$((a + b))
echo "F(5) = $((2 + 3)) = $c"
a=$b
b=$c

# Calculate F(6)
c=$((a + b))
echo "F(6) = $((3 + 5)) = $c"
a=$b
b=$c

# Calculate F(7)
c=$((a + b))
echo "F(7) = $((5 + 8)) = $c"
a=$b
b=$c

# Calculate F(8)
c=$((a + b))
echo "F(8) = $((8 + 13)) = $c"
a=$b
b=$c

# Calculate F(9)
c=$((a + b))
echo "F(9) = $((13 + 21)) = $c"
a=$b
b=$c

# Calculate F(10)
c=$((a + b))
echo "F(10) = $((21 + 34)) = $c"

echo
echo "=== Arithmetic Expression Examples ==="
echo

# Various arithmetic operations
x=55  # F(10)
y=34  # F(9)
echo "F(10) = $x"
echo "F(9) = $y"
echo
echo "F(10) + F(9) = $((x + y))"
echo "F(10) - F(9) = $((x - y))"
echo "F(10) * 2 = $((x * 2))"
echo "F(10) / 5 = $((x / 5))"
echo "F(10) % 10 = $((x % 10))"

echo
echo "=== Testing Other Arithmetic Features ==="
echo

# Increment operators
i=0
echo "Initial i = $i"
i=$((i + 1))
echo "After i = i + 1: $i"
i=$((i + 1))
echo "After another increment: $i"

# Comparison operators
echo
echo "Comparisons:"
echo "Is F(10) > F(9)? $((x > y)) (1 = true, 0 = false)"
echo "Is F(10) == 55? $((x == 55))"
echo "Is F(9) < 40? $((y < 40))"

# Bitwise operations
echo
echo "Bitwise operations on F(6) = 8:"
echo "8 & 12 = $((8 & 12))"
echo "8 | 4 = $((8 | 4))"
echo "8 << 1 = $((8 << 1))"
echo "8 >> 1 = $((8 >> 1))"

# Ternary operator
echo
echo "Ternary operator:"
echo "Is F(10) even? $((x % 2 == 0 ? 1 : 0)) (1 = yes, 0 = no)"

# Hex and octal
echo
echo "Number bases:"
echo "Hex 0xFF = $((0xFF))"
echo "Octal 010 = $((010))"
echo "Binary-like: 2^8 = $((2 ** 8))"