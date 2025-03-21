from fastapi import Request

# dependency to make it explicit that routers are accessing hidden state
def get_cache_db(request: Request):
    return request.state.cache_db_pool