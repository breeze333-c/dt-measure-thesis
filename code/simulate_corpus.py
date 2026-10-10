# -*- coding: utf-8 -*-
"""
simulate_corpus.py —— 演示语料生成器（第 0 步，可整体跳过）

用途：
    本项目为"预演毕业论文"（方法学演示稿），为规避数据获取与版权限制，
    以程序方式生成一份【结构对齐真实年报"管理层讨论与分析(MD&A)"章节】的
    模拟中文语料，并同步生成配套的财务元数据（企业-年份面板）。

    真实研究时：将 data/corpus/*.txt 替换为从巨潮资讯网(http://www.cninfo.com.cn)
    下载的年报 PDF 中提取的 MD&A 文本（保留文件名 {股票代码}_{年份}.txt 约定），
    并用真实财务数据替换 data/financials_raw.csv，流水线代码无需任何改动。

生成逻辑：
    为每家样本公司赋予一个潜在的"数字化转型强度" d_it（企业异质性 + 年度趋势 +
    随机扰动），强度决定 (1) 文本中数字技术语句的出现频次（进而决定词典可命中的
    词频），(2) 研发强度、无形资产占比、ROA 等财务变量。该设计保证了语料内部
    存在可被测度方法捕捉的真实结构，从而演示"文本 -> 测度 -> 经济后果检验"的
    完整链条。

运行：
    python simulate_corpus.py
输出：
    data/corpus/{code}_{year}.txt   180 篇 MD&A 模拟文本
    data/firms.csv                  公司名录（代码/简称/行业/产权性质）
    data/financials_raw.csv         企业-年份财务元数据（含生成用潜在强度 d_true）
"""
import csv
import math
import os
import random
import re

random.seed(2026)  # 固定随机种子，保证语料可复现

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(BASE, "data", "corpus")
DATA_DIR = os.path.join(BASE, "data")

YEARS = [2021, 2022, 2023]
N_FIRMS = 60

INDUSTRIES = [
    ("C27", "医药制造业"), ("C38", "电气机械和器材制造业"), ("C39", "计算机、通信和其他电子设备制造业"),
    ("I65", "软件和信息技术服务业"), ("C34", "通用设备制造业"), ("C26", "化学原料和化学制品制造业"),
    ("F51", "批发业"), ("K70", "房地产业"),
]

# ---------- 公司名录 ----------
PRE = ["华", "中", "恒", "睿", "弘", "金", "泰", "德", "联", "新", "远", "天", "安", "宏", "瑞",
       "康", "益", "卓", "正", "兴", "嘉", "丰", "海", "凌", "光", "凯", "科", "蓝", "拓", "晟"]
MID = ["达", "创", "威", "讯", "能", "源", "拓", "迅", "搏", "锐", "盛", "信", "邦", "格", "尔"]
SUF = ["科技", "智造", "股份", "电子", "机械", "材料", "生物", "信息", "重工", "精密"]
EXCH = ["SZ", "SZ", "SZ", "SH", "SH"]  # 交易所后缀权重


def make_firms():
    used = set()
    firms = []
    for i in range(N_FIRMS):
        while True:
            name = random.choice(PRE) + random.choice(MID) + random.choice(SUF)
            if name not in used:
                used.add(name)
                break
        code = "%06d" % (i + 1)
        ind_code, ind_name = INDUSTRIES[i % len(INDUSTRIES)]
        firms.append({
            "code": code, "name": name, "exchange": random.choice(EXCH),
            "industry_code": ind_code, "industry_name": ind_name,
            "soe": 1 if random.random() < 0.25 else 0,
            "found_year": random.randint(1985, 2015),
        })
    return firms


