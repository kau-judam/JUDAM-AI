"""
양조장 OCR 검증용 더미 서류 PNG 생성기 (서류 5종)
사용법: python scripts/gen_dummy_docs.py

대상 서류:
  1. 사업자등록증
  2. 신분증(주민등록증)
  3. 통신판매업 신고증
  4. 주류 통신판매 승인서
  5. 전통주 제조면허증

주의:
  - 모든 값은 명백한 가짜. 등록/면허번호도 가짜 형식.
  - "테스트용 견본 / NOT A REAL DOCUMENT" 워터마크를 크게 박아 위조 방지.
  - ground-truth 는 data/dummy_docs/labels.json 에 저장.

서식 근거(웹조사):
  - 통신판매업 신고증 = 전자상거래법 시행규칙 별지 제3호 (신고번호/상호/대표자/사업자등록번호/소재지/신고기관)
  - 전통주 제조면허/주류통신판매 = 관할 세무서장 발급 (면허번호/면허종류/제조장/승인주종 등)
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path("data/dummy_docs")
FONT_REG = "C:/Windows/Fonts/malgun.ttf"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"

# 공통 가짜 업체 정보
_BIZ = "주식회사 테스트양조"
_CEO = "김단아"
_BIZ_NO = "214-88-12345"
_ADDR = "강원특별자치도 평창군 봉평면 견본로 123"

# 서류 5종 정의: (파일명, 제목, 발급기관, [(라벨, 값)...], 정답라벨)
#   정답라벨의 일반 필드 키: document_type / brewery_name / registration_number /
#   owner_name / address / issue_date / issuing_authority
DOCS = [
    {
        "file": "01_사업자등록증.png",
        "title": "사업자등록증",
        "subtitle": "( 법인사업자 )",
        "rows": [
            ("등록번호", _BIZ_NO),
            ("법인명(상호)", _BIZ),
            ("대표자", _CEO),
            ("개업연월일", "2020-03-15"),
            ("사업장 소재지", _ADDR),
            ("업태 / 종목", "제조업 / 주류(탁주·약주)"),
        ],
        "authority": "평창세무서장",
        "issue_date": "2020-03-20",
        "label": {
            "document_type": "사업자등록증",
            "brewery_name": _BIZ,
            "registration_number": _BIZ_NO,
            "owner_name": _CEO,
            "address": _ADDR,
            "issue_date": "2020-03-20",
            "issuing_authority": "평창세무서장",
        },
    },
    {
        "file": "02_신분증.png",
        "title": "주민등록증",
        "subtitle": "(신분증 견본)",
        "rows": [
            ("성명", "이가상"),
            ("주민등록번호", "900101-2345678"),
            ("주소", "서울특별시 종로구 견본동 1-1"),
        ],
        "authority": "서울특별시 종로구청장",
        "issue_date": "2018-05-20",
        "label": {
            "document_type": "신분증",
            "brewery_name": "",                       # 신분증엔 상호 없음 → 채점 제외
            "registration_number": "900101-2345678",  # 주민등록번호
            "owner_name": "이가상",
            "address": "서울특별시 종로구 견본동 1-1",
            "issue_date": "2018-05-20",
            "issuing_authority": "서울특별시 종로구청장",
        },
    },
    {
        "file": "03_통신판매업신고증.png",
        "title": "통신판매업 신고증",
        "subtitle": "(전자상거래법 별지 제3호 서식)",
        "rows": [
            ("신고번호", "제 2023-강원평창-0042 호"),
            ("상호", _BIZ),
            ("대표자", _CEO),
            ("사업자등록번호", _BIZ_NO),
            ("사업장 소재지", _ADDR),
        ],
        "authority": "평창군수",
        "issue_date": "2023-07-01",
        "label": {
            "document_type": "통신판매업신고증",
            "brewery_name": _BIZ,
            "registration_number": "제 2023-강원평창-0042 호",
            "owner_name": _CEO,
            "address": _ADDR,
            "issue_date": "2023-07-01",
            "issuing_authority": "평창군수",
        },
    },
    {
        "file": "04_주류통신판매승인서.png",
        "title": "주류 통신판매 승인서",
        "subtitle": "(전통주 통신판매 승인)",
        "rows": [
            ("승인번호", "제 2024-전통주-0007 호"),
            ("업체명(상호)", _BIZ),
            ("대표자", _CEO),
            ("사업자등록번호", _BIZ_NO),
            ("승인 주종", "탁주, 약주"),
            ("제조장 소재지", _ADDR),
        ],
        "authority": "평창세무서장",
        "issue_date": "2024-02-10",
        "label": {
            "document_type": "주류통신판매승인서",
            "brewery_name": _BIZ,
            "registration_number": "제 2024-전통주-0007 호",
            "owner_name": _CEO,
            "address": _ADDR,
            "issue_date": "2024-02-10",
            "issuing_authority": "평창세무서장",
        },
    },
    {
        "file": "05_전통주제조면허증.png",
        "title": "주류 제조면허증",
        "subtitle": "( 전통주 )",
        "rows": [
            ("면허번호", "제 2019-주류-0033 호"),
            ("면허 종류", "전통주(탁주)"),
            ("제조장 상호", _BIZ),
            ("대표자", _CEO),
            ("제조장 소재지", _ADDR),
        ],
        "authority": "평창세무서장",
        "issue_date": "2019-11-05",
        "label": {
            "document_type": "전통주제조면허증",
            "brewery_name": _BIZ,
            "registration_number": "제 2019-주류-0033 호",
            "owner_name": _CEO,
            "address": _ADDR,
            "issue_date": "2019-11-05",
            "issuing_authority": "평창세무서장",
        },
    },
]

W, H = 900, 1180
WATERMARK = "테스트용 견본 · NOT A REAL DOCUMENT"

# ── Negative(비정상) 더미 ──
# 목적: is_valid_document=false 로 걸러져야 정상인 입력.
#   06 위조 의심   : 서류 형태이나 식별번호 판독불가 + 직인/발급기관 없음
#   07 무관(풍경)  : 서류 아님 (산·해·들판)
#   08 무관(음식)  : 서류 아님 (접시·부침개·잔)
#   09 서류아닌텍스트: 일상 메모(시/일기) — 인증 서류 아님
# 모두 "테스트용 견본" 워터마크 유지. ground-truth: expect_valid=False.
_NEG_LABEL_EMPTY = {
    "document_type": "인식불가", "brewery_name": "", "registration_number": "",
    "owner_name": "", "address": "", "issue_date": "", "issuing_authority": "",
}


def _font(path, size):
    return ImageFont.truetype(path, size)


def draw_watermark(img):
    """크게 대각선 반복 워터마크 (위조 방지)."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = _font(FONT_BOLD, 34)
    for yi in range(-2, 12):
        d.text((-150, yi * 130), WATERMARK + "   " + WATERMARK,
               font=f, fill=(220, 30, 30, 70))
    layer = layer.rotate(30, expand=False)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def render(doc):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    # 테두리
    d.rectangle([20, 20, W - 20, H - 20], outline=(60, 60, 60), width=3)

    title_f = _font(FONT_BOLD, 52)
    sub_f = _font(FONT_REG, 26)
    label_f = _font(FONT_BOLD, 30)
    val_f = _font(FONT_REG, 30)
    small_f = _font(FONT_REG, 24)

    # 제목
    tw = d.textlength(doc["title"], font=title_f)
    d.text(((W - tw) / 2, 70), doc["title"], font=title_f, fill="black")
    sw = d.textlength(doc["subtitle"], font=sub_f)
    d.text(((W - sw) / 2, 140), doc["subtitle"], font=sub_f, fill=(90, 90, 90))
    d.line([60, 190, W - 60, 190], fill=(120, 120, 120), width=2)

    # 항목들
    y = 250
    for label, val in doc["rows"]:
        d.text((80, y), f"{label}", font=label_f, fill=(20, 20, 20))
        d.text((360, y), f": {val}", font=val_f, fill=(20, 20, 20))
        y += 70

    # 발급일 / 발급기관
    y = max(y + 40, H - 260)
    d.text((W // 2 - 120, y), doc["issue_date"], font=small_f, fill="black")
    y += 60
    auth_f = _font(FONT_BOLD, 38)
    aw = d.textlength(doc["authority"], font=auth_f)
    d.text(((W - aw) / 2, y), doc["authority"], font=auth_f, fill="black")
    d.text(((W - aw) / 2 + aw + 10, y), " (직인)", font=small_f, fill=(150, 150, 150))

    return draw_watermark(img)


# ── Negative 렌더러 ──

def render_forgery():
    """위조 의심: 사업자등록증 형태이나 핵심 식별번호 판독불가·직인/발급기관 없음."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, W - 20, H - 20], outline=(60, 60, 60), width=3)
    title_f = _font(FONT_BOLD, 52)
    label_f = _font(FONT_BOLD, 30)
    val_f = _font(FONT_REG, 30)
    tw = d.textlength("사업자등록증", font=title_f)
    d.text(((W - tw) / 2, 80), "사업자등록증", font=title_f, fill="black")
    d.line([60, 180, W - 60, 180], fill=(120, 120, 120), width=2)
    rows = [
        ("등록번호", "(식별번호 훼손 · 판독 불가)"),
        ("법인명(상호)", "？？？"),
        ("대표자", "███"),
        ("개업연월일", "20██-██-██"),
        ("사업장 소재지", "(잉크 번짐으로 판독 불가)"),
    ]
    y = 260
    for lab, val in rows:
        d.text((80, y), lab, font=label_f, fill=(20, 20, 20))
        d.text((360, y), f": {val}", font=val_f, fill=(120, 20, 20))
        y += 70
    # 등록번호 자리에 검은 마스킹 바(훼손 흔적)
    d.rectangle([360, 258, 760, 296], fill=(20, 20, 20))
    # 직인/발급기관 없음 (의도적으로 비움)
    return draw_watermark(img)


def render_landscape():
    """무관한 이미지: 풍경(산·해·들판). 텍스트 없음."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, int(H * 0.55)], fill=(135, 206, 235))           # 하늘
    d.ellipse([W - 230, 80, W - 110, 200], fill=(255, 221, 80))           # 해
    d.polygon([(0, int(H * 0.55)), (int(W * 0.35), int(H * 0.27)),
               (int(W * 0.70), int(H * 0.55))], fill=(110, 140, 90))      # 산1
    d.polygon([(int(W * 0.40), int(H * 0.55)), (int(W * 0.75), int(H * 0.33)),
               (W, int(H * 0.55))], fill=(90, 120, 80))                   # 산2
    d.rectangle([0, int(H * 0.55), W, H], fill=(124, 179, 66))            # 들판
    return draw_watermark(img)


def render_food():
    """무관한 이미지: 음식(접시·부침개·잔). 텍스트 없음."""
    img = Image.new("RGB", (W, H), (250, 245, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(H * 0.62), W, H], fill=(160, 110, 70))            # 식탁
    d.ellipse([170, 300, 720, 760], fill=(245, 245, 245),
              outline=(205, 205, 205), width=6)                          # 접시
    d.ellipse([250, 380, 640, 690], fill=(214, 160, 80))                 # 부침개
    for cx, cy in [(360, 460), (520, 500), (440, 580), (560, 440)]:
        d.ellipse([cx, cy, cx + 42, cy + 42], fill=(180, 60, 40))        # 고명
    d.ellipse([720, 430, 860, 570], fill=(230, 230, 255),
              outline=(180, 180, 200), width=4)                          # 잔
    return draw_watermark(img)


def render_note():
    """서류 아닌 텍스트: 일상 메모/일기. 인증 서류 아님."""
    img = Image.new("RGB", (W, H), (255, 253, 245))
    d = ImageDraw.Draw(img)
    title_f = _font(FONT_BOLD, 46)
    body_f = _font(FONT_REG, 34)
    d.text((80, 70), "오늘의 메모", font=title_f, fill=(40, 40, 40))
    lines = [
        "내일 친구들이랑 막걸리 마시기로 함.",
        "장 볼 것: 김치, 두부, 파, 부침가루",
        "비 오는 날엔 역시 파전이지.",
        "다음에 가볼 양조장도 검색해보자.",
        "",
        "- 그냥 끄적이는 일기 -",
    ]
    y = 200
    for ln in lines:
        d.text((80, y), ln, font=body_f, fill=(55, 55, 55))
        y += 64
    return draw_watermark(img)


NEG_DOCS = [
    {"file": "06_위조의심_훼손사업자등록증.png", "render": render_forgery,
     "label": {**_NEG_LABEL_EMPTY, "expect_valid": False,
               "neg_kind": "위조의심", "note": "식별번호 훼손·직인 없음"}},
    {"file": "07_무관_풍경.png", "render": render_landscape,
     "label": {**_NEG_LABEL_EMPTY, "expect_valid": False,
               "neg_kind": "무관(풍경)", "note": "서류 아님"}},
    {"file": "08_무관_음식.png", "render": render_food,
     "label": {**_NEG_LABEL_EMPTY, "expect_valid": False,
               "neg_kind": "무관(음식)", "note": "서류 아님"}},
    {"file": "09_서류아닌_메모.png", "render": render_note,
     "label": {**_NEG_LABEL_EMPTY, "expect_valid": False,
               "neg_kind": "서류아닌텍스트", "note": "일상 메모/일기"}},
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    labels = {}
    # Positive(정상 서류 5종) — expect_valid=True
    for doc in DOCS:
        img = render(doc)
        path = OUT_DIR / doc["file"]
        img.save(path)
        label = {**doc["label"], "expect_valid": True}
        labels[doc["file"]] = label
        print(f"생성[정상]: {path}  ({label['document_type']})")

    # Negative(비정상 4종) — expect_valid=False, 걸러져야 정상
    for doc in NEG_DOCS:
        img = doc["render"]()
        path = OUT_DIR / doc["file"]
        img.save(path)
        labels[doc["file"]] = doc["label"]
        print(f"생성[비정상]: {path}  ({doc['label']['neg_kind']})")

    (OUT_DIR / "labels.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    pos = sum(1 for v in labels.values() if v.get("expect_valid", True))
    neg = len(labels) - pos
    print(f"\nground-truth 저장: {OUT_DIR / 'labels.json'}  "
          f"(정상 {pos}종 + 비정상 {neg}종 = {len(labels)})")


if __name__ == "__main__":
    main()
