"""2024~2025년 원/달러 환율 트렌드 분석

데이터 출처 : Yahoo Finance — USD/KRW (티커 KRW=X, yfinance 패키지)
분석 기간   : 2024-01-02 ~ 2025-12-30
실행 방법   : python analysis.py   (images/ 폴더에 그래프가 생성됩니다)
"""
import os
import sys
from datetime import date, timedelta
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- 설정 ----------------------------------------------------------
TICKER, START_DATE, END_DATE = "KRW=X", "2024-01-01", "2025-12-31"
DATA_PATH   = "data/usdkrw-exchange-rate-analysis.csv"
IMG_DIR     = "images"
TOPIC_TITLE = "2024~2025년 원/달러 환율 트렌드 분석"
VALUE_LABEL = "원/달러 환율 (원)"

ALIGN_TO_KR_TRADING_DAYS = True
MISSING_POLICY = "ffill"
OUTLIER_METHOD = "domain"
OUTLIER_POLICY = "keep"
IQR_K, Z_THRESHOLD = 1.5, 3.0
HAMPEL_WIN, HAMPEL_K, DOMAIN_LIMIT = 21, 3.0, 10.0
MA_SHORT, MA_LONG, VOL_WINDOW = 7, 30, 30
# --------------------------------------------------------------------

def setup_korean_font():
    """한글 폰트를 등록한다."""
    import matplotlib.font_manager as fm
    candidates = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/AppleGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "C:/Windows/Fonts/malgun.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            fm.fontManager.addfont(p)
            prop = fm.FontProperties(fname=p)
            plt.rcParams["font.family"] = prop.get_name()
            plt.rcParams["axes.unicode_minus"] = False
            return
    plt.rcParams["axes.unicode_minus"] = False


def load_data():
    """저장된 CSV가 있으면 먼저 읽고, 없으면 yfinance에서 다운로드한다."""
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH, index_col="date", parse_dates=True)
        print(f"[로드] {DATA_PATH} 에서 {len(df)}행 로드")
        return df

    print(f"[다운로드] yfinance 에서 {TICKER} ({START_DATE} ~ {END_DATE}) 다운로드 중...")
    import yfinance as yf
    raw = yf.download(TICKER, start=START_DATE, end=END_DATE,
                      progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = pd.DataFrame({"value": raw["Close"].astype(float)})
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df = df.sort_index()

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, encoding="utf-8-sig")
    print(f"[저장] {DATA_PATH} 에 스냅샷 저장 완료 ({len(df)}행)")
    return df


def align_to_kr_trading_days(df):
    """주말과 한국 공휴일을 제거해 서울 외환시장 거래일 축에 맞춘다."""
    if not ALIGN_TO_KR_TRADING_DAYS:
        return df

    try:
        import holidays as pyholidays
        years = range(df.index.min().year, df.index.max().year + 1)
        hs = set(pyholidays.KR(years=list(years)).keys())
        for y in years:
            hs.add(date(y, 5, 1))
            hs.add(date(y, 12, 31))
    except Exception:
        hs = set()

    is_weekend = df.index.dayofweek >= 5
    idx_dates = pd.Series(df.index.date, index=df.index)
    is_holiday = idx_dates.isin(hs)

    drop = is_weekend | is_holiday.values
    cleaned = df[~drop].copy()

    biz = pd.bdate_range(cleaned.index.min(), cleaned.index.max())
    expected = pd.DatetimeIndex([d for d in biz if d.date() not in hs],
                                name=cleaned.index.name)
    missing = expected.difference(cleaned.index)
    if len(missing):
        cleaned = cleaned.reindex(expected)

    return cleaned


def clean(df):
    """결측치와 이상치를 정제한다."""
    d = df.sort_index().copy()
    d = d[~d.index.duplicated(keep="first")]

    if d["value"].isna().any():
        if MISSING_POLICY == "ffill":
            d["value"] = d["value"].ffill().bfill()
        elif MISSING_POLICY == "interpolate":
            d["value"] = d["value"].interpolate(method="linear").ffill().bfill()
        else:
            d = d.dropna(subset=["value"])

    d["is_outlier"] = d["value"].pct_change().abs().fillna(0) > DOMAIN_LIMIT / 100
    return d


