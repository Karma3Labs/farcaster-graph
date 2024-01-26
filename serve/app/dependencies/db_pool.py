from fastapi import Request

# dependency to make it explicit that routers are accessing hidden state
def get_db(request: Request):
    return request.state.db_pool