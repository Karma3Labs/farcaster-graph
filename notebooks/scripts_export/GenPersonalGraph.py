#!/usr/bin/env python
# coding: utf-8

# In[6]:


get_ipython().run_line_magic('pip', 'install igraph niquests pandas')


# In[7]:


import pandas as pd
import numpy as np
import igraph as ig
import time
import itertools
import requests
import random
import asyncio
from niquests import AsyncSession, Response

pd.set_option("mode.copy_on_write", True)


# In[8]:


import IPython
IPython.version_info


# In[9]:


USE_PANDAS_PERF=True # if multiple CPU cores are available


# In[33]:


async def _get_direct_edges_df(
  fids,
  df,
  max_neighbors,
):
    # WARNING we are operating on a shared dataframe...
    # ...inplace=False by default, explicitly setting here for emphasis
    out_df = df[df['i'].isin(fids)].sort_values(by=['v'], ascending=False, inplace=False)[:max_neighbors]
    return out_df


# In[65]:


async def find_vertex_idx(ig, fid):
    try:
        return ig.vs.find(name=fid).index
    except:
        return None

async def _fetch_korder_neighbors(
  fids,graph,max_degree,max_neighbors,min_degree = 1
):

    # vids = [find_vertex_idx(graph.graph, fid) for fid in fids]
    # vids = list(filter(None, vids)) # WARNING - this filters vertex id 0 also
    vids = [vid for fid in fids for vid in [await find_vertex_idx(graph, fid)] if vid is not None ]
    if len(vids) <= 0:
        raise Exception(f"{fids}:Invalid fids")
    try:
        klists = []
        mindist_and_order = min_degree
        limit = max_neighbors
        while mindist_and_order <= max_degree:
            neighbors = graph.neighborhood(
                vids, order=mindist_and_order, mode="out", mindist=mindist_and_order
            )
            # TODO prune the graph after sorting by edge weight
            klists.append(graph.vs[neighbors[0][:limit]]["name"])
            limit = limit - len(neighbors[0])
            if limit <= 0:
                break # we have reached limit of neighbors
            mindist_and_order += 1
        # end of while
        return set(itertools.chain(*klists))
    except ValueError:
        raise Exception(f"{fids}:Neighbors not found")


# In[60]:


async def _get_neighbors_edges(
  fids, df, graph, max_degree, max_neighbors,
):

    start_time = time.perf_counter()
    neighbors_df = await _get_direct_edges_df(fids, df, max_neighbors)
    print(f"{fids}:direct_edges_df took {time.perf_counter() - start_time} secs"
          f" for {len(neighbors_df)} first degree edges")
    max_neighbors = max_neighbors - len(neighbors_df)
    if max_neighbors > 0 and max_degree > 1:

        start_time = time.perf_counter()
        k_neighbors_list = await _fetch_korder_neighbors(fids, graph, max_degree, max_neighbors, min_degree=2)
        print(f"{fids}:{time.perf_counter() - start_time} secs for {len(k_neighbors_list)} neighbors")

        start_time  = time.perf_counter()
        if USE_PANDAS_PERF:
            # if multiple CPU cores are available
            k_df = df.query('i in @k_neighbors_list').query('j in @k_neighbors_list')
        else:
            # filter with an '&' is slower because of the size of the dataframe
            # split the filtering so that indexes can be used if present
            # k_df = graph.df[graph.df['i'].isin(k_neighbors_list) & graph.df['j'].isin(k_neighbors_list)]
            k_df = df[df['i'].isin(k_neighbors_list)]
            k_df = k_df[k_df['j'].isin(k_neighbors_list)]
        # .loc will throw KeyError when fids have no outgoing actions
        ### in other words, some neighbor fids may not be present in 'i'
        # k_df = graph.df.loc[(k_neighbors_list, k_neighbors_list)]
        print(f"{fids}:k_df took {time.perf_counter() - start_time} secs for {len(k_df)} edges")

        start_time  = time.perf_counter()
        neighbors_df = pd.concat([neighbors_df, k_df])
        print(f"{fids}:neighbors_df concat took {time.perf_counter() - start_time} secs"
              f" for {len(neighbors_df)} edges")

    return neighbors_df


# In[61]:


async def get_neighbors_list(
  fids, df, graph, max_degree = 2, max_neighbors = 100,
):
    df = await _get_neighbors_edges(fids, df, graph, max_degree, max_neighbors)
    # WARNING we are operating on a shared dataframe...
    # ...inplace=False by default, explicitly setting here for emphasis
    out_df = df.groupby(by='j')[['v']].sum().sort_values(by=['v'], ascending=False, inplace=False)
    return out_df.index.to_list()


# In[62]:


