
import random
import uuid

import streamlit as st
from supabase import create_client


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="급식 반찬 월드컵",
    page_icon="🍱",
    layout="centered",
)

st.title("🍱 급식 반찬 월드컵")
st.write("8개의 반찬 중 가장 좋아하는 반찬을 선택해 주세요!")
st.caption("8강 → 4강 → 결승 · 총 7번 선택")


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
라운드별_대결수 = [4, 2, 1]
라운드별_누적대결수 = [0, 4, 6]


# -----------------------------
# Supabase 연결 및 저장
# -----------------------------
@st.cache_resource
def supabase_연결():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def 대결결과_저장(
    game_id,
    round_name,
    left_menu,
    right_menu,
    winner,
):
    client = supabase_연결()

    payload = {
        "game_id": game_id,
        "round": round_name,
        "left_menu": left_menu,
        "right_menu": right_menu,
        "winner": winner,
    }

    response = (
        client.table("menu_duels")
        .insert(payload)
        .select(
            "id, game_id, round, left_menu, right_menu, winner"
        )
        .execute()
    )

    rows = response.data

    # 저장된 결과가 정확히 한 건이고,
    # 저장된 내용이 요청한 내용과 일치하는지 확인
    if not isinstance(rows, list) or len(rows) != 1:
        raise RuntimeError("저장 결과를 확인할 수 없습니다.")

    saved = rows[0]

    for key, expected_value in payload.items():
        if saved.get(key) != expected_value:
            raise RuntimeError("저장된 결과가 요청한 내용과 다릅니다.")

    if saved.get("id") is None:
        raise RuntimeError("저장된 기록의 ID를 확인할 수 없습니다.")

    return saved


# -----------------------------
# 게임 초기화
# -----------------------------
def 새_판_초기화():
    후보 = 반찬목록.copy()
    random.shuffle(후보)

    st.session_state.game_id = str(uuid.uuid4())
    st.session_state.round_index = 0
    st.session_state.match_index = 0
    st.session_state.round_candidates = 후보
    st.session_state.next_round_winners = []
    st.session_state.champion = None
    st.session_state.save_failed = False
    st.session_state.error_message = ""
    st.session_state.game_started = True


if "game_started" not in st.session_state:
    st.session_state.game_started = False

if "save_failed" not in st.session_state:
    st.session_state.save_failed = False


# -----------------------------
# 반찬 선택 처리
# -----------------------------
def 반찬_선택(winner):
    if st.session_state.save_failed:
        return

    round_index = st.session_state.round_index
    match_index = st.session_state.match_index
    candidates = st.session_state.round_candidates

    left_menu = candidates[match_index * 2]
    right_menu = candidates[match_index * 2 + 1]
    round_name = 라운드이름[round_index]

    # 데이터베이스 저장 및 확인이 먼저 진행됨
    try:
        대결결과_저장(
            game_id=st.session_state.game_id,
            round_name=round_name,
            left_menu=left_menu,
            right_menu=right_menu,
            winner=winner,
        )
    except Exception as e:
        # 저장 성공 여부가 불확실하면 다음 선택을 막음
        st.session_state.save_failed = True
        st.session_state.error_message = (
            f"{type(e).__name__}: {e}"
        )
        return

    # 저장 확인에 성공한 경우에만 게임 진행
    st.session_state.next_round_winners.append(winner)
    st.session_state.match_index += 1

    # 현재 라운드의 모든 대결이 끝났는지 확인
    if (
        st.session_state.match_index
        >= 라운드별_대결수[round_index]
    ):
        winners = st.session_state.next_round_winners.copy()

        if round_index == 2:
            st.session_state.champion = winners[0]
        else:
            st.session_state.round_index += 1
            st.session_state.match_index = 0
            st.session_state.round_candidates = winners
            st.session_state.next_round_winners = []


# -----------------------------
# 게임 시작 화면
# -----------------------------
if not st.session_state.game_started:
    st.info(
        "반찬 두 가지 중 더 좋아하는 반찬을 고르면 "
        "다음 대결로 넘어갑니다."
    )

    if st.button(
        "월드컵 시작하기",
        type="primary",
        use_container_width=True,
    ):
        새_판_초기화()
        st.rerun()

    st.stop()


# -----------------------------
# 저장 오류 화면
# -----------------------------
if st.session_state.save_failed:
    st.error("결과 저장을 확인하지 못해 선택을 중단했습니다.")

    st.write(
        "중복 기록을 방지하기 위해 자동으로 다시 저장하거나 "
        "다음 대결로 진행하지 않습니다."
    )

    st.write(
        "오류 내용:",
        st.session_state.error_message,
    )

    st.warning(
        "선생님께 Supabase의 menu_duels 테이블과 "
        "연결 설정을 확인해 달라고 요청해 주세요. "
        "기록이 실제로 저장되었는지도 확인해야 합니다."
    )

    st.stop()


# -----------------------------
# 우승 결과 화면
# -----------------------------
if st.session_state.champion is not None:
    st.balloons()

    st.success("🏆 최종 우승 반찬")

    st.header(f"🥇 {st.session_state.champion}")

    st.write("7번의 선택이 모두 완료되었습니다.")

    st.caption(
        f"게임 ID: {st.session_state.game_id}"
    )

    if st.button(
        "새 월드컵 시작하기",
        type="primary",
        use_container_width=True,
    ):
        새_판_초기화()
        st.rerun()

    st.stop()


# -----------------------------
# 현재 대결 표시
# -----------------------------
라운드번호 = st.session_state.round_index
대결번호 = st.session_state.match_index
후보 = st.session_state.round_candidates

round_name = 라운드이름[라운드번호]
전체대결수 = 라운드별_대결수[라운드번호]

왼쪽반찬 = 후보[대결번호 * 2]
오른쪽반찬 = 후보[대결번호 * 2 + 1]


# -----------------------------
# 진행률 계산 - 수정된 부분
# -----------------------------
완료한대결수 = (
    라운드별_누적대결수[라운드번호]
    + 대결번호
)

진행률 = min(완료한대결수 / 7, 1.0)

st.progress(
    진행률,
    text=(
        f"{round_name} · "
        f"대결 {대결번호 + 1}/{전체대결수} "
        f"· 완료 {완료한대결수}/7"
    ),
)

st.subheader(f"현재 {round_name}")
st.write("둘 중 더 먹고 싶은 반찬을 선택하세요!")

왼쪽칸, 오른쪽칸 = st.columns(2)

with 왼쪽칸:
    st.markdown("### 🍽️")

    if st.button(
        왼쪽반찬,
        key=f"left_{라운드번호}_{대결번호}",
        use_container_width=True,
        type="primary",
    ):
        반찬_선택(왼쪽반찬)
        st.rerun()

with 오른쪽칸:
    st.markdown("### 🍽️")

    if st.button(
        오른쪽반찬,
        key=f"right_{라운드번호}_{대결번호}",
        use_container_width=True,
        type="primary",
    ):
        반찬_선택(오른쪽반찬)
        st.rerun()
