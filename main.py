
# main.py
# 🍱 급식 반찬 월드컵 — 8강 토너먼트

import random
import uuid

import streamlit as st
from supabase import create_client


st.set_page_config(
    page_title="급식 반찬 월드컵",
    page_icon="🍱",
    layout="centered",
)

# --------------------------------------------------
# 후보 반찬
# --------------------------------------------------

반찬목록 = [
    "제육볶음",
    "간장찜닭",
    "가자미순살튀김",
    "돈육불백",
    "미트볼데리야끼볶음",
    "수육",
    "진미채고추장볶음",
    "치즈떡닭갈비",
]

라운드이름 = ["8강", "4강", "결승"]


# --------------------------------------------------
# Supabase 연결
# --------------------------------------------------

@st.cache_resource
def supabase_연결():
    """Secrets에 설정된 Supabase 접속 정보를 사용합니다."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def 대결결과_저장(game_id, round_name, left_menu, right_menu, winner):
    """
    기존 menu_duels 테이블에 한 행을 저장합니다.

    저장 성공을 확인할 수 있도록 삽입한 행을 반환받습니다.
    id와 created_at은 데이터베이스 기본값을 사용합니다.
    """
    client = supabase_연결()

    저장자료 = {
        "game_id": game_id,
        "round": round_name,
        "left_menu": left_menu,
        "right_menu": right_menu,
        "winner": winner,
    }

    response = (
        client.table("menu_duels")
        .insert(저장자료)
        .select("id, game_id, round, left_menu, right_menu, winner")
        .execute()
    )

    # 삽입 결과 행을 확인할 수 없으면 성공으로 처리하지 않습니다.
    if not response.data or len(response.data) != 1:
        raise RuntimeError("저장된 대결 결과를 확인할 수 없습니다.")

    저장행 = response.data[0]

    # 반환된 행이 이번에 요청한 결과와 일치하는지 확인합니다.
    for 열 in ["game_id", "round", "left_menu", "right_menu", "winner"]:
        if 저장행.get(열) != 저장자료[열]:
            raise RuntimeError("저장 결과가 요청한 대결 결과와 일치하지 않습니다.")

    return 저장행


# --------------------------------------------------
# 세션 초기화
# --------------------------------------------------

def 새_판_초기화():
    후보 = 반찬목록.copy()
    random.shuffle(후보)

    st.session_state["game_id"] = str(uuid.uuid4())
    st.session_state["후보"] = 후보
    st.session_state["라운드번호"] = 0
    st.session_state["대결번호"] = 0
    st.session_state["다음라운드진출자"] = []
    st.session_state["우승반찬"] = None
    st.session_state["저장오류잠금"] = False
    st.session_state["저장오류메시지"] = ""
    st.session_state["게임시작"] = True


if "게임시작" not in st.session_state:
    st.session_state["게임시작"] = False


# --------------------------------------------------
# 선택 처리
# --------------------------------------------------

def 반찬_선택(winner):
    """저장 성공이 확인된 경우에만 대결을 진행합니다."""

    if st.session_state["저장오류잠금"]:
        return

    라운드번호 = st.session_state["라운드번호"]
    대결번호 = st.session_state["대결번호"]
    후보 = st.session_state["후보"]

    left_menu = 후보[대결번호 * 2]
    right_menu = 후보[대결번호 * 2 + 1]
    round_name = 라운드이름[라운드번호]

    # 서로 다른 두 후보 중 하나만 선택할 수 있습니다.
    if winner not in (left_menu, right_menu):
        return

    try:
        # 반드시 저장 및 반환 결과 확인이 성공해야 다음 단계로 이동합니다.
        대결결과_저장(
            game_id=st.session_state["game_id"],
            round_name=round_name,
            left_menu=left_menu,
            right_menu=right_menu,
            winner=winner,
        )

    except Exception as 오류:
        # 저장 여부가 불확실하면 재선택과 재저장을 잠급니다.
        st.session_state["저장오류잠금"] = True
        st.session_state["저장오류메시지"] = (
            "대결 결과를 저장했는지 확인할 수 없습니다. "
            "중복 저장을 막기 위해 이 판의 선택을 잠갔습니다. "
            "교사가 Supabase의 menu_duels 테이블을 확인해야 합니다. "
            f"(오류 종류: {type(오류).__name__})"
        )
        return

    # 저장 성공 확인 후에만 승자를 반영합니다.
    st.session_state["다음라운드진출자"].append(winner)
    st.session_state["대결번호"] += 1

    # 해당 라운드의 모든 대결이 끝났는지 확인합니다.
    현재라운드대결수 = len(st.session_state["후보"]) // 2

    if st.session_state["대결번호"] >= 현재라운드대결수:
        진출자 = st.session_state["다음라운드진출자"]

        if len(진출자) == 1:
            # 결승까지 끝났습니다.
            st.session_state["우승반찬"] = 진출자[0]
        else:
            # 다음 라운드로 진출합니다.
            st.session_state["후보"] = 진출자
            st.session_state["다음라운드진출자"] = []
            st.session_state["라운드번호"] += 1
            st.session_state["대결번호"] = 0


# --------------------------------------------------
# 화면
# --------------------------------------------------

st.title("🍱 급식 반찬 월드컵")
st.write("8개의 반찬 중 오늘의 최애 반찬을 골라 보세요!")
st.caption("8강 4번 + 4강 2번 + 결승 1번 = 총 7번 선택")

if not st.session_state["게임시작"]:

    st.markdown("""
    ### 🏆 오늘의 급식 월드컵

    - 후보 8개가 무작위 순서로 대결합니다.
    - 두 반찬 중 하나를 선택합니다.
    - 승리한 반찬만 다음 라운드에 진출합니다.
    - 각 대결 결과는 교사가 준비한 Supabase 테이블에 저장됩니다.
    """)

    if st.button("🎮 월드컵 시작하기", type="primary", use_container_width=True):
        새_판_초기화()
        st.rerun()

elif st.session_state["저장오류잠금"]:

    st.error("⚠️ 대결 결과 확인이 필요합니다.")

    st.write(st.session_state["저장오류메시지"])

    st.info(
        "중복 저장 방지를 위해 이 화면에서는 추가 선택을 할 수 없습니다. "
        "교사가 데이터베이스의 해당 game_id 기록을 확인해야 합니다. "
        "페이지를 새로고침하거나 앱을 재시작하면 상태가 초기화될 수 있으므로 "
        "확인 전에는 다시 시작하지 마세요."
    )

elif st.session_state["우승반찬"] is not None:

    st.balloons()

    st.subheader("🏆 오늘의 최종 우승 반찬")

    st.title(st.session_state["우승반찬"])

    st.success("7번의 선택을 모두 완료했습니다!")

    st.caption(
        "대결 기록 game_id: "
        + st.session_state["game_id"]
    )

    if st.button("🔄 다시 시작하기", type="primary", use_container_width=True):
        새_판_초기화()
        st.rerun()

else:

    라운드번호 = st.session_state["라운드번호"]
    대결번호 = st.session_state["대결번호"]
    후보 = st.session_state["후보"]

    left_menu = 후보[대결번호 * 2]
    right_menu = 후보[대결번호 * 2 + 1]

    round_name = 라운드이름[라운드번호]
    전체대결수 = len(후보) // 2

    st.progress(
        (라운드번호 * 4 + 대결번호 + 1) / 7,
        text=f"{round_name} · 대결 {대결번호 + 1}/{전체대결수}",
    )

    st.subheader(f"🔥 {round_name}")
    st.write("둘 중 더 먹고 싶은 반찬 하나를 선택하세요!")

    왼쪽칸, 오른쪽칸 = st.columns(2)

    with 왼쪽칸:
        st.markdown(
            f"""
            <div style="
                border: 2px solid #e0e0e0;
                border-radius: 16px;
                padding: 24px 8px;
                text-align: center;
                min-height: 120px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 22px;
                font-weight: bold;
            ">{left_menu}</div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            left_menu,
            key=f"왼쪽_{라운드번호}_{대결번호}",
            use_container_width=True,
            type="primary",
        ):
            반찬_선택(left_menu)
            st.rerun()

    with 오른쪽칸:
        st.markdown(
            f"""
            <div style="
                border: 2px solid #e0e0e0;
                border-radius: 16px;
                padding: 24px 8px;
                text-align: center;
                min-height: 120px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 22px;
                font-weight: bold;
            ">{right_menu}</div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            right_menu,
            key=f"오른쪽_{라운드번호}_{대결번호}",
            use_container_width=True,
            type="primary",
        ):
            반찬_선택(right_menu)
            st.rerun()

    st.caption(
        f"현재 판의 ID: {st.session_state['game_id']}"
    )
