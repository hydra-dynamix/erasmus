#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Third-party imports






 
 
 
 
 
#
-
.
T
a
a
a
a
c
d
d
h
i
i
i
i
i
i
m
m
m
m
m
n
n
o
o
o
o
p
p
p
p
p
p
p
p
r
r
r
r
r
r
s
s
s
s
s
t
t
t
t
t
t
t
u
y
y
y



# Source: /tmp/pytest-of-bakobi/pytest-39/test_package_project0/project/main.py

def main():
data = pd.read_csv('data.csv')
result = process_data(data)
print(result)

if __name__ == '__main__':
main()

# Source: /tmp/pytest-of-bakobi/pytest-39/test_package_project0/project/utils/__init__.py

def process_data(data):
return np.mean(data) + stats.sem(data)