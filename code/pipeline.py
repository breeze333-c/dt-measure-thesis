# -*- coding: utf-8 -*-
"""
pipeline.py —— NLP 测度构建五步流水线（主脚本）

研究设计：基于上市公司年报"管理层讨论与分析(MD&A)"文本，
          构建企业数字化转型测度，并检验其经济后果。

五步流水线（NLP 测度构建方法）：
    Step 1  文本获取   Acquisition     —— 语料清单化、抽样与企业-年份映射
    Step 2  文本预处理 Preprocessing   —— 清洗、全半角归一、字数统计
    Step 3  词典构建   Dictionary      —— 五类数字技术词典加载与匹配模式编译
    Step 4  测度计算   Measurement     —— 词频统计、三类指标公式、变量定义与面板合并
    Step 5  检验分析   Validation      —— 信度（Cronbach α / 折半）、效度（聚合/区分/复测）、
                                          描述性统计、相关性、OLS 回归（含年度与行业固定效应）

依赖：仅 Python 标准库（csv / re / math / statistics），零第三方依赖，保证可复现。
运行：
    python pipeline.py
输出：
    data/panel.csv                  企业-年份面板（测度结果 + 财务变量）
    results/descriptive_stats.csv   描述性统计
    results/correlation_matrix.csv  相关性矩阵
    results/reliability_validity.csv 信度与效度检验结果
    results/regression_results.csv  回归结果表
    results/summary.md              全部结果摘要（供论文引用）
"""
import csv
import math
import os
import re
import statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(BASE, "data", "corpus")
DATA_DIR = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "results")
DICT_PATH = os.path.join(BASE, "code", "dictionary", "digital_dict.txt")
HOTWORDS = ["战略", "竞争力", "品牌", "人才", "效率", "治理", "内控", "聚焦主业"]

os.makedirs(RESULT_DIR, exist_ok=True)


# =====================================================================
# Step 1  文本获取 Acquisition
# =====================================================================
def step1_acquire():
    """扫描语料目录，解析 {股票代码}_{年份}.txt，返回企业-年份文档清单。"""
    docs = []
    for fn in sorted(os.listdir(CORPUS_DIR)):
        m = re.match(r"^(\d{6})_(\d{4})\.txt$", fn)
        if not m:
            continue
        docs.append({"code": m.group(1), "year": int(m.group(2)), "path": os.path.join(CORPUS_DIR, fn)})
    if not docs:
        raise SystemExit("Step1 失败：data/corpus 下未找到任何 {code}_{year}.txt 文件。")
    print("[Step1 文本获取] 共定位 %d 篇企业-年份文档" % len(docs))
    return docs


# =====================================================================
# Step 2  文本预处理 Preprocessing
# =====================================================================
_FULL2HALF = {ord(f): ord(t) for f, t in zip(
    "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")}


def clean_text(raw):
    """年报文本清洗：去空白噪声、全角转半角、英文字母统一小写（保留 5G/B2B 类词形）。"""
    t = raw.replace("\u3000", " ")
    t = t.translate(_FULL2HALF)          # 全角字母数字 -> 半角
    t = re.sub(r"\s+", "", t)            # 中文文本去除全部空白（词频以子串计）
    t = re.sub(r"第[一二三四五六七八九十]+节[^\n]{0,20}", "", t)
    t = re.sub(r"（[一二三四五六七八九十]+）", "", t)
    return t.lower()


def step2_preprocess(docs):
    for d in docs:
        with open(d["path"], encoding="utf-8") as f:
            raw = f.read()
        d["clean"] = clean_text(raw)
        d["n_chars"] = len(d["clean"])
    print("[Step2 文本预处理] 清洗完成，语料总字数 %d，均值 %.0f 字/篇"
          % (sum(d["n_chars"] for d in docs), statistics.mean(d["n_chars"] for d in docs)))
    return docs