# ---------- 语料模板 ----------
# 数字技术语句模板（{kw} 处从对应类别词典抽样填入，每句 2-4 个关键词）
DIG_TPL = {
    "人工智能技术": [
        "公司加大{kw1}领域的研发投入，将{kw2}算法应用于质检环节，并通过{kw3}模型持续优化工艺参数。",
        "报告期内，公司上线{kw1}平台，依托{kw2}与{kw3}技术实现关键工序的自动判定与预警。",
        "子公司与高校联合实验室围绕{kw1}开展攻关，相关{kw2}能力已在多条产线部署。",
    ],
    "大数据技术": [
        "公司建成集团级{kw1}中台，统一数据标准，完善{kw2}体系，为经营决策提供{kw3}支撑。",
        "依托{kw1}与{kw2}技术，公司构建了覆盖销售、供应、生产的一体化数据平台，实现{kw3}驱动的精准营销。",
        "报告期内，公司推进{kw1}治理专项，沉淀数据资产，形成可复用的{kw2}服务能力。",
    ],
    "云计算技术": [
        "公司核心业务系统整体{kw1}上云，采用{kw2}架构承载高并发业务，降低IT运行成本。",
        "报告期内，公司建设{kw1}与{kw2}节点，将研发测试环境迁移至{kw3}，资源利用率显著提升。",
        "公司采用{kw1}与{kw2}相结合的混合部署方案，保障核心数据安全与业务弹性。",
    ],
    "区块链技术": [
        "公司在供应链金融场景落地{kw1}应用，通过{kw2}与{kw3}机制保障交易不可篡改。",
        "报告期内，公司完成{kw1}存证平台二期建设，与上下游客户实现链上协同。",
    ],
    "数字技术应用": [
        "公司深化{kw1}建设，推进{kw2}与{kw3}改造，关键装备数控化率稳步提升。",
        "报告期内，公司入选省级{kw1}示范工厂，数字化转型进入全面推广阶段。",
        "公司打通线上线下渠道，构建{kw1}营销体系，用户全生命周期运营能力增强。",
        "公司积极融入{kw1}发展大局，围绕{kw2}加快业务模式升级。",
    ],
}

# 泛管理话语（用于区分效度检验的热词对照，与转型强度仅弱相关）
HOT_TPL = [
    "公司坚持{战略}引领，不断提升核心竞争力。",
    "报告期内，公司优化组织架构，人才梯队建设取得积极进展。",
    "公司聚焦主业，品牌影响力与市场竞争力持续增强。",
    "管理层认为，效率提升与降本增效仍是下阶段工作重点。",
    "公司完善内控体系，治理水平进一步提高。",
]

FILLER = [
    "报告期内，公司实现营业收入{rev}亿元，同比下降{down}%，主要受行业景气度波动影响。",
    "分产品看，主营业务收入结构保持稳定，核心产品市场份额稳中有升。",
    "公司持续推进渠道下沉，经销商网络覆盖进一步扩大。",
    "原材料价格波动对毛利率形成一定压力，公司通过集中采购与套期保值予以对冲。",
    "报告期末，公司资产总额{asset}亿元，资产负债结构总体稳健。",
    "公司严格遵守环保与安全生产法规，未发生重大安全环保事故。",
    "研发方面，公司全年研发投入{rd}亿元，新增授权专利{pat}项。",
    "公司继续加大市场开拓力度，海外业务收入占比稳步提升。",
    "报告期内，公司完成对两家子公司的增资，产能布局进一步优化。",
    "展望下一年度，公司将坚持稳健经营，努力实现高质量可持续发展。",
    "公司现金流状况良好，经营性现金流净额为正。",
    "人才方面，公司实施股权激励计划，核心团队保持稳定。",
    "公司深化与主要客户的战略合作，订单能见度有所提升。",
    "汇率波动对出口业务产生一定影响，公司已采取远期结售汇等应对措施。",
    "报告期内，公司获得高新技术企业复审通过，享受相应税收优惠。",
]


def fill(tpl, kws=None):
    s = tpl
    if kws:
        for i, kw in enumerate(kws, start=1):
            s = s.replace("{kw%d}" % i, kw)
    s = s.replace("{rev}", "%.1f" % random.uniform(8, 180))
    s = s.replace("{asset}", "%.1f" % random.uniform(10, 300))
    s = s.replace("{down}", "%.1f" % random.uniform(0.5, 18))
    s = s.replace("{rd}", "%.2f" % random.uniform(0.3, 8))
    s = s.replace("{pat}", str(random.randint(2, 60)))
    return s


def poisson(lam):
    """Knuth 泊松采样"""
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= random.random()
        if p <= L:
            return k
        k += 1


def gauss(mu, sigma):
    return random.gauss(mu, sigma)