async def go_eigentrust(
    pretrust, max_pt_id, localtrust, max_lt_id,
):
    start_time = time.perf_counter()

    lt_len_before = len(localtrust)
    localtrust[:] = (x for x in localtrust if x["i"] != x["j"])
    lt_len_after = len(localtrust)
    if lt_len_before != lt_len_after:
        print(f"dropped {lt_len_before-lt_len_after} records with i == j")

    req = {
        "pretrust": {
            "scheme": "inline",
            # "size": int(max_pt_id)+1, #np.int64 doesn't serialize; cast to int
            "size": max_pt_id,
            "entries": pretrust,
        },
        "localTrust": {
            "scheme": "inline",
            # "size": int(max_lt_id)+1, #np.int64 doesn't serialize; cast to int
            "size": max_lt_id,
            "entries": localtrust,
        },
        "alpha": 0.5,
    }

    async with AsyncSession() as s:
        response = await s.post(
            "http://localhost:8080/basic/v1/compute",
            json=req,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=3000,
        )

        if response.status_code != 200:
            print(f"Server error: {response.status_code}:{response.reason}")
            raise Exception("Unknown error")
        trustscores = response.json()["entries"]
        print(
            f"{pretrust}:eigentrust took {time.perf_counter() - start_time} secs for {len(trustscores)} scores"
        )
        return trustscores


# In[63]:


async def get_neighbors_scores(
    fids, df, graph, max_degree, max_neighbors
):
    start_time = time.perf_counter()
    try:
        df = await _get_neighbors_edges(fids, df, graph, max_degree, max_neighbors)
        print(
            f"{fids}:dataframe took {time.perf_counter() - start_time} secs for {len(df)} edges"
        )
    except Exception as e:
        print(e)
        return []

    if df.shape[0] < 1:
        return []
    
    stacked = df.loc[:, ("i", "j")].stack()
    pseudo_id, orig_id = stacked.factorize()

    # pseudo_df is a new dataframe to avoid modifying existing shared global df
    pseudo_df = pd.Series(pseudo_id, index=stacked.index).unstack()
    pseudo_df.loc[:, ("v")] = df.loc[:, ("v")]

    if len(fids) > 1:
        # when more than 1 fid in input list, the neighbor edges may not have some input fids.
        pt_fids = orig_id.where(orig_id.isin(fids))
    else:
        pt_fids = fids
    pt_len = len(fids)
    # pretrust = [{'i': fid, 'v': 1/pt_len} for fid in pt_fids]
    pretrust = [
        {"i": orig_id.get_loc(fid), "v": 1 / pt_len}
        for fid in pt_fids
        if not np.isnan(fid)
    ]
    # max_pt_id = max(pt_fids)
    max_pt_id = len(orig_id)

    localtrust = pseudo_df.to_dict(orient="records")
    # max_lt_id = max(df['i'].max(), df['j'].max())
    max_lt_id = len(orig_id)

    print(
        f"{fids}:max_lt_id:{max_lt_id}, localtrust size:{len(localtrust)},"
        f" max_pt_id:{max_pt_id}, pretrust size:{len(pretrust)}"
    )

    i_scores = await go_eigentrust(
        pretrust=pretrust,
        max_pt_id=max_pt_id,
        localtrust=localtrust,
        max_lt_id=max_lt_id,
    )

    # rename i and v to fid and score respectively
    # also, filter out input fids
    fid_scores = [
        {"fid": int(orig_id[score["i"]]), "score": score["v"]}
        for score in i_scores
        if score["i"] not in fids
    ]
    print(
        f"{fids}:sample fid_scores:{random.sample(fid_scores, min(10, len(fid_scores)))}"
    )
    return fid_scores


# In[68]:


lt_df = pd.read_pickle("data/fc_v3engagement_fid_2024-06-18_filtered_df.pkl")


# In[69]:


lt_df.info()


# In[20]:


lt_df.head()


# In[70]:


get_ipython().run_cell_magic('time', '', "g = ig.Graph.Read_Pickle('data/fc_v3engagement_fid_2024-06-18_filtered_ig.pkl')")


# In[71]:


g.summary()


# In[22]:


rainbow_fids = pd.read_csv('/tmp/rainbow_fids_18sep2024.csv')


# In[23]:


rainbow_fids.head()


# In[24]:


rainbow_fids.info()


# In[56]:


async def main() -> None:
    tasks = []
    for fid in rainbow_fids['fid'].sample(10):
        print(fid)
        tasks.append(
            asyncio.create_task(
                get_neighbors_scores(
                    fids=[fid], df=lt_df, graph=g, max_degree=5, max_neighbors=1000)))
    responses = await asyncio.gather(*tasks)


# In[72]:


import timeit
start_time = timeit.default_timer()
asyncio.run(main()) # await main()
elapsed = timeit.default_timer() - start_time
print(f"Overall time taken: {elapsed} secs")


# In[ ]:




