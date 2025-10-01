# LLM Agent 发展历程定量分析代码

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class LLMAgentAnalysis:
    """LLM Agent 发展历程分析类"""
    
    def __init__(self):
        self.development_data = self._load_development_data()
        self.market_data = self._load_market_data()
        self.technology_data = self._load_technology_data()
    
    def _load_development_data(self):
        """加载发展历程数据"""
        return {
            '年份': ['2020', '2021', '2022', '2023', '2024'],
            '阶段': ['基础能力建设', '基础能力建设', '推理能力突破', '自主性发展', '多智能体协作'],
            '技术成熟度': [20, 35, 60, 80, 90],
            '市场关注度': [15, 25, 45, 75, 85],
            '学术论文数量': [50, 120, 350, 800, 1200],
            '开源项目数量': [10, 25, 80, 250, 500]
        }
    
    def _load_market_data(self):
        """加载市场数据"""
        return {
            '年份': ['2020', '2021', '2022', '2023', '2024', '2025', '2026', '2027', '2028', '2029', '2030'],
            'LLM市场规模(十亿美元)': [0.5, 1.2, 2.8, 5.6, 6.4, 8.5, 11.2, 15.0, 20.0, 28.0, 36.1],
            'AI Agent市场规模(十亿美元)': [0.1, 0.3, 1.2, 3.5, 5.26, 7.9, 12.5, 19.8, 30.5, 38.2, 46.58],
            '年增长率(%)': [0, 200, 300, 192, 50, 50, 58, 58, 54, 25, 22]
        }
    
    def _load_technology_data(self):
        """加载技术采用数据"""
        return {
            '阶段': ['创新者', '早期采用者', '早期大众', '晚期大众', '落后者'],
            '时间范围': ['2020-2022', '2023-2024', '2025-2026', '2027-2028', '2029+'],
            '市场份额(%)': [2.5, 13.5, 34, 34, 16],
            '主要用户': ['研究人员', '科技公司', '企业用户', '传统行业', '保守用户']
        }
    
    def calculate_growth_metrics(self):
        """计算增长指标"""
        df = pd.DataFrame(self.development_data)
        
        metrics = {}
        for i in range(1, len(df)):
            year = df.loc[i, '年份']
            tech_growth = df.loc[i, '技术成熟度'] - df.loc[i-1, '技术成熟度']
            market_growth = df.loc[i, '市场关注度'] - df.loc[i-1, '市场关注度']
            paper_growth = df.loc[i, '学术论文数量'] - df.loc[i-1, '学术论文数量']
            
            metrics[year] = {
                '技术成熟度增长': tech_growth,
                '市场关注度增长': market_growth,
                '学术论文增长': paper_growth
            }
        
        return metrics
    
    def calculate_market_cagr(self):
        """计算市场复合年增长率"""
        df = pd.DataFrame(self.market_data)
        start_value = df.loc[4, 'AI Agent市场规模(十亿美元)']  # 2024
        end_value = df.loc[10, 'AI Agent市场规模(十亿美元)']   # 2030
        years = 6
        
        cagr = (end_value / start_value) ** (1/years) - 1
        return cagr
    
    def generate_development_report(self):
        """生成发展报告"""
        df_dev = pd.DataFrame(self.development_data)
        df_market = pd.DataFrame(self.market_data)
        df_tech = pd.DataFrame(self.technology_data)
        
        report = {
            '发展概况': {
                '当前阶段': df_dev.loc[4, '阶段'],
                '技术成熟度': f"{df_dev.loc[4, '技术成熟度']}%",
                '市场关注度': f"{df_dev.loc[4, '市场关注度']}/100"
            },
            '学术研究': {
                '累计论文数量': df_dev.loc[4, '学术论文数量'],
                '累计开源项目': df_dev.loc[4, '开源项目数量']
            },
            '市场预测': {
                '2030年AI Agent市场规模': f"{df_market.loc[10, 'AI Agent市场规模(十亿美元)']}十亿美元",
                '2024-2030年CAGR': f"{self.calculate_market_cagr():.1%}",
                '技术采用阶段': df_tech.loc[1, '阶段']  # 当前处于早期采用者阶段
            }
        }
        
        return report

# 使用示例
if __name__ == "__main__":
    analyzer = LLMAgentAnalysis()
    
    # 计算增长指标
    growth_metrics = analyzer.calculate_growth_metrics()
    print("=== 增长指标分析 ===")
    for year, metrics in growth_metrics.items():
        print(f"{year}年:")
        for metric, value in metrics.items():
            print(f"  {metric}: {value}")
    
    # 计算CAGR
    cagr = analyzer.calculate_market_cagr()
    print(f"\n2024-2030年复合年增长率(CAGR): {cagr:.1%}")
    
    # 生成报告
    report = analyzer.generate_development_report()
    print("\n=== 发展报告 ===")
    for category, data in report.items():
        print(f"{category}:")
        for key, value in data.items():
            print(f"  {key}: {value}")