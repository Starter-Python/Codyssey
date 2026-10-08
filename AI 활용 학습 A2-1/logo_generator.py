"""
AI 기반 브랜드 로고 시안 생성기 (담당 3 - Codyssey API 연동)
- 담당 1(브랜드명/키워드)과 담당 2(컬러 팔레트)의 정보를 입력받아
- Codyssey 이미지 생성 AI를 위한 고품질 로고 프롬프트를 구성하고
- gpt-image-1-mini 모델과 b64_json 방식으로 로고 시안을 생성하여 PNG로 저장한다.

사용법:
  1) .venv/bin/python "AI 활용 학습 A2-1/logo_generator.py"
"""

import os
import json
import base64
import urllib.request
import urllib.error

# ============================================================
# 🔑 Codyssey API 설정
# ============================================================
API_KEY = os.environ.get("OPENAI_API_KEY", "sk-cody-live-_tiH4Q8Nhc0c5ti9_KljWYyNL7WfzIANIqKYNA1iVSA")
API_URL = "https://copa.codyssey.kr/api/v1/images"
MODEL_NAME = "gpt-image-1-mini"


# ============================================================
# ① 프롬프트 생성 : 브랜드 및 컬러 정보를 영문 프롬프트로 변환
# ============================================================
def build_logo_prompts(brand_info, count=3):
    """
    브랜드 정보와 컬러 정보를 바탕으로 서로 다른 스타일의 로고 프롬프트 리스트를 생성한다.
    """
    name = brand_info.get("brand_name", "Brand")
    industry = brand_info.get("industry", "")
    target = brand_info.get("target", "")
    keywords = ", ".join(brand_info.get("keywords", []))
    tone = brand_info.get("tone", "")
    main_color = brand_info.get("main_color", "#2E7D32")
    sub_colors = brand_info.get("sub_colors", ["#A5D6A7"])
    sub_colors_str = ", ".join(sub_colors)

    # 3가지 서로 다른 디자인 스타일 템플릿
    styles = [
        # 스타일 1: 미니멀 심볼 & 아이콘형 (Minimalist Modern Vector)
        f"A clean, modern, minimalist vector logo for a brand named '{name}' in the {industry} industry. "
        f"Target audience: {target}. Concept keywords: {keywords}. Tone: {tone}. "
        f"Primary brand color: {main_color}, secondary accent colors: {sub_colors_str}. "
        f"Focus on a sleek geometric symbol or iconic mark. Flat design, crisp vector graphics, "
        f"pure solid white background, high aesthetic quality, no complex gradients.",

        # 스타일 2: 자연/유기적 라인아트형 (Organic Nature Line-Art)
        f"An elegant, organic line-art logo symbol inspired by nature for '{name}', a {industry} brand. "
        f"Embodying {keywords} with a {tone} aesthetic. "
        f"Main color theme: {main_color} with subtle accents of {sub_colors_str}. "
        f"Sophisticated botanical or organic motif, minimalist line work, harmonious curves, "
        f"clean white background, centered composition, premium boutique feel.",

        # 스타일 3: 모던 엠블럼/모노그램형 (Modern Abstract Emblem)
        f"A contemporary abstract logo mark and emblem for '{name}', representing {industry}. "
        f"Reflecting a {tone} mood with themes of {keywords}. "
        f"Color palette: dominant {main_color}, paired with harmonious accents of {sub_colors_str}. "
        f"Distinctive signature emblem, balanced negative space, modern flat vector art, "
        f"solid white background, studio lighting feel, versatile corporate branding."
    ]

    return styles[:count]


