
import random
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client


# =====================================
# 기본 설정
# =====================================
st.set_page_config(
    page_title="급식 반찬 월드컵",
    page_icon="🍱",
    layout="wide",
)

st.title("🍱 급식 반찬 월드컵")
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

필요한열 = [
    "id",
    "game_id",
    "round",
    "left_menu",
    "right_menu",
    "winner",
]


# =====================================
# Supabase 연결
# =====================================
@st.cache_resource
def supabase_연결():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# =====================================
# 월드컵 기록 저장
# =====================================
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

    if not isinstance(rows, list) or len(rows) != 1:
        raise RuntimeError("저장 결과를 확인할 수 없습니다.")

    saved = rows[0]

    for key, expected_value in payload.items():
        if saved.get(key) != expected_value:
            raise RuntimeError("저장된 내용이 요청한 내용과 다릅니다.")

    if saved.get("id") is None:
        raise RuntimeError("저장 기록의 ID를 확인할 수 없습니다.")

    return saved


# =====================================
# 전체 대결 기록 조회
# =====================================
def 전체_기록_조회():
    client = supabase_연결()
    모든기록 = []
    시작번호 = 0
    한페이지크기 = 1000

    while True:
        response = (
            client.table("menu_duels")
            .select(
                "id, game_id, round, left_menu, right_menu, winner"
            )
            .order("id")
            .range(
                시작번호,
                시작번호 + 한페이지크기 - 1,
            )
            .execute()
        )

        페이지기록 = response.data or []
        모든기록.extend(페이지기록)

        if len(페이지기록) < 한페이지크기:
            break

        시작번호 += 한페이지크기

    return 모든기록


# =====================================
# 월드컵 초기화
# =====================================
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


# =====================================
# 반찬 선택 처리
# =====================================
def 반찬_선택(winner):
    if st.session_state.save_failed:
        return

    round_index = st.session_state.round_index
    match_index = st.session_state.match_index
    candidates = st.session_state.round_candidates

    left_menu = candidates[match_index * 2]
    right_menu = candidates[match_index * 2 + 1]
    round_name = 라운드이름[round_index]

    try:
        대결결과_저장(
            game_id=st.session_state.game_id,
            round_name=round_name,
            left_menu=left_menu,
            right_menu=right_menu,
            winner=winner,
        )
    except Exception as e:
        st.session_state.save_failed = True
        st.session_state.error_message = (
            f"{type(e).__name__}: {e}"
        )
        return

    # 저장 확인에 성공한 경우에만 다음으로 진행
    st.session_state.next_round_winners.append(winner)
    st.session_state.match_index += 1

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


# =====================================
# 두 화면 탭
# =====================================
월드컵탭, 분석탭 = st.tabs(
    ["🍱 반찬 월드컵", "📊 학급 전체 대결 분석"]
)


