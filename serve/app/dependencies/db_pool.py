from fastapi import Request


# dependency to make it explicit that routers are accessing a hidden state
def get_db(request: Request):
    return request.state.db_pool


def get_cache_db(request: Request):
    return request.state.cache_db_pool