# ============================================================
# ② 이미지 생성 API 호출 (Codyssey API: gpt-image-1-mini + b64_json)
# ============================================================
def call_image_api(prompt, api_key=API_KEY):
    """Codyssey 이미지 생성 API를 직접 호출하여 base64 문자열을 반환한다."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "size": "1024x1024",
        "response_format": "b64_json"
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            # Codyssey 응답 구조: res_json['result']['images'][0]['b64_json']
            result_obj = res_json.get("result", {})
            images = result_obj.get("images", [])
            if not images:
                raise RuntimeError(f"API 응답에 이미지 데이터가 없습니다: {res_json}")
            return images[0]["b64_json"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP 에러 ({e.code}): {error_body}")
    except Exception as e:
        raise RuntimeError(f"API 호출 실패: {e}")


# ============================================================
# ③ Base64 디코딩 및 PNG 파일 저장
# ============================================================
def save_b64_image(b64_data, save_path):
    """base64 이미지 데이터를 디코딩하여 PNG 파일로 저장한다."""
    try:
        image_bytes = base64.b64decode(b64_data)
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        print(f"  -> 로고 이미지 저장 완료: {save_path}")
        return True
    except Exception as e:
        raise RuntimeError(f"이미지 파일 저장 실패: {e}")


# ============================================================
# 메인 로고 생성 함수 (담당 4 통합 시 호출할 함수)
# ============================================================
def generate_logos(brand_info, output_dir="./output", api_key=None, count=3):
    """
    브랜드 정보를 입력받아 로고 시안 count개를 생성하고,
    생성된 파일 경로 리스트를 반환한다.
    
    :param brand_info: 브랜드 정보 딕셔너리
    :param output_dir: 결과 이미지를 저장할 디렉토리 경로 (기본값: ./output)
    :param api_key: Codyssey/OpenAI API 키 (None일 경우 환경변수 OPENAI_API_KEY 사용)
    :param count: 생성할 로고 시안 개수 (기본값: 3)
    :return: 저장된 파일 경로 리스트 (예: ["./output/logo_01.png", ...])
    """
    # 1. API 키 확인
    key = api_key or os.environ.get("OPENAI_API_KEY") or API_KEY
    if not key or key == "여기에_본인_API_키_입력":
        raise ValueError("API 키가 설정되지 않았습니다. api_key 인자 또는 OPENAI_API_KEY 환경변수를 설정해주세요.")

    # 2. 출력 디렉토리 확인 및 생성
    os.makedirs(output_dir, exist_ok=True)

    # 3. 프롬프트 리스트 생성
    prompts = build_logo_prompts(brand_info, count=count)
    saved_paths = []

    print(f"\n🎨 로고 시안 {count}개 생성을 시작합니다 (엔드포인트: {API_URL})...")

    for i, prompt in enumerate(prompts, start=1):
        filename = f"logo_{i:02d}.png"
        filepath = os.path.join(output_dir, filename)
        print(f"[{i}/{count}] 로고 시안 {i} 생성 중 ({MODEL_NAME} 호출)...")

        try:
            b64_data = call_image_api(prompt, key)
            save_b64_image(b64_data, filepath)
            saved_paths.append(filepath)
        except Exception as e:
            print(f"  ⚠️ 로고 시안 {i} 생성 중 오류 발생: {e}")

    return saved_paths


# ============================================================
# 단독 테스트 실행
# ============================================================
if __name__ == "__main__":
    # 담당 1(브랜드 문구)과 담당 2(컬러 팔레트)에게서 전달받는다고 가정한 테스트 데이터
    sample_brand_info = {
        "brand_name": "Blooming",
        "industry": "친환경 화장품",
        "target": "20~30대 여성",
        "keywords": ["자연", "순수", "건강"],
        "tone": "따뜻하고 신뢰감 있는",
        # 2번 담당자가 생성한 실제 컬러 HEX 코드 반영
        "main_color": "#2E7D32",
        "sub_colors": ["#A5D6A7", "#FFF3E0", "#5D4037"]
    }

    # 결과 저장 폴더 설정
    output_directory = "./output"

    print("==================================================")
    print("AI 브랜드 로고 시안 생성기 (담당 3 단독 테스트)")
    print("==================================================")
    print("입력 브랜드 정보:")
    print(json.dumps(sample_brand_info, indent=2, ensure_ascii=False))

    # 로고 생성 실행
    try:
        results = generate_logos(sample_brand_info, output_dir=output_directory, count=3)
        print("\n✅ 모든 로고 시안 생성 완료!")
        print("반환된 파일 목록:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {e}")
