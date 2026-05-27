import os
os.environ["TAVILY_API_KEY"] = "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"
try:
    from langchain_tavily import TavilySearch
    tool = TavilySearch(max_results=3, include_raw_content=True)
except:
    from langchain_community.tools.tavily_search import TavilySearchResults
    tool = TavilySearchResults(max_results=3, include_raw_content=True)

res = tool.invoke({"query": "who is the current chief minister of tamil nadu "})
print("TYPE:", type(res))
if isinstance(res, list):
    for r in res:
        print("LIST ITEM:", type(r), r)
elif isinstance(res, dict):
    print("DICT KEYS:", res.keys())
    for k, v in res.items():
        print(k, ":", type(v), str(v)[:100])
else:
    print("RES:", res)
