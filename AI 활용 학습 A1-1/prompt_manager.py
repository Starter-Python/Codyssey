"""A1-1 과제: VSCode 통합 터미널에서 사용하는 콘솔 프롬프트 관리자.

기본은 실행 중 메모리에 데이터를 유지하고, 종료 후 다시 실행하면
기본 예시 데이터로 초기화된다. 보너스로 JSON 저장·불러오기와
Markdown 내보내기, 수정·삭제, 조회수 기록·Top 보기를 제공한다.
입력이 필요한 프로그램이므로 VSCode의 Output 창이나 Debug Console이
아니라 통합 터미널에서 실행해야 한다.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import TypedDict


class Prompt(TypedDict):
    """프롬프트 한 건의 데이터 구조."""

    title: str
    content: str
    category: str
    favorite: bool
    view_count: int


PROMPTS_JSON_FILE = "prompts.json"
PROMPTS_MARKDOWN_FILE = "prompts_by_category.md"


class UserInputCancelled(Exception):
    """입력 스트림이 닫히거나 사용자가 Ctrl+C로 입력을 중단했을 때 사용한다."""


CATEGORIES = (
    "텍스트 생성",
    "이미지 생성",
    "영상 생성",
    "페르소나",
    "자동화",
    "기타",
)

DEFAULT_PROMPTS: list[Prompt] = [
    {
        "title": "블로그 초안 작성",
        "content": "당신은 친절한 콘텐츠 마케터입니다. 주제를 바탕으로 독자가 이해하기 쉬운 블로그 초안을 작성하세요.",
        "category": "텍스트 생성",
        "favorite": True,
        "view_count": 0,
    },
    {
        "title": "따뜻한 책방 포스터",
        "content": "비 오는 오후의 독립 서점을 홍보하는 따뜻한 분위기의 포스터를 제작하세요. 수채화 질감과 부드러운 조명을 사용합니다.",
        "category": "이미지 생성",
        "favorite": False,
        "view_count": 0,
    },
    {
        "title": "학습 코치 페르소나",
        "content": "당신은 초보 학습자의 목표를 작은 단계로 나누고 격려하는 학습 코치입니다. 쉬운 한국어로 답변하세요.",
        "category": "페르소나",
        "favorite": False,
        "view_count": 0,
    },
    {
        "title": "SNS 홍보 문구 3종",
        "content": "신제품의 핵심 장점을 바탕으로 인스타그램용 짧은 홍보 문구 3개를 서로 다른 말투로 작성하세요.",
        "category": "텍스트 생성",
        "favorite": False,
        "view_count": 0,
    },
    {
        "title": "친환경 제품 상세 이미지",
        "content": "재활용 소재로 만든 텀블러를 밝은 자연광 아래에서 보여 주는 제품 상세 이미지를 제작하세요. 깨끗한 배경과 신선한 초록색 포인트를 사용합니다.",
        "category": "이미지 생성",
        "favorite": False,
        "view_count": 0,
    },
    {
        "title": "15초 릴스 스토리보드",
        "content": "신입 직장인의 아침 루틴을 주제로 15초 세로형 릴스의 장면 구성, 자막, 전환 효과를 시간 순서대로 제안하세요.",
        "category": "영상 생성",
        "favorite": True,
        "view_count": 0,
    },
    {
        "title": "제품 소개 영상 내레이션",
        "content": "무선 이어폰의 노이즈 캔슬링과 배터리 장점을 자연스럽게 소개하는 30초 분량의 한국어 내레이션을 작성하세요.",
        "category": "영상 생성",
        "favorite": False,
        "view_count": 0,
    },
    {
        "title": "고객 상담 도우미 페르소나",
        "content": "당신은 고객의 불편을 먼저 공감하고, 쉬운 표현으로 해결 방법을 단계별로 안내하는 온라인 쇼핑몰 상담 도우미입니다.",
        "category": "페르소나",
        "favorite": False,
        "view_count": 0,
    },
    {
        "title": "일일 업무 보고 자동화",
        "content": "아래 업무 메모를 완료·진행 중·이슈·내일 할 일 네 항목으로 정리한 일일 업무 보고서 형식으로 변환하세요.",
        "category": "자동화",
        "favorite": False,
        "view_count": 0,
    },
    {
        "title": "주간 회고 질문",
        "content": "한 주를 돌아볼 수 있도록 잘한 점, 아쉬운 점, 배운 점, 다음 주 목표에 관한 질문 4개를 작성하세요.",
        "category": "기타",
        "favorite": False,
        "view_count": 0,
    },
]

MENU_OPTIONS = {
    "1": "프롬프트 추가",
    "2": "전체 프롬프트 목록 보기",
    "3": "카테고리별 조회",
    "4": "프롬프트 검색",
    "5": "프롬프트 상세 보기",
    "6": "즐겨찾기 추가/해제",
    "7": "즐겨찾기 목록 보기",
    "8": "프롬프트 삭제",
    "9": "프롬프트 수정",
    "10": "조회수 Top 보기",
    "11": "JSON 저장",
    "12": "JSON 불러오기",
    "13": "Markdown 내보내기",
    "14": "종료",
}


def create_initial_prompts() -> list[Prompt]:
    """기본 프롬프트를 깊은 복사해 실행별 독립 목록을 생성한다."""

    return deepcopy(DEFAULT_PROMPTS)


def is_interactive_terminal() -> bool:
    """현재 실행 환경이 사용자 입력을 안정적으로 받을 수 있는 터미널인지 확인한다."""

    return sys.stdin.isatty() and sys.stdout.isatty()


def show_terminal_execution_help() -> None:
    """VSCode Output·Debug Console에서 실행했을 때 통합 터미널 실행 방법을 안내한다."""

    print("\n[ 실행 환경 안내 ]")
    print("이 프로그램은 사용자 입력이 필요한 콘솔 프로그램입니다.")
    print("VSCode의 Output 창, Debug Console, 'Run Code' 실행이 아니라 통합 터미널을 사용하세요.")
    print("1. VSCode 메뉴에서 Terminal > New Terminal을 선택합니다.")
    print('2. cd "AI 활용 학습 A1-1"을 입력합니다.')
    print("3. Windows는 python prompt_manager.py, macOS·Linux는 python3 prompt_manager.py를 입력합니다.")


def read_user_input(prompt: str) -> str:
    """입력을 받고, EOF 또는 Ctrl+C 중단을 호출자에게 일관되게 알린다."""

    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt) as error:
        raise UserInputCancelled from error


def get_non_empty_input(label: str) -> str:
    """공백이 아닌 값이 입력될 때까지 사용자의 입력을 받는다."""

    while True:
        value = read_user_input(f"{label}: ").strip()
        if value:
            return value
        print(f"{label}은(는) 비워둘 수 없습니다. 다시 입력하세요.")


def is_valid_prompt_number(value: str, prompts: list[Prompt]) -> bool:
    """입력값이 현재 목록 범위의 프롬프트 번호인지 판별한다."""

    return value.isdigit() and 1 <= int(value) <= len(prompts)


def get_prompt_index(prompts: list[Prompt]) -> int | None:
    """유효한 프롬프트 번호를 0부터 시작하는 목록 위치로 변환한다."""

    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return None

    while True:
        value = read_user_input("프롬프트 번호를 입력하세요: ").strip()
        if is_valid_prompt_number(value, prompts):
            return int(value) - 1
        print("잘못된 프롬프트 번호입니다. 목록의 번호를 입력하세요.")


def choose_category() -> str:
    """기본 카테고리를 선택하거나 새 카테고리를 직접 입력하도록 한다."""

    print("카테고리를 선택하세요.")
    for number, category in enumerate(CATEGORIES, start=1):
        print(f"{number}. {category}")
    print("0. 직접 입력")

    while True:
        choice = read_user_input("카테고리 번호를 입력하세요: ").strip()
        if choice == "0":
            return get_non_empty_input("직접 입력할 카테고리")
        if choice.isdigit() and 1 <= int(choice) <= len(CATEGORIES):
            return CATEGORIES[int(choice) - 1]
        print("잘못된 카테고리 번호입니다. 다시 입력하세요.")


def normalize_prompt_text(value: str) -> str:
    """대소문자와 연속 공백 차이를 무시할 수 있도록 텍스트를 정규화한다."""

    return " ".join(value.casefold().split())


def find_duplicate_prompt(prompts: list[Prompt], title: str, content: str) -> Prompt | None:
    """제목과 내용이 모두 같은 기존 프롬프트를 찾아 반환한다."""

    normalized_title = normalize_prompt_text(title)
    normalized_content = normalize_prompt_text(content)
    return next(
        (
            prompt
            for prompt in prompts
            if normalize_prompt_text(prompt["title"]) == normalized_title
            and normalize_prompt_text(prompt["content"]) == normalized_content
        ),
        None,
    )


def add_prompt(prompts: list[Prompt]) -> None:
    """새 프롬프트를 추가하되 제목과 내용이 같은 항목은 중복 등록하지 않는다."""

    print("\n[ 새 프롬프트 추가 ]")
    title = get_non_empty_input("제목")
    content = get_non_empty_input("내용")
    duplicate = find_duplicate_prompt(prompts, title, content)
    if duplicate is not None:
        print(f"동일한 프롬프트가 이미 존재합니다: '{duplicate['title']}'")
        print("내용을 다르게 작성한 뒤 다시 등록하세요.")
        return

    category = choose_category()
    prompts.append(
        {
            "title": title,
            "content": content,
            "category": category,
            "favorite": False,
            "view_count": 0,
        }
    )
    print(f"'{title}' 프롬프트가 추가되었습니다.")


def format_prompt_summary(number: int, prompt: Prompt) -> str:
    """목록에 출력할 프롬프트 한 줄을 만든다."""

    favorite_mark = "⭐" if prompt["favorite"] else "-"
    view_count = prompt.get("view_count", 0)
    return (
        f"{number}. {prompt['title']} | 카테고리: {prompt['category']} | "
        f"즐겨찾기: {favorite_mark} | 조회: {view_count}"
    )


def show_prompt_list(prompts: list[Prompt], heading: str = "전체 프롬프트 목록") -> None:
    """프롬프트 목록을 번호, 제목, 카테고리, 즐겨찾기 표시와 함께 출력한다."""

    print(f"\n[ {heading} ]")
    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return

    for number, prompt in enumerate(prompts, start=1):
        print(format_prompt_summary(number, prompt))


def get_view_categories(prompts: list[Prompt]) -> list[str]:
    """기본 카테고리와 직접 추가된 카테고리를 중복 없이 반환한다."""

    custom_categories = sorted(
        {prompt["category"] for prompt in prompts if prompt["category"] not in CATEGORIES}
    )
    return [*CATEGORIES, *custom_categories]


def select_category_to_view(prompts: list[Prompt]) -> str:
    """조회할 카테고리를 선택받는다."""

    categories = get_view_categories(prompts)
    print("조회할 카테고리를 선택하세요.")
    for number, category in enumerate(categories, start=1):
        print(f"{number}. {category}")

    while True:
        choice = read_user_input("카테고리 번호를 입력하세요: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(categories):
            return categories[int(choice) - 1]
        print("잘못된 카테고리 번호입니다. 다시 입력하세요.")


def filter_prompts_by_category(prompts: list[Prompt], category: str) -> list[Prompt]:
    """지정한 카테고리에 속한 프롬프트만 반환한다."""

    return [prompt for prompt in prompts if prompt["category"] == category]


def show_prompts_by_category(prompts: list[Prompt]) -> None:
    """선택한 카테고리에 속한 프롬프트만 출력한다."""

    category = select_category_to_view(prompts)
    show_prompt_list(filter_prompts_by_category(prompts, category), f"{category} 프롬프트")


def find_prompts(prompts: list[Prompt], keyword: str) -> list[Prompt]:
    """제목 또는 내용에 키워드가 포함된 프롬프트를 반환한다."""

    normalized_keyword = keyword.casefold()
    return [
        prompt
        for prompt in prompts
        if normalized_keyword in prompt["title"].casefold()
        or normalized_keyword in prompt["content"].casefold()
    ]


def search_prompts(prompts: list[Prompt]) -> None:
    """키워드를 입력받아 제목 또는 내용에서 일치하는 프롬프트를 출력한다."""

    keyword = get_non_empty_input("검색 키워드")
    show_prompt_list(find_prompts(prompts, keyword), f"'{keyword}' 검색 결과")


def show_prompt_detail(prompts: list[Prompt]) -> None:
    """선택한 프롬프트의 모든 핵심 정보를 출력하고 조회수를 기록한다."""

    print("\n[ 프롬프트 상세 보기 ]")
    index = get_prompt_index(prompts)
    if index is None:
        return

    prompt = prompts[index]
    prompt["view_count"] = prompt.get("view_count", 0) + 1
    favorite_status = "⭐ 즐겨찾기" if prompt["favorite"] else "- 즐겨찾기 아님"
    print(f"제목: {prompt['title']}")
    print(f"카테고리: {prompt['category']}")
    print(f"즐겨찾기: {favorite_status}")
    print(f"조회수: {prompt['view_count']}")
    print("내용:")
    print(prompt["content"])


def toggle_favorite(prompts: list[Prompt]) -> None:
    """선택한 프롬프트의 즐겨찾기 상태를 추가 또는 해제한다."""

    print("\n[ 즐겨찾기 추가/해제 ]")
    index = get_prompt_index(prompts)
    if index is None:
        return

    prompt = prompts[index]
    prompt["favorite"] = not prompt["favorite"]
    action = "추가" if prompt["favorite"] else "해제"
    print(f"'{prompt['title']}' 프롬프트를 즐겨찾기에서 {action}했습니다.")


def get_favorite_prompts(prompts: list[Prompt]) -> list[Prompt]:
    """즐겨찾기된 프롬프트만 반환한다."""

    return [prompt for prompt in prompts if prompt["favorite"]]


def show_favorites(prompts: list[Prompt]) -> None:
    """즐겨찾기된 프롬프트만 모아 출력한다."""

    show_prompt_list(get_favorite_prompts(prompts), "즐겨찾기 프롬프트")


def delete_prompt(prompts: list[Prompt]) -> None:
    """선택한 프롬프트를 확인 후 목록에서 삭제한다."""

    print("\n[ 프롬프트 삭제 ]")
    index = get_prompt_index(prompts)
    if index is None:
        return

    prompt = prompts[index]
    print(f"제목: {prompt['title']}")
    print(f"카테고리: {prompt['category']}")
    confirm = read_user_input("정말 삭제할까요? (y/N): ").strip().lower()
    if confirm != "y":
        print("삭제를 취소했습니다.")
        return

    removed = prompts.pop(index)
    print(f"'{removed['title']}' 프롬프트를 삭제했습니다.")


def edit_prompt(prompts: list[Prompt]) -> None:
    """선택한 프롬프트의 제목·내용·카테고리를 수정한다."""

    print("\n[ 프롬프트 수정 ]")
    index = get_prompt_index(prompts)
    if index is None:
        return

    prompt = prompts[index]
    print(f"현재 제목: {prompt['title']}")
    new_title = read_user_input("새 제목(Enter면 유지): ").strip()
    print(f"현재 내용: {prompt['content']}")
    new_content = read_user_input("새 내용(Enter면 유지): ").strip()

    final_title = new_title if new_title else prompt["title"]
    final_content = new_content if new_content else prompt["content"]
    duplicate = find_duplicate_prompt(prompts, final_title, final_content)
    if duplicate is not None and duplicate is not prompt:
        print(f"동일한 프롬프트가 이미 존재합니다: '{duplicate['title']}'")
        print("수정을 취소했습니다.")
        return

    print(f"현재 카테고리: {prompt['category']}")
    change = read_user_input("카테고리를 변경할까요? (y/N): ").strip().lower()
    final_category = choose_category() if change == "y" else prompt["category"]

    prompt["title"] = final_title
    prompt["content"] = final_content
    prompt["category"] = final_category
    print(f"'{prompt['title']}' 프롬프트를 수정했습니다.")


def get_top_prompts(prompts: list[Prompt], limit: int = 5) -> list[Prompt]:
    """조회수가 높은 순서로 프롬프트를 반환한다."""

    return sorted(prompts, key=lambda item: item.get("view_count", 0), reverse=True)[:limit]


def show_top_prompts(prompts: list[Prompt], limit: int = 5) -> None:
    """조회수 기준 상위 프롬프트를 출력한다."""

    top = get_top_prompts(prompts, limit)
    show_prompt_list(top, f"조회수 Top {len(top)}")


def normalize_loaded_prompt(item: dict) -> Prompt:
    """JSON에서 읽은 항목에 빠진 필드를 기본값으로 채운다."""

    return {
        "title": str(item.get("title", "")),
        "content": str(item.get("content", "")),
        "category": str(item.get("category", "기타")),
        "favorite": bool(item.get("favorite", False)),
        "view_count": int(item.get("view_count", 0) or 0),
    }


def save_prompts(prompts: list[Prompt], path: str = PROMPTS_JSON_FILE) -> None:
    """프롬프트 목록을 JSON 파일로 저장한다."""

    with open(path, "w", encoding="utf-8") as file:
        json.dump(prompts, file, ensure_ascii=False, indent=2)
    print(f"{len(prompts)}개를 '{path}'에 저장했습니다.")


def load_prompts(path: str = PROMPTS_JSON_FILE) -> list[Prompt]:
    """JSON 파일에서 프롬프트 목록을 불러온다."""

    with open(path, encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("프롬프트 파일 형식이 올바르지 않습니다.")
    return [normalize_loaded_prompt(item) for item in data if isinstance(item, dict)]


def load_prompts_into(prompts: list[Prompt], path: str = PROMPTS_JSON_FILE) -> None:
    """JSON 파일 내용을 현재 목록에 덮어쓴다."""

    try:
        loaded = load_prompts(path)
    except FileNotFoundError:
        print(f"'{path}' 파일이 없습니다. 기본 데이터로 계속합니다.")
        return
    except (ValueError, OSError) as error:
        print(f"불러오기에 실패했습니다: {error}")
        return
    prompts[:] = loaded
    print(f"{len(loaded)}개를 '{path}'에서 불러왔습니다.")


def export_prompts_markdown(
    prompts: list[Prompt], path: str = PROMPTS_MARKDOWN_FILE
) -> None:
    """카테고리별로 묶어 Markdown 파일로 내보낸다."""

    categories = get_view_categories(prompts)
    lines = ["# 프롬프트 모음", ""]
    for category in categories:
        items = filter_prompts_by_category(prompts, category)
        if not items:
            continue
        lines.append(f"## {category} ({len(items)}개)")
        lines.append("")
        for prompt in items:
            star = "⭐" if prompt["favorite"] else "-"
            views = prompt.get("view_count", 0)
            lines.append(f"### {prompt['title']}")
            lines.append("")
            lines.append(f"- 카테고리: {category}")
            lines.append(f"- 즐겨찾기: {star}")
            lines.append(f"- 조회수: {views}")
            lines.append("")
            lines.append(str(prompt["content"]))
            lines.append("")
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
    print(f"{len(prompts)}개를 '{path}'에 내보냈습니다.")


def show_menu() -> None:
    """현재 제공하는 콘솔 메뉴를 출력한다."""

    print("\n" + "=" * 42)
    print("       Python 콘솔 프롬프트 관리자")
    print("=" * 42)
    for number, label in MENU_OPTIONS.items():
        print(f"{number}. {label}")


def get_menu_choice() -> str:
    """유효한 메뉴 번호가 입력될 때까지 재입력받는다."""

    while True:
        choice = read_user_input("메뉴 번호를 입력하세요: ").strip()
        if choice in MENU_OPTIONS:
            return choice
        print("잘못된 메뉴 번호입니다. 표시된 번호를 입력하세요.")


def run_menu_loop(prompts: list[Prompt]) -> None:
    """메뉴를 반복 출력하고 선택한 기능을 실행한다."""

    while True:
        show_menu()
        choice = get_menu_choice()

        if choice == "1":
            add_prompt(prompts)
        elif choice == "2":
            show_prompt_list(prompts)
        elif choice == "3":
            show_prompts_by_category(prompts)
        elif choice == "4":
            search_prompts(prompts)
        elif choice == "5":
            show_prompt_detail(prompts)
        elif choice == "6":
            toggle_favorite(prompts)
        elif choice == "7":
            show_favorites(prompts)
        elif choice == "8":
            delete_prompt(prompts)
        elif choice == "9":
            edit_prompt(prompts)
        elif choice == "10":
            show_top_prompts(prompts)
        elif choice == "11":
            save_prompts(prompts)
        elif choice == "12":
            load_prompts_into(prompts)
        elif choice == "13":
            export_prompts_markdown(prompts)
        elif choice == "14":
            print("프롬프트 관리자를 종료합니다. 안녕히 가세요.")
            return


def main() -> None:
    """실행 환경을 확인한 뒤 메뉴 기반 프로그램을 시작한다."""

    if not is_interactive_terminal():
        show_terminal_execution_help()
        return

    print("프롬프트 관리자에 오신 것을 환영합니다.")
    try:
        run_menu_loop(create_initial_prompts())
    except UserInputCancelled:
        print("\n입력이 중단되어 프로그램을 종료합니다. 안녕히 가세요.")


if __name__ == "__main__":
    main()