def add_features(df):
    """이동평균, 일간 변동률, 롤링 변동성을 파생변수로 추가한다."""
    d = df.copy()
    d["ma_short"]   = d["value"].rolling(MA_SHORT).mean()
    d["ma_long"]    = d["value"].rolling(MA_LONG).mean()
    d["ret"]        = d["value"].pct_change() * 100
    d["volatility"] = d["ret"].rolling(VOL_WINDOW).std()
    d["cum_ret"]    = (d["value"] / d["value"].iloc[0] - 1) * 100
    return d


def plot_all(d):
    """리포트에 들어갈 시각화 6개를 생성해 images/ 에 저장한다."""
    setup_korean_font()
    os.makedirs(IMG_DIR, exist_ok=True)
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

    # 01 전체 추세 + 이동평균
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(d.index, d["value"], color="#4A90E2", lw=1.2, label=VALUE_LABEL)
    ax.plot(d.index, d["ma_short"], color="#F5A623", lw=1.6, label=f"{MA_SHORT}일 이동평균")
    ax.plot(d.index, d["ma_long"], color="#D0021B", lw=1.8, label=f"{MA_LONG}일 이동평균")
    ax.set_title(f"{TOPIC_TITLE} — 전체 추세와 이동평균선", fontsize=14, pad=12)
    ax.set_xlabel("날짜"); ax.set_ylabel(VALUE_LABEL)
    ax.legend(loc="upper left"); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(f"{IMG_DIR}/01_trend_moving_average.png", dpi=130)
    plt.close(fig)

    # 02 일간 변동률 + 롤링 변동성
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    cols = np.where(d["ret"] >= 0, "#E74C3C", "#3498DB")
    ax1.bar(d.index, d["ret"], color=cols, width=1.5, alpha=0.85)
    ax1.set_ylabel("일간 변동률 (%)")
    ax1.set_title("일간 변동률 및 30일 롤링 변동성 추이", fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax2.plot(d.index, d["volatility"], color="#8E44AD", lw=1.5,
             label=f"{VOL_WINDOW}일 롤링 표준편차")
    ax2.set_xlabel("날짜"); ax2.set_ylabel("변동성 (%)")
    ax2.legend(loc="upper left"); ax2.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(f"{IMG_DIR}/02_return_volatility.png", dpi=130)
    plt.close(fig)

    # 03 월별 변동률
    try:
        monthly = d["value"].resample("ME").last()
    except ValueError:
        monthly = d["value"].resample("M").last()
    m_ret = (monthly.pct_change() * 100).dropna()
    m_avg = m_ret.groupby(m_ret.index.month).mean()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    cols = np.where(m_avg >= 0, "#E74C3C", "#3498DB")
    ax.bar([f"{m}월" for m in m_avg.index], m_avg.values, color=cols, alpha=0.85)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("월별 평균 변동률 패턴 (2024~2025년)", fontsize=14, pad=12)
    ax.set_xlabel("월"); ax.set_ylabel("평균 변동률 (%)")
    for i, v in enumerate(m_avg.values):
        ax.text(i, v + (0.05 if v >= 0 else -0.15), f"{v:+.2f}%", ha="center", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(f"{IMG_DIR}/03_monthly_return.png", dpi=130)
    plt.close(fig)

    # 04 누적 변동률 + 요일별
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.plot(d.index, d["cum_ret"], color="#27AE60", lw=1.5)
    ax1.axhline(0, color="black", lw=0.8, ls="--")
    ax1.set_title("시작일 대비 누적 수익률 추이", fontsize=13)
    ax1.set_xlabel("날짜"); ax1.set_ylabel("누적 변화율 (%)"); ax1.grid(True, alpha=0.3)
    w_avg = d.groupby(d.index.dayofweek)["ret"].mean()
    cols = np.where(w_avg[:5] >= 0, "#E74C3C", "#3498DB")
    ax2.bar([weekday_names[i] for i in range(5)], w_avg[:5], color=cols, alpha=0.85)
    ax2.axhline(0, color="black", lw=0.8)
    ax2.set_title("요일별 평균 일간 변동률 (월~금)", fontsize=13)
    ax2.set_xlabel("요일"); ax2.set_ylabel("평균 일간 변동률 (%)"); ax2.grid(True, alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(f"{IMG_DIR}/04_cumulative_weekday.png", dpi=130)
    plt.close(fig)

    # 05 히스토그램 + 박스플롯
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    r = d["ret"].dropna()
    axes[0].hist(r, bins=30, color="#2E86DE", alpha=0.8, edgecolor="white")
    axes[0].axvline(0, color="black", lw=0.9)
    axes[0].axvline(r.mean(), color="#E74C3C", ls="--", lw=1.4,
                    label=f"평균 {r.mean():.3f}%")
    axes[0].set_title("일간 변동률 분포 (히스토그램)", fontsize=13)
    axes[0].set_xlabel("일간 변동률 (%)"); axes[0].set_ylabel("일수"); axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    years = sorted(d.index.year.unique())
    groups = [d.loc[d.index.year == y, "ret"].dropna().values for y in years]
    bp = axes[1].boxplot(groups, labels=[f"{y}년" for y in years],
                         patch_artist=True, whis=1.5)
    for box in bp["boxes"]: box.set(facecolor="#AED6F1", alpha=0.8)
    for med in bp["medians"]: med.set(color="#1B4F72", linewidth=2)
    axes[1].axhline(0, color="black", lw=0.9)
    axes[1].set_title("연도별 일간 변동률 (박스플롯, 수염 1.5xIQR)", fontsize=13)
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(f"{IMG_DIR}/05_distribution.png", dpi=130)
    plt.close(fig)

    # 06 월 x 요일 히트맵
    pv = (d.assign(월=d.index.month, 요일=d.index.dayofweek)
            .pivot_table(index="월", columns="요일", values="ret", aggfunc="mean"))
    pv = pv[[c for c in pv.columns if c <= 4]]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    lim = np.nanmax(np.abs(pv.values))
    im = ax.imshow(pv.values, cmap="RdBu_r", aspect="auto", vmin=-lim, vmax=lim)
    ax.set_xticks(range(len(pv.columns)))
    ax.set_xticklabels([weekday_names[c] for c in pv.columns])
    ax.set_yticks(range(len(pv.index)))
    ax.set_yticklabels([f"{m}월" for m in pv.index])
    for a_ in range(pv.shape[0]):
        for b_ in range(pv.shape[1]):
            val = pv.values[a_, b_]
            if not np.isnan(val):
                ax.text(b_, a_, f"{val:+.2f}", ha="center", va="center", fontsize=9,
                        color="white" if abs(val) > lim * 0.6 else "black")
    ax.set_title("월 × 요일 평균 일간 변동률 (%)", fontsize=13, pad=12)
    fig.colorbar(im, ax=ax, label="평균 변동률 (%)")
    fig.tight_layout(); fig.savefig(f"{IMG_DIR}/06_heatmap.png", dpi=130)
    plt.close(fig)

    print("[시각화] images/ 에 그래프 6개 저장 완료")


def summarize(d):
    """리포트 인사이트의 근거가 된 핵심 수치를 출력한다."""
    print("-" * 52)
    print(f"기간        : {d.index.min().date()} ~ {d.index.max().date()} ({len(d)}개)")
    print(f"전체 변화율   : {(d['value'].iloc[-1] / d['value'].iloc[0] - 1) * 100:+.2f}%")
    print(f"최고 / 최저   : {d['value'].max():,.2f} / {d['value'].min():,.2f}")
    print(f"일간 변동성   : {d['ret'].std():.2f}%")
    print(f"평균 / 중앙값 : {d['value'].mean():,.2f} / {d['value'].median():,.2f}")
    q1, q3 = d["value"].quantile(0.25), d["value"].quantile(0.75)
    print(f"Q1 / Q3 / IQR : {q1:,.2f} / {q3:,.2f} / {q3 - q1:,.2f}")
    print("-" * 52)


if __name__ == "__main__":
    data = add_features(clean(align_to_kr_trading_days(load_data())))
    plot_all(data)
    summarize(data)
