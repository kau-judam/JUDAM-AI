import requests

tests = [
    {"title": "숙취 없는 건강 막걸리", "description": "치료 효과가 있습니다"},
    {"title": "미성년자용 딸기 막걸리", "description": "어린이도 마실 수 있어요"},
    {"title": "경기도 쌀 막걸리", "description": "경기도산 쌀로 만든 전통 막걸리"}
]

for t in tests:
    res = requests.post("http://127.0.0.1:8000/api/law/filter", json={
        "content_type": "recipe",
        "title": t["title"],
        "description": t["description"],
        "ingredients": ["쌀", "누룩"],
        "target_region": "서울"
    })
    print(f"{t['title']}: violation={res.json().get('violation')}")
