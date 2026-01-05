# 文件名: evening_push.py
import akshare as ak
import pandas as pd
import datetime
import requests
import os
import re

# 1. 获取 Key
KEYS_STR = os.getenv("SERVERCHAN_KEY", "")

# 2. 辅助函数：将中文单位(亿/万)转换为数字(亿元)
def parse_money(value):
    try:
        # 如果已经是数字
        if isinstance(value, (int, float)):
            return float(value) / 1e8
        
        # 如果是字符串，处理单位
        str_val = str(value)
        if '亿' in str_val:
            return float(str_val.replace('亿', '')) 
        elif '万' in str_val:
            return float(str_val.replace('万', '')) / 10000
        else:
            return float(str_val) / 1e8
    except:
        return 0.0

def get_market_analysis():
    print("🌙 正在生成【A股复盘】(使用资金流接口)...")
    summary_lines = []
    
    try:
        # === 核心修改：使用资金流向专用接口 ===
        # indicator="今日" 代表获取当天的实时资金流排行
        # 返回列名通常包含：['名称', '今日涨跌幅', '今日主力净流入', '今日超大单净流入'...]
        
        # 1. 抓取行业数据
        df_ind = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
        
        # 2. 抓取概念数据
        df_con = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流")
        
        # 3. 确定列名 (防止接口字段微调)
        # 自动寻找包含 "涨跌幅" 和 "主力净流入" 的列
        name_col = next((x for x in df_ind.columns if "名称" in x), "名称")
        pct_col = next((x for x in df_ind.columns if "涨跌幅" in x), "今日涨跌幅")
        flow_col = next((x for x in df_ind.columns if "主力净流入" in x), "今日主力净流入")

        # === 分析 1: 领涨行业 (按涨跌幅排序) ===
        # 转换涨跌幅为浮点数以便排序 (去掉%)
        df_ind['sort_pct'] = df_ind[pct_col].astype(str).str.replace('%','').astype(float)
        top_ind = df_ind.sort_values(by='sort_pct', ascending=False).head(3)
        
        summary_lines.append("🔥 **领涨行业**:")
        for _, row in top_ind.iterrows():
            name = row[name_col]
            pct = row[pct_col]
            # 清洗资金数据
            flow_val = parse_money(row[flow_col])
            summary_lines.append(f"• **{name}**: {pct} (主力 {flow_val:+.1f}亿)")
        summary_lines.append("")

        # === 分析 2: 热门概念 ===
        df_con['sort_pct'] = df_con[pct_col].astype(str).str.replace('%','').astype(float)
        top_con = df_con.sort_values(by='sort_pct', ascending=False).head(3)
        
        summary_lines.append("💡 **热门概念**:")
        for _, row in top_con.iterrows():
            name = row[name_col]
            pct = row[pct_col]
            summary_lines.append(f"• {name}: {pct}")
        summary_lines.append("")

        # === 分析 3: 主力抢筹 (按净流入排序) ===
        # 先把资金列全部转为数字(亿元)用于排序
        df_ind['sort_flow'] = df_ind[flow_col].apply(parse_money)
        top_flow = df_ind.sort_values(by='sort_flow', ascending=False).head(3)
        
        summary_lines.append("💰 **主力抢筹**:")
        for _, row in top_flow.iterrows():
            name = row[name_col]
            flow_val = row['sort_flow']
            pct = row[pct_col]
            summary_lines.append(f"• **{name}**: {flow_val:+.1f}亿 (涨幅 {pct})")

        # 生成标题
        first_name = top_ind.iloc[0][name_col]
        first_pct = top_ind.iloc[0][pct_col]
        title = f"A股复盘: {first_name} {first_pct} | 主力动向"
        
        today = datetime.datetime.now().strftime("%m-%d %H:%M")
        content = f"📅 {today}\n\n" + "\n\n".join(summary_lines)
        return title, content

    except Exception as e:
        import traceback
        traceback.print_exc()
        return "分析失败", f"数据解析错误: {str(e)}"

def push_to_wechat(title, content):
    if not KEYS_STR: 
        print("⚠️ 未配置 Key")
        return
    keys = KEYS_STR.split(",")
    for key in keys:
        key = key.strip()
        if not key: continue
        url = f"https://sctapi.ftqq.com/{key}.send"
        requests.post(url, data={"title": title, "desp": content})
        print(f"✅ 推送给 ...{key[-4:]}")

if __name__ == "__main__":
    title, content = get_market_analysis()
    print("----------------")
    print(title)
    print(content)
    print("----------------")
    push_to_wechat(title, content)