# =====================================================================
# Step 3  词典构建 Dictionary
# =====================================================================
def step3_dictionary():
    """加载五类数字技术词典，编译不区分大小写的匹配模式（长词优先）。"""
    cats, cur = {}, None
    with open(DICT_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("["):
                cur = line.strip("[]")
                cats[cur] = []
            else:
                cats[cur].extend(w for w in re.split(r"\s+", line) if w)
    patterns = {}
    n_words = 0
    for cat, words in cats.items():
        words_sorted = sorted(set(words), key=len, reverse=True)  # 长词优先交替，保证最长匹配
        patterns[cat] = re.compile("|".join(re.escape(w.lower()) for w in words_sorted))
        n_words += len(words_sorted)
    print("[Step3 词典构建] %d 个类别、%d 个词项" % (len(cats), n_words))
    return cats, patterns


# =====================================================================
# Step 4  测度计算 Measurement
# =====================================================================
def step4_measure(docs, patterns):
    for d in docs:
        t = d["clean"]
        cat_cnt = {}
        for cat, pat in patterns.items():
            cat_cnt[cat] = len(pat.findall(t))
        d["hot_freq"] = sum(t.count(w) for w in HOTWORDS)  # 泛管理热词（区分效度对照组）
        freq = sum(cat_cnt.values())
        d["DT_freq"] = freq                                             # 总词频
        d["DT1"] = math.log(1 + freq)                                   # 对数化：ln(1+词频)
        d["DT2"] = freq / (d["n_chars"] / 10000.0)                      # 相对化：每万字词频
        p = [c / freq for c in cat_cnt.values() if c > 0]
        d["DT3"] = -sum(pi * math.log(pi) for pi in p) if p else 0.0    # 多元度：类别熵
        for cat, c in cat_cnt.items():
            d["cat_" + cat] = c
    print("[Step4 测度计算] 词频与三类指标计算完成（DT1=ln(1+词频), DT2=每万字词频, DT3=类别熵）")
    return docs


def load_financials():
    rows = {}
    with open(os.path.join(DATA_DIR, "financials_raw.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows[(r["code"], int(r["year"]))] = r
    return rows


def merge_panel(docs, cats):
    """变量定义表见论文表 2；输出企业-年份面板。"""
    fin = load_financials()
    firms = {}
    with open(os.path.join(DATA_DIR, "firms.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            firms[r["code"]] = r
    panel = []
    for d in docs:
        key = (d["code"], d["year"])
        if key not in fin:
            continue
        row = {"code": d["code"], "name": firms[d["code"]]["name"],
               "year": d["year"],
               "industry": firms[d["code"]]["industry_name"],
               "soe": int(firms[d["code"]]["soe"]),
               "n_chars": d["n_chars"], "hot_freq": d["hot_freq"],
               "DT_freq": d["DT_freq"], "DT1": round(d["DT1"], 4),
               "DT2": round(d["DT2"], 4), "DT3": round(d["DT3"], 4)}
        for cat in sorted(cats):
            row["cat_" + cat] = d["cat_" + cat]
        f5 = fin[key]
        row.update({"size": round(float(f5["size"]), 4), "lev": round(float(f5["lev"]), 4),
                    "age": int(f5["age"]), "roa": round(float(f5["roa"]), 5),
                    "rd": round(float(f5["rd"]), 5),
                    "intangible_ratio": round(float(f5["intangible_ratio"]), 5)})
        panel.append(row)
    panel.sort(key=lambda r: (r["code"], r["year"]))
    out = os.path.join(DATA_DIR, "panel.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(panel[0].keys()))
        w.writeheader()
        w.writerows(panel)
    print("[Step4 面板合并] 企业-年份面板 %d 条 -> data/panel.csv" % len(panel))
    return panel


# =====================================================================
# 统计工具（纯标准库实现）
# =====================================================================
def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx, sy = statistics.stdev(xs), statistics.stdev(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (len(xs) - 1)
    return cov / (sx * sy)


def cronbach_alpha(rows):
    """rows: 观测行列表，每行为各分量（五类词频）取值。"""
    k = len(rows[0])
    var_k = [statistics.variance(col) for col in zip(*rows)]
    tot = statistics.variance([sum(r) for r in rows])
    return k / (k - 1) * (1 - sum(var_k) / tot)


def zscore(xs):
    m, s = statistics.mean(xs), statistics.stdev(xs)
    return [(x - m) / s for x in xs]


def _solve(aug, k):
    """高斯消元求解 k 元线性方程组（aug 为 k x (k+1) 增广矩阵）。"""
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(aug[r][c]))
        aug[c], aug[piv] = aug[piv], aug[c]
        pv = aug[c][c]
        aug[c] = [v / pv for v in aug[c]]
        for r in range(k):
            if r != c and aug[r][c] != 0:
                fac = aug[r][c]
                aug[r] = [v - fac * w for v, w in zip(aug[r], aug[c])]
    return [aug[i][k] for i in range(k)]


def ols(y, X, names):
    """普通最小二乘（正规方程 + 高斯消元），返回系数表、R2、N。"""
    n, k = len(y), len(X[0])
    xtx = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k)]
    beta = _solve([xtx[i][:] + [xty[i]] for i in range(k)], k)
    yhat = [sum(X[i][j] * beta[j] for j in range(k)) for i in range(n)]
    ssr = sum((yi - yh) ** 2 for yi, yh in zip(y, yhat))
    sst = sum((yi - statistics.mean(y)) ** 2 for yi in y)
    r2 = 1 - ssr / sst
    sigma2 = ssr / (n - k)
    out = []
    for j in range(k):
        e = [1.0 if i == j else 0.0 for i in range(k)]           # 求 (X'X)^-1 第 j 列
        col = _solve([xtx[i][:] + [e[i]] for i in range(k)], k)
        se = math.sqrt(sigma2 * col[j])
        t = beta[j] / se if se > 0 else 0.0
        star = "***" if abs(t) >= 2.576 else "**" if abs(t) >= 1.96 else "*" if abs(t) >= 1.645 else ""
        out.append({"var": names[j], "coef": round(beta[j], 5), "se": round(se, 5),
                    "t": round(t, 3), "sig": star})
    return out, r2, n


# =====================================================================
# Step 5  检验分析 Validation
# =====================================================================
def step5_analyze(panel, cats):
    cat_names = sorted(cats)
    summary = ["# 测度结果与检验分析摘要（由 pipeline.py 自动生成）", ""]

    # ---------- 5.1 信度 ----------
    alpha_rows = [[r["cat_" + c] for c in cat_names] for r in panel]
    alpha = cronbach_alpha(alpha_rows)
    half_a = [sum(r["cat_" + c] for c in cat_names[0::2]) for r in panel]
    half_b = [sum(r["cat_" + c] for c in cat_names[1::2]) for r in panel]
    r_half = pearson(half_a, half_b)
    sb = 2 * r_half / (1 + r_half)

    # ---------- 5.2 效度 ----------
    dt1 = [r["DT1"] for r in panel]
    dt2 = [r["DT2"] for r in panel]
    intang = [r["intangible_ratio"] for r in panel]
    hot10k = [r["hot_freq"] / (r["n_chars"] / 10000.0) for r in panel]
    r_conv = pearson(dt1, intang)
    r_disc = pearson(dt1, hot10k)
    r_alt = pearson(dt1, dt2)

    rel_rows = [
        {"检验": "内部一致性信度", "指标": "Cronbach's α（五类词频）", "取值": round(alpha, 4),
         "判断": "通过" if alpha > 0.7 else "未通过"},
        {"检验": "折半信度", "指标": "Spearman-Brown 系数", "取值": round(sb, 4),
         "判断": "通过" if sb > 0.7 else "未通过"},
        {"检验": "聚合效度", "指标": "corr(DT1, 无形资产占比)", "取值": round(r_conv, 4),
         "判断": "通过" if r_conv > 0.4 else "弱" if r_conv > 0.2 else "未通过"},
        {"检验": "区分效度", "指标": "corr(DT1, 泛管理热词/万字)", "取值": round(r_disc, 4),
         "判断": "低于聚合效度相关，区分良好" if r_disc < r_conv else "未通过"},
        {"检验": "复测效度", "指标": "corr(DT1, DT2 备择测度)", "取值": round(r_alt, 4),
         "判断": "高相关，测度稳健" if r_alt > 0.7 else "一般"},
    ]
    with open(os.path.join(RESULT_DIR, "reliability_validity.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["检验", "指标", "取值", "判断"])
        w.writeheader()
        w.writerows(rel_rows)
    summary += ["## 信度与效度检验", "", "| 检验 | 指标 | 取值 | 判断 |", "| --- | --- | --- | --- |"]
    summary += ["| {} | {} | {} | {} |".format(*r.values()) for r in rel_rows]
    summary.append("")

    # ---------- 5.3 描述性统计 ----------
    def desc(xs):
        xs = sorted(xs)
        n = len(xs)
        q = lambda p: xs[min(n - 1, max(0, int(round(p * (n - 1)))))]
        return (n, round(statistics.mean(xs), 4), round(statistics.stdev(xs), 4),
                round(xs[0], 4), round(q(0.25), 4), round(q(0.5), 4),
                round(q(0.75), 4), round(xs[-1], 4))

    desc_vars = [("DT1", "ln(1+词频)"), ("DT2", "每万字词频"), ("DT3", "类别熵"),
                 ("DT_freq", "总词频"), ("roa", "总资产收益率"), ("rd", "研发强度"),
                 ("intangible_ratio", "无形资产占比"), ("size", "企业规模"),
                 ("lev", "资产负债率"), ("age", "企业年龄")]
    drows = []
    for v, lab in desc_vars:
        drows.append((v, lab) + desc([r_[v] for r_ in panel]))
    with open(os.path.join(RESULT_DIR, "descriptive_stats.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["变量", "含义", "N", "均值", "标准差", "最小值", "P25", "中位数", "P75", "最大值"])
        w.writerows(drows)
    summary += ["## 描述性统计", "",
                "| 变量 | 含义 | N | 均值 | 标准差 | 最小值 | P25 | 中位数 | P75 | 最大值 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    summary += ["| " + " | ".join(str(x) for x in row) + " |" for row in drows]
    summary.append("")

    # ---------- 5.4 相关性 ----------
    corr_vars = ["DT1", "DT2", "DT3", "roa", "rd", "intangible_ratio", "size", "lev", "age"]
    cm = []
    for a in corr_vars:
        row = [a]
        for b in corr_vars:
            row.append(round(pearson([r_[a] for r_ in panel], [r_[b] for r_ in panel]), 3))
        cm.append(row)
    with open(os.path.join(RESULT_DIR, "correlation_matrix.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(corr_vars)
        w.writerows(cm)
    summary += ["## 相关性矩阵（Pearson）", "",
                "| " + " | ".join(corr_vars) + " |", "|" + " --- |" * len(corr_vars)]
    summary += ["| " + " | ".join(str(x) for x in row) + " |" for row in cm]
    summary.append("")

    # ---------- 5.5 回归（含年度与行业固定效应） ----------
    years = sorted({r_["year"] for r_ in panel})
    inds = sorted({r_["industry"] for r_ in panel})
    DTz, DT2z = zscore(dt1), zscore(dt2)

    def design(dtcol):
        X, names = [], []
        for i, r_ in enumerate(panel):
            x = [1.0, dtcol[i], r_["size"], r_["lev"], r_["age"] / 100.0, r_["soe"]]
            for yy in years[1:]:
                x.append(1.0 if r_["year"] == yy else 0.0)
            for ii in inds[1:]:
                x.append(1.0 if r_["industry"] == ii else 0.0)
            X.append(x)
        names = (["常数项", "数字化转型DT", "企业规模Size", "资产负债率Lev", "企业年龄Age", "产权性质SOE"]
                 + ["年份%d" % yy for yy in years[1:]] + ["行业%d" % i for i in range(1, len(inds))])
        return X, names

    models = [
        ("模型1：ROA", [r_["roa"] for r_ in panel], DTz),
        ("模型2：研发强度RD", [r_["rd"] for r_ in panel], DTz),
        ("模型3：ROA（备择测度DT2）", [r_["roa"] for r_ in panel], DT2z),
    ]
    reg_tables, r2_map = [], {}
    show_vars = {"数字化转型DT", "企业规模Size", "资产负债率Lev", "企业年龄Age", "产权性质SOE"}
    for label, dep, dtcol in models:
        X, names = design(dtcol)
        res, r2, n = ols(dep, X, names)
        r2_map[label] = (round(r2, 4), n)
        for r_ in res:
            if r_["var"] in show_vars:
                reg_tables.append({"模型": label, **r_})
        reg_tables.append({"模型": label, "var": "R2", "coef": round(r2, 4), "se": "", "t": "", "sig": ""})
        reg_tables.append({"模型": label, "var": "N", "coef": n, "se": "", "t": "", "sig": ""})

    with open(os.path.join(RESULT_DIR, "regression_results.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["模型", "var", "coef", "se", "t", "sig"])
        w.writeheader()
        w.writerows(reg_tables)

    summary += ["## 回归结果（DT 为 z 标准化；控制年度与行业固定效应）", ""]
    for label, _, _ in models:
        rows = [r_ for r_ in reg_tables if r_["模型"] == label]
        summary += ["### " + label, "", "| 变量 | 系数 | 标准误 | t值 | 显著性 |", "| --- | --- | --- | --- | --- |"]
        summary += ["| {} | {} | {} | {} | {} |".format(r_["var"], r_["coef"], r_["se"], r_["t"], r_["sig"]) for r_ in rows]
        summary.append("")
    summary.append("> 注：*** p<0.01, ** p<0.05, * p<0.1（正态近似）")

    with open(os.path.join(RESULT_DIR, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
    print("[Step5 检验分析] Cronbach α=%.3f | 折半 SB=%.3f | 聚合 r=%.3f | 区分 r=%.3f | 备择 r=%.3f"
          % (alpha, sb, r_conv, r_disc, r_alt))
    for label, _, _ in models:
        print("    %s  R2=%.3f  N=%d" % (label, r2_map[label][0], r2_map[label][1]))
    print("全部结果输出至 results/ 目录；摘要见 results/summary.md")


def main():
    docs = step1_acquire()
    docs = step2_preprocess(docs)
    cats, patterns = step3_dictionary()
    docs = step4_measure(docs, patterns)
    panel = merge_panel(docs, cats)
    step5_analyze(panel, cats)


if __name__ == "__main__":
    main()
