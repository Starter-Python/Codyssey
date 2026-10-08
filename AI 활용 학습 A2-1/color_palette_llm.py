"""
LLM 기반 브랜드 컬러 팔레트 생성기 (담당 2 - Codyssey API 연동)
- 담당 1에게서 받은 JSON(6개 항목)을 입력받아
- LLM으로 컬러(HEX)를 추천받고
- matplotlib으로 팔레트를 시각화하여 PNG로 저장한다

사용법:
  1) .venv/bin/pip install openai matplotlib
  2) 아래 API_KEY에 본인 키 입력 (또는 환경변수 OPENAI_API_KEY 설정)
  3) .venv/bin/python "AI 활용 학습 A2-1/color_palette_llm.py"
"""

import os
import re
import json
import matplotlib.pyplot as plt

# ============================================================
# 🔑 Codyssey API 키 및 Base URL 설정
# ============================================================
API_KEY = os.environ.get("OPENAI_API_KEY", "sk-cody-live-_tiH4Q8Nhc0c5ti9_KljWYyNL7WfzIANIqKYNA1iVSA")
BASE_URL = "https://copa.codyssey.kr/v1"


# ============================================================
# ① LLM 호출 : 브랜드 정보(6개 항목) -> 컬러 추천(JSON)
# ============================================================
def call_llm_for_colors(brief):
    """LLM에게 브랜드 정보를 주고 컬러 팔레트를 JSON으로 받는다."""
    from openai import OpenAI

    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL
    )

    prompt = f"""
너는 브랜드 컬러 전문가야. 아래 브랜드 정보에 어울리는 컬러 팔레트를 추천해줘.

브랜드 정보:
- 업종: {brief.get('industry')}
- 타겟: {brief.get('target')}
- 키워드: {', '.join(brief.get('keywords', []))}
- 톤앤매너: {brief.get('tone')}
- 경쟁사: {', '.join(brief.get('competitors', []))}
- 추가 요청사항: {brief.get('notes') or '없음'}

조건:
- 경쟁사와는 차별화되는 컬러를 제안할 것
- 메인 컬러 1개, 서브 컬러 3개
- 반드시 HEX 코드(#RRGGBB) 형식
- 아래 JSON 형식으로만 답변:
{{"main": "#RRGGBB", "sub": ["#RRGGBB", "#RRGGBB", "#RRGGBB"]}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content


# ============================================================
# ② 검증 : HEX 형식 + 개수 확인
# ============================================================
def parse_and_validate(raw_text):
    """LLM 응답(JSON 문자열)을 파싱하고 HEX 형식/개수를 검증한다."""
    data = json.loads(raw_text)
    hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")

    main = data["main"]
    sub = data["sub"]

    if not hex_pattern.match(main):
        raise ValueError(f"메인 컬러 형식 오류: {main}")

    if not (2 <= len(sub) <= 3):
        raise ValueError(f"서브 컬러 개수 오류: {len(sub)}개")

    for c in sub:
        if not hex_pattern.match(c):
            raise ValueError(f"서브 컬러 형식 오류: {c}")

    return {"main": main, "sub": sub}


# ============================================================
# ③ 시각화 : matplotlib으로 팔레트 그리기 + PNG 저장
# ============================================================
def hex_to_rgb(hex_code):
    """'#2E7D32' -> (46, 125, 50) 로 변환"""
    hex_code = hex_code.lstrip("#")
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))


def draw_palette(palette, filename="color_palette.png"):
    """컬러 팔레트를 이미지로 그려서 저장한다."""
    colors = [palette["main"]] + palette["sub"]
    labels = ["MAIN"] + [f"SUB {i+1}" for i in range(len(palette["sub"]))]

    fig, ax = plt.subplots(figsize=(len(colors) * 2, 3))

    for i, (color, label) in enumerate(zip(colors, labels)):
        ax.add_patch(plt.Rectangle((i, 0), 1, 1, color=color))

        r, g, b = hex_to_rgb(color)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = "black" if brightness > 140 else "white"

        ax.text(i + 0.5, 0.6, label, ha="center", va="center",
                color=text_color, fontsize=12, fontweight="bold")
        ax.text(i + 0.5, 0.4, color.upper(), ha="center", va="center",
                color=text_color, fontsize=10)

    ax.set_xlim(0, len(colors))
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Brand Color Palette", fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"이미지 저장 완료 -> {filename}")


# ============================================================
# 메인 실행 흐름
# ============================================================
def generate_palette(brief, filename="color_palette.png"):
    raw = call_llm_for_colors(brief)
    palette = parse_and_validate(raw)
    draw_palette(palette, filename=filename)
    return palette


if __name__ == "__main__":
    brief = {
        "industry": "친환경 화장품",
        "target": "20~30대 여성",
        "keywords": ["자연", "순수", "건강"],
        "tone": "따뜻하고 신뢰감 있는",
        "competitors": ["이니스프리", "아로마티카"],
        "notes": "",
    }

    result = generate_palette(brief)

    print("생성된 컬러 팔레트:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
