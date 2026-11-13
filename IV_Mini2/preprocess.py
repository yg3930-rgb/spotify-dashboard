"""
preprocess.py
将 Kaggle "Top Spotify Songs in 73 Countries (Daily Updated)" 原始数据
检查并筛选为仪表板使用的轻量 CSV。

用法:
    python preprocess.py --input universal_top_spotify_songs.csv
可选参数:
    --countries US DE BR MX JP KR   要保留的国家代码（建议 <= 7 个，便于颜色图例）
    --days 90                       保留最近多少天的数据
    --output spotify_filtered.csv
"""
import argparse
import pandas as pd

# 仪表板需要的字段（原始文件中不存在的字段会被自动跳过）
KEEP_COLS = [
    "spotify_id", "name", "artists", "daily_rank", "country", "snapshot_date",
    "popularity", "is_explicit", "duration_ms", "album_release_date",
    "danceability", "energy", "valence", "tempo", "key", "mode",
]
AUDIO_COLS = ["danceability", "energy", "valence", "tempo"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--countries", nargs="+", default=["US", "DE", "BR", "MX", "JP", "KR"])
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--output", default="spotify_filtered.csv")
    return p.parse_args()


def main():
    args = parse_args()
    kept, country_counts = [], pd.Series(dtype="int64")

    # 分块读取，避免大文件占满内存
    for chunk in pd.read_csv(args.input, usecols=lambda c: c in KEEP_COLS, chunksize=200_000):
        country_counts = country_counts.add(chunk["country"].fillna("GLOBAL").value_counts(), fill_value=0)
        kept.append(chunk[chunk["country"].isin(args.countries)])

    df = pd.concat(kept, ignore_index=True)
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])

    # ---- 1. 数据概况 ----
    print("== 原始数据中各国家的行数（前 15）==")
    print(country_counts.sort_values(ascending=False).head(15).astype(int))
    missing = set(args.countries) - set(country_counts.index)
    if missing:
        print(f"\n[警告] 以下国家代码不存在: {missing}")

    print(f"\n== 所选国家的日期范围: {df['snapshot_date'].min().date()} ~ {df['snapshot_date'].max().date()}")

    # ---- 2. 检查音频特征缺失情况（按月）----
    present = [c for c in AUDIO_COLS if c in df.columns]
    print("\n== 音频特征缺失比例（按月）==")
    print(df.groupby(df["snapshot_date"].dt.to_period("M"))[present]
            .apply(lambda g: g.isna().mean()).round(3).tail(12))

    # ---- 3. 筛选最近 N 天并去掉缺失音频特征的行 ----
    cutoff = df["snapshot_date"].max() - pd.Timedelta(days=args.days)
    out = df[df["snapshot_date"] > cutoff].dropna(subset=present)

    # 去重：同一国家、同一天、同一排名只保留一条（原始数据中有少量重复）
    before = len(out)
    out = out.drop_duplicates(subset=["country", "snapshot_date", "daily_rank"])
    print(f"\n== 去除重复行: {before - len(out)} 行")

    # 覆盖率检查：某国天数明显少于其他国家时给出警告（例如 GB 在 2025-04 之后基本缺失）
    days_per_country = out.groupby("country")["snapshot_date"].nunique()
    print("\n== 各国覆盖天数 ==")
    print(days_per_country)
    sparse = days_per_country[days_per_country < 0.8 * days_per_country.max()]
    if not sparse.empty:
        print(f"[警告] 以下国家数据不完整，建议更换: {list(sparse.index)}")

    out.to_csv(args.output, index=False)
    print(f"\n== 已保存 {args.output}: {len(out):,} 行, "
          f"{out['spotify_id'].nunique():,} 首不同歌曲, "
          f"{out['snapshot_date'].nunique()} 天 ==")
    print(out.head(3).T)


if __name__ == "__main__":
    main()
