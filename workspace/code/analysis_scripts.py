# LLM Agent 发展历程 - 数据分析脚本
# 创建时间: 2024年12月

import pandas as pd
import numpy as np

# 数据定义 - LLM Agent 发展指标 (2020-2024)
llm_agent_data = {
    'year': [2020, 2021, 2022, 2023, 2024],
    'tech_maturity': [20, 35, 60, 80, 90],  # 技术成熟度 (%)
    'market_adoption': [10, 20, 45, 75, 85],  # 市场采用率 (%)
    'papers_count': [5, 15, 45, 120, 180],  # 论文数量
    'key_events': [
        '大语言模型初步发展',
        'GPT-3等技术突破',
        'ChatGPT发布，AI普及',
        'LLM Agent概念兴起',
        'AI Agent元年，多智能体发展'
    ]
}

def calculate_growth_metrics(data):
    """计算增长指标"""
    df = pd.DataFrame(data)
    
    # 计算年增长率
    df['tech_growth_rate'] = df['tech_maturity'].pct_change() * 100
    df['market_growth_rate'] = df['market_adoption'].pct_change() * 100
    df['papers_growth_rate'] = df['papers_count'].pct_change() * 100
    
    # 计算总体增长率
    total_tech_growth = ((df['tech_maturity'].iloc[-1] - df['tech_maturity'].iloc[0]) / df['tech_maturity'].iloc[0]) * 100
    total_market_growth = ((df['market_adoption'].iloc[-1] - df['market_adoption'].iloc[0]) / df['market_adoption'].iloc[0]) * 100
    total_papers_growth = ((df['papers_count'].iloc[-1] - df['papers_count'].iloc[0]) / df['papers_count'].iloc[0]) * 100
    
    return df, total_tech_growth, total_market_growth, total_papers_growth

def calculate_correlations(data):
    """计算相关性矩阵"""
    df = pd.DataFrame(data)
    correlation_matrix = df[['tech_maturity', 'market_adoption', 'papers_count']].corr()
    return correlation_matrix

def analyze_trends(data):
    """分析发展趋势"""
    df = pd.DataFrame(data)
    
    # 线性回归分析
    from sklearn.linear_model import LinearRegression
    
    X = df[['year']]
    
    trends = {}
    for column in ['tech_maturity', 'market_adoption', 'papers_count']:
        y = df[column]
        model = LinearRegression()
        model.fit(X, y)
        trends[column] = {
            'slope': model.coef_[0],
            'intercept': model.intercept_,
            'r_squared': model.score(X, y)
        }
    
    return trends

# 执行分析
if __name__ == "__main__":
    print("=== LLM Agent 发展历程数据分析 ===\n")
    
    # 计算增长指标
    df, tech_growth, market_growth, papers_growth = calculate_growth_metrics(llm_agent_data)
    
    print("1. 总体增长分析:")
    print(f"   技术成熟度增长: {tech_growth:.1f}%")
    print(f"   市场采用率增长: {market_growth:.1f}%")
    print(f"   论文数量增长: {papers_growth:.1f}%")
    
    print("\n2. 年度增长详情:")
    print(df.to_string(index=False))
    
    # 计算相关性
    correlation_matrix = calculate_correlations(llm_agent_data)
    print("\n3. 相关性分析:")
    print(correlation_matrix.round(4))
    
    # 趋势分析
    trends = analyze_trends(llm_agent_data)
    print("\n4. 趋势分析:")
    for key, value in trends.items():
        print(f"   {key}: 斜率={value['slope']:.2f}, R²={value['r_squared']:.4f}")
    
    print("\n5. 发展阶段分析:")
    print("   2020-2021: 萌芽期 (技术探索)")
    print("   2022-2023: 成长期 (技术突破)")
    print("   2024: 成熟期 (广泛应用)")
    
    # 预测2025年发展
    print("\n6. 2025年预测:")
    for key, trend in trends.items():
        prediction = trend['slope'] * 2025 + trend['intercept']
        print(f"   {key}: 预计{int(prediction)} ({trend['slope']:.1f}/年增长)")