import sys

path = sys.argv[1]
with open(path, "rb") as f:
    data = f.read()
for i, b in enumerate(data):
    if b != 0:
        print(i)
        break
else:
    print(-1)