# =====================================
# 월드컵 화면
# =====================================
with 월드컵탭:
    if not st.session_state.game_started:
        st.info(
            "두 반찬 중 더 좋아하는 반찬을 선택하세요. "
            "각 선택 결과는 데이터베이스에 저장됩니다."
        )

        if st.button(
            "월드컵 시작하기",
            type="primary",
            use_container_width=True,
        ):
            새_판_초기화()
            st.rerun()

    elif st.session_state.save_failed:
        st.error("결과 저장을 확인하지 못해 선택을 중단했습니다.")

        st.write(
            "중복 기록을 막기 위해 자동 재저장이나 "
            "다음 대결 진행을 하지 않습니다."
        )
        st.write("오류 내용:", st.session_state.error_message)

        st.warning(
            "선생님께 Supabase의 menu_duels 테이블과 연결 설정, "
            "실제 저장 여부를 확인해 달라고 요청해 주세요."
        )

    elif st.session_state.champion is not None:
        st.balloons()
        st.success("🏆 최종 우승 반찬")
        st.header(f"🥇 {st.session_state.champion}")

        st.write("7번의 선택이 모두 완료되었습니다.")
        st.caption(f"게임 ID: {st.session_state.game_id}")

        if st.button(
            "새 월드컵 시작하기",
            type="primary",
            use_container_width=True,
        ):
            새_판_초기화()
            st.rerun()

    else:
        라운드번호 = st.session_state.round_index
        대결번호 = st.session_state.match_index
        후보 = st.session_state.round_candidates

        round_name = 라운드이름[라운드번호]
        전체대결수 = 라운드별_대결수[라운드번호]

        왼쪽반찬 = 후보[대결번호 * 2]
        오른쪽반찬 = 후보[대결번호 * 2 + 1]

        # 진행률 오류 수정: 항상 0~1 사이 값
        완료한대결수 = (
            라운드별_누적대결수[라운드번호]
            + 대결번호
        )
        진행률 = min(완료한대결수 / 7, 1.0)

        st.progress(
            진행률,
            text=(
                f"{round_name} · "
                f"대결 {대결번호 + 1}/{전체대결수} · "
                f"완료 {완료한대결수}/7"
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


# =====================================
# 학급 전체 대결 분석 화면
# =====================================
with 분석탭:
    st.header("📊 학급 전체 반찬 대결 분석")

    st.write(
        "menu_duels에 저장된 전체 대결 기록을 분석합니다. "
        "특정 학생이나 특정 게임만 따로 집계하지 않습니다."
    )

    st.info(
        "대결 기록 수와 참여 인원은 서로 다릅니다. "
        "한 판에서 7개의 대결 기록이 나올 수 있으며, "
        "진행 중인 판에서 저장된 대결도 집계에 포함됩니다."
    )

    if st.button(
        "🔄 결과 다시 불러오기",
        key="refresh_analysis",
        type="primary",
    ):
        st.session_state.pop("analysis_records", None)
        st.session_state.pop("analysis_error", None)

    # 처음 열었거나 다시 불러오기를 누른 경우 조회
    if "analysis_records" not in st.session_state:
        try:
            st.session_state.analysis_records = 전체_기록_조회()
            st.session_state.analysis_error = None
        except Exception as e:
            st.session_state.analysis_records = None
            st.session_state.analysis_error = (
                f"{type(e).__name__}: {e}"
            )

    기록 = st.session_state.analysis_records
    조회오류 = st.session_state.analysis_error

    if 조회오류 is not None:
        st.error(
            "대결 기록을 불러오지 못했습니다. "
            "기록이 없는 상태와는 다릅니다."
        )
        st.write("오류 내용:", 조회오류)
        st.write(
            "Supabase 연결 정보, 테이블 권한, "
            "menu_duels 테이블의 열 이름을 확인해 주세요."
        )

    elif 기록 is None:
        st.error("기록 조회 결과를 확인할 수 없습니다.")

    elif len(기록) == 0:
        st.warning(
            "아직 저장된 대결 기록이 없습니다. "
            "월드컵에서 대결을 진행한 뒤 다시 불러와 주세요."
        )

        st.metric("집계에 사용한 대결 기록 수", 0)
        st.metric("기록에 나타난 판 수", 0)

    else:
        df = pd.DataFrame(기록)

        # 필요한 열이 실제로 존재하는지 검사
        누락된열 = [
            col for col in 필요한열
            if col not in df.columns
        ]

        if 누락된열:
            st.error(
                "기록에 필요한 열이 없습니다: "
                + ", ".join(누락된열)
            )

        else:
            # 모든 후보를 표시하며, 대결이 없는 후보도 포함
            집계 = pd.DataFrame({"반찬": 반찬목록})
            집계["대결 수"] = 0
            집계["승리 수"] = 0
            집계["승률"] = float("nan")
            집계["우승 횟수"] = 0

            # left_menu와 right_menu 양쪽을 대결 수에 포함
            대결수 = pd.concat(
                [
                    df["left_menu"],
                    df["right_menu"],
                ],
                ignore_index=True,
            ).value_counts()

            승리수 = df["winner"].value_counts()

            결승기록 = df[
                df["round"].astype(str).str.strip() == "결승"
            ]
            우승수 = 결승기록["winner"].value_counts()

            집계["대결 수"] = (
                집계["반찬"].map(대결수).fillna(0).astype(int)
            )
            집계["승리 수"] = (
                집계["반찬"].map(승리수).fillna(0).astype(int)
            )
            집계["우승 횟수"] = (
                집계["반찬"].map(우승수).fillna(0).astype(int)
            )

            # 대결 기록이 있는 반찬만 승률을 계산
            기록있음 = 집계["대결 수"] > 0
            집계.loc[기록있음, "승률"] = (
                집계.loc[기록있음, "승리 수"]
                / 집계.loc[기록있음, "대결 수"]
                * 100
            )

            # 승률 높은 순서, 기록 없는 후보는 아래쪽
            정렬표 = 집계.sort_values(
                by=["승률", "승리 수", "우승 횟수", "반찬"],
                ascending=[False, False, False, True],
                na_position="last",
            ).reset_index(drop=True)

            판수 = df["game_id"].nunique(dropna=True)

            # 기록 수와 판 수를 별도로 표시
            지표1, 지표2 = st.columns(2)

            지표1.metric(
                "집계에 사용한 대결 기록 수",
                f"{len(df):,}건",
            )
            지표2.metric(
                "기록에 나타난 판 수",
                f"{판수:,}판",
            )

            st.caption(
                "판 수는 game_id의 고유 개수입니다. "
                "기록 수는 참여 인원 수가 아니며, "
                "진행 중인 판의 기록도 포함됩니다."
            )

            # 표에 표시할 승률 문자열
            표시표 = 정렬표.copy()
            표시표["승률"] = 표시표["승률"].map(
                lambda x: (
                    f"{x:.1f}%"
                    if pd.notna(x)
                    else "아직 알 수 없음"
                )
            )

            st.subheader("반찬별 기록 순위")

            st.dataframe(
                표시표[
                    [
                        "반찬",
                        "대결 수",
                        "승리 수",
                        "승률",
                        "우승 횟수",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "승률은 승리 수 ÷ 대결 수 × 100으로 계산합니다. "
                "대결 기록이 없는 반찬의 승률은 0%가 아니라 "
                "'아직 알 수 없음'으로 표시합니다."
            )

            st.subheader("반찬별 승률 비교")

            # 기록이 없는 후보도 축에 표시하되 막대는 그리지 않음
            그래프표 = 정렬표.copy()
            그래프표["승률"] = 그래프표["승률"].round(1)

            그래프 = px.bar(
                그래프표,
                x="승률",
                y="반찬",
                orientation="h",
                text="승률",
                category_orders={
                    "반찬": 그래프표["반찬"].tolist()
                },
                labels={
                    "승률": "승률 (%)",
                    "반찬": "반찬",
                },
                hover_data={
                    "대결 수": True,
                    "승리 수": True,
                    "우승 횟수": True,
                    "승률": ":.1f",
                },
                title="대결 기록이 있는 반찬의 승률",
            )

            그래프.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
                cliponaxis=False,
            )

            그래프.update_layout(
                xaxis_title="승률 (%)",
                yaxis_title="",
                xaxis=dict(
                    range=[
                        0,
                        max(
                            10,
                            float(
                                그래프표["승률"].max(skipna=True)
                                if 그래프표["승률"].notna().any()
                                else 0
                            ) * 1.2,
                        ),
                    ]
                ),
                yaxis={"categoryorder": "array",
                       "categoryarray": 그래프표["반찬"].tolist()},
                height=420,
                margin=dict(l=20, r=50, t=60, b=30),
            )

            st.plotly_chart(
                그래프,
                use_container_width=True,
            )

            st.caption(
                "승률을 계산할 기록이 없는 후보는 그래프에 이름만 표시되고 "
                "막대는 표시되지 않습니다. 막대가 없는 것은 승률 0%라는 "
                "뜻이 아닙니다."
            )
