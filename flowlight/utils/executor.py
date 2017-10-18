__executor = None


def get_executor(nodes=4):
    global __executor
    if __executor is None:
        from concurrent.futures import ThreadPoolExecutor
        __executor = ThreadPoolExecutor(max_workers=min(nodes, 4))
    return __executor
