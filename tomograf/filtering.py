import numpy as np

def get_filter(limit=21):
    base = np.array([1])
    arr = [-4 / (np.pi**2 * x**2) if x % 2 else 0 for x in range(limit)]
    return np.append(np.flip(arr), np.append(base, arr));