from fastapi import Request
from ..models.graph_model import Graph, GraphType

# dependency to make it explicit that routers are accessing hidden state
# to avoid model name hardcoding in routers
# TODO clean up hardcoded names; use enums
def get_following_graph(request: Request) -> Graph:
    return request.state.graphs[GraphType.following]

def get_engagement_graph(request: Request) -> Graph:
    return request.state.graphs[GraphType.engagement]