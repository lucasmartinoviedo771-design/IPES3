def split_reqs(s: str):
    return [x.strip() for x in s.split(",") if x.strip()]