def make_text(d, dicts):
    """按潜在转型强度 d 生成一篇 MD&A 模拟文本。

    设计要点（保证测度方法的可检验性）：
    1. 数字技术语句【跨类别共现】——每个语句组混合 2 个类别，模拟真实年报中
       "人工智能+大数据+云计算"等技术在同一段落密集共现的现象；
    2. 泛管理热词按转型强度【等比例】投放，使热词密度与转型强度在构念上相互独立，
       为区分效度检验提供干净的对照组。
    """
    cat_list = list(DIG_TPL.keys())
    paras = []
    n_overview = poisson(max(0.2, 3 * d))
    first = ["报告期内，公司围绕年度经营计划扎实推进各项工作，整体经营业绩保持平稳。"]
    for _ in range(n_overview):
        cat = random.choice(cat_list)
        kws = random.sample(dicts[cat], k=min(len(dicts[cat]), random.randint(2, 4)))
        first.append(fill(random.choice(DIG_TPL[cat]), kws))
    paras.append("".join(first))

    # 数字语句数量 ~ Poisson(5 + 60*d)
    n_dig = poisson(5 + 60 * d)
    n_hot = poisson(0.5 * (5 + 60 * d))   # 热词与数字语句等比例 -> 密度与强度独立
    n_fill = poisson(14)
    body = []
    # 数字技术语句成组出现，且每组混用 2 个类别（共现结构）
    while n_dig > 0:
        grp = min(n_dig, random.randint(2, 4))
        seg = []
        for _ in range(grp):
            cat = random.sample(cat_list, k=2)[random.randint(0, 1)]
            kws = random.sample(dicts[cat], k=min(len(dicts[cat]), random.randint(2, 4)))
            seg.append(fill(random.choice(DIG_TPL[cat]), kws))
            n_dig -= 1
        body.append("".join(seg))
    for _ in range(n_hot):
        body.append(fill(random.choice(HOT_TPL)))
    for _ in range(n_fill):
        body.append(fill(random.choice(FILLER)))
    random.shuffle(body)
    for i in range(0, len(body), 3):
        paras.append("".join(body[i:i + 3]))
    return "\n".join(paras)


def main():
    os.makedirs(CORPUS_DIR, exist_ok=True)
    firms = make_firms()

    with open(os.path.join(DATA_DIR, "firms.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["code", "name", "exchange", "industry_code", "industry_name", "soe", "found_year"])
        w.writeheader()
        w.writerows(firms)

    # 加载词典（供语句模板抽词）
    dicts = {}
    cur = None
    with open(os.path.join(BASE, "code", "dictionary", "digital_dict.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("["):
                cur = line.strip("[]")
                dicts[cur] = []
            else:
                dicts[cur].extend(re.split(r"\s+", line))

    rows = []
    for fm in firms:
        # 企业固有转型倾向：约 25% 高强度、50% 中低强度、25% 极低
        base = random.choice([random.uniform(0.18, 0.32), random.uniform(0.04, 0.14), random.uniform(0.0, 0.03)])
        size0 = gauss(22.2, 1.1)
        lev0 = min(0.75, max(0.08, gauss(0.42, 0.12)))
        for t, yr in enumerate(YEARS):
            d = max(0.0, min(0.45, base + 0.035 * t + gauss(0, 0.02)))
            text = make_text(d, dicts)
            with open(os.path.join(CORPUS_DIR, "%s_%d.txt" % (fm["code"], yr)), "w", encoding="utf-8") as tf:
                tf.write(text)
            size = size0 + 0.04 * t + gauss(0, 0.05)
            lev = min(0.8, max(0.05, lev0 + gauss(0, 0.02)))
            age = yr - fm["found_year"]
            roa = 0.018 + 0.055 * d - 0.02 * (lev - 0.42) - 0.002 * t + gauss(0, 0.012)
            rd = 0.018 + 0.09 * d + 0.006 * (size - 22.2) + (0.01 if fm["industry_code"] in ("I65", "C39", "C27") else 0) + abs(gauss(0, 0.006))
            intangible = max(0.002, 0.02 + 0.045 * d + abs(gauss(0, 0.008)))
            rows.append({
                "code": fm["code"], "year": yr, "size": round(size, 4), "lev": round(lev, 4),
                "age": age, "roa": round(roa, 5), "rd": round(rd, 5),
                "intangible_ratio": round(intangible, 5), "d_true": round(d, 5),
            })

    with open(os.path.join(DATA_DIR, "financials_raw.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("语料生成完成：%d 篇 MD&A 文本 -> %s" % (len(rows), os.path.relpath(CORPUS_DIR, BASE)))
    print("财务元数据：%d 条企业-年份记录 -> data/financials_raw.csv" % len(rows))


if __name__ == "__main__":
    main()
