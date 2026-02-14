import math

def floor(x):
    return math.floor(x)

def nroot(n: int, x: int) -> int:
    return round(x ** (1 / n))

def reverse(str: str) -> str:
    return str[::-1]

def validAnagram(str1: str, str2: str) -> bool:
    return sorted(str1) == sorted(str2)

def sort(*args:str) -> str:
    return sorted(args)