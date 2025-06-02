export PS1='PSH> '
export PS2='... '
if true; then
echo SUCCESS
fi
echo '---DIVIDER---'
for i in 1 2 3; do
echo NUM: $i
done
echo '---DIVIDER---'
i=0
while [ $i -lt 3 ]; do
echo COUNT: $i
i=$((i+1))
done
echo '---DIVIDER---'
greet() {
echo Hello, $1!
}
greet World
echo '---DIVIDER---'
x=2
case $x in
1) echo one;;
2) echo two;;
*) echo other;;
esac
echo '---DIVIDER---'
for i in 1 2; do
if [ $i -eq 1 ]; then
echo FIRST
else
echo SECOND
fi
done
echo '---DIVIDER---'
echo one \
two \
three
echo '---DIVIDER---'
cat <<EOF
line1
line2
EOF
echo '---DIVIDER---'
