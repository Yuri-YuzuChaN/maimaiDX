import re
import time


def hash(qq: int):
    days = int(time.strftime("%d", time.localtime(time.time()))) + 31 * int(
        time.strftime("%m", time.localtime(time.time()))) + 77
    return (days * qq) >> 8

def regular(s: str):
    s = s.replace('^', r'\^')
    s = s.replace('$', r'\$')
    s = s.replace('.', r'\.')
    s = s.replace('|', r'\|')
    s = s.replace('+', r'\+')
    s = s.replace('*', r'\*')
    s = s.replace('?', r'\?')
    s = s.replace('{', r'\{')
    s = s.replace('}', r'\}')
    s = s.replace('(', r'\(')
    s = s.replace(')', r'\)')
    return s

def search_dict(m_dict, name):
    result = []
    for key, value in m_dict.items():
        r_key = re.compile(regular(key), re.I)
        if r_key.search(name):
            for v in value:
                if v not in result:
                    result.append(v)
    return result