"""
ML Model Metrics Visualization Script
Creates comprehensive visualizations of anomaly detection results
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import numpy as np

# Configuration
ES_HOST = "http://localhost:9200"
ML_INDEX = "firefox-ml-anomalies-*"

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def fetch_anomalies(hours=24, size=1000):
    """Fetch anomalies from Elasticsearch"""
    query = {
        "size": size,
        "query": {
            "range": {
                "@timestamp": {
                    "gte": f"now-{hours}h"
                }
            }
        },
        "sort": [{"@timestamp": "desc"}]
    }
    
    response = requests.post(f"{ES_HOST}/{ML_INDEX}/_search", json=query)
    data = response.json()
    
    anomalies = []
    for hit in data['hits']['hits']:
        anomalies.append(hit['_source'])
    
    return pd.DataFrame(anomalies)

def plot_score_timeline(df):
    """Plot anomaly score over time"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    df['@timestamp'] = pd.to_datetime(df['@timestamp'])
    df = df.sort_values('@timestamp')
    
    ax.plot(df['@timestamp'], df['anomaly_score'], 
            marker='o', linestyle='-', linewidth=2, markersize=6)
    
    # Add threshold line
    ax.axhline(y=70, color='r', linestyle='--', label='High Score Threshold')
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Anomaly Score', fontsize=12)
    ax.set_title('Anomaly Score Timeline (Last 24h)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('ml_metrics_timeline.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: ml_metrics_timeline.png")
    plt.show()

def plot_type_distribution(df):
    """Plot anomaly type distribution"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Pie chart
    type_counts = df['anomaly_type'].value_counts()
    colors = sns.color_palette('Set2', len(type_counts))
    ax1.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%',
            startangle=90, colors=colors)
    ax1.set_title('Anomaly Type Distribution', fontsize=14, fontweight='bold')
    
    # Bar chart
    type_counts.plot(kind='barh', ax=ax2, color=colors)
    ax2.set_xlabel('Count', fontsize=12)
    ax2.set_ylabel('Anomaly Type', fontsize=12)
    ax2.set_title('Anomaly Type Counts', fontsize=14, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('ml_metrics_types.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: ml_metrics_types.png")
    plt.show()

def plot_severity_heatmap(df):
    """Plot severity distribution over time"""
    df['@timestamp'] = pd.to_datetime(df['@timestamp'])
    df['hour'] = df['@timestamp'].dt.hour
    
    # Create pivot table
    severity_hourly = pd.crosstab(df['severity'], df['hour'])
    
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(severity_hourly, annot=True, fmt='d', cmap='YlOrRd', 
                cbar_kws={'label': 'Count'}, ax=ax)
    
    ax.set_xlabel('Hour of Day', fontsize=12)
    ax.set_ylabel('Severity', fontsize=12)
    ax.set_title('Anomaly Severity Heatmap by Hour', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('ml_metrics_severity_heatmap.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: ml_metrics_severity_heatmap.png")
    plt.show()

def plot_score_distribution(df):
    """Plot anomaly score distribution"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Histogram
    ax1.hist(df['anomaly_score'], bins=20, color='skyblue', edgecolor='black', alpha=0.7)
    ax1.axvline(df['anomaly_score'].mean(), color='red', linestyle='--', 
                label=f'Mean: {df["anomaly_score"].mean():.2f}')
    ax1.axvline(df['anomaly_score'].median(), color='green', linestyle='--',
                label=f'Median: {df["anomaly_score"].median():.2f}')
    ax1.set_xlabel('Anomaly Score', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('Anomaly Score Distribution', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # Box plot by type
    df.boxplot(column='anomaly_score', by='anomaly_type', ax=ax2)
    ax2.set_xlabel('Anomaly Type', fontsize=12)
    ax2.set_ylabel('Anomaly Score', fontsize=12)
    ax2.set_title('Score Distribution by Type', fontsize=14, fontweight='bold')
    plt.suptitle('')  # Remove auto-generated title
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('ml_metrics_score_distribution.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: ml_metrics_score_distribution.png")
    plt.show()

def plot_feature_correlation(df):
    """Plot feature correlation matrix"""
    # Extract features
    features_df = pd.json_normalize(df['features'])
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    corr = features_df.corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    
    sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='coolwarm',
                center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax)
    
    ax.set_title('Feature Correlation Matrix', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('ml_metrics_feature_correlation.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: ml_metrics_feature_correlation.png")
    plt.show()

def plot_model_performance(df):
    """Plot model performance metrics"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    # Confidence distribution
    ax1.hist(df['confidence'], bins=20, color='lightgreen', edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Confidence', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('Model Confidence Distribution', fontsize=12, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    # Score vs Confidence scatter
    severity_colors = {'critical': 'red', 'high': 'orange', 'medium': 'yellow', 'low': 'blue'}
    for severity, color in severity_colors.items():
        mask = df['severity'] == severity
        ax2.scatter(df[mask]['anomaly_score'], df[mask]['confidence'], 
                   label=severity, alpha=0.6, s=50, color=color)
    ax2.set_xlabel('Anomaly Score', fontsize=12)
    ax2.set_ylabel('Confidence', fontsize=12)
    ax2.set_title('Score vs Confidence', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Severity distribution
    severity_counts = df['severity'].value_counts()
    severity_counts.plot(kind='bar', ax=ax3, color=['red', 'orange', 'yellow', 'blue'])
    ax3.set_xlabel('Severity', fontsize=12)
    ax3.set_ylabel('Count', fontsize=12)
    ax3.set_title('Severity Distribution', fontsize=12, fontweight='bold')
    ax3.tick_params(axis='x', rotation=0)
    ax3.grid(axis='y', alpha=0.3)
    
    # Detection rate over time
    df_sorted = df.sort_values('@timestamp')
    df_sorted['hour'] = pd.to_datetime(df_sorted['@timestamp']).dt.floor('H')
    hourly_counts = df_sorted.groupby('hour').size()
    hourly_counts.plot(kind='line', ax=ax4, marker='o', color='purple')
    ax4.set_xlabel('Time', fontsize=12)
    ax4.set_ylabel('Anomalies Detected', fontsize=12)
    ax4.set_title('Detection Rate Over Time', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig('ml_metrics_model_performance.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: ml_metrics_model_performance.png")
    plt.show()

def generate_summary_report(df):
    """Generate text summary report"""
    report = f"""
╔═══════════════════════════════════════════════════════╗
║     ML ANOMALY DETECTION - SUMMARY REPORT             ║
╚═══════════════════════════════════════════════════════╝

📊 OVERALL STATISTICS
{'─' * 55}
Total Anomalies Detected:        {len(df)}
Time Range:                       Last 24 hours
Average Anomaly Score:            {df['anomaly_score'].mean():.2f}
Max Anomaly Score:                {df['anomaly_score'].max():.2f}
Min Anomaly Score:                {df['anomaly_score'].min():.2f}
Std Deviation:                    {df['anomaly_score'].std():.2f}

🎯 ANOMALY TYPES
{'─' * 55}
{df['anomaly_type'].value_counts().to_string()}

⚠️  SEVERITY BREAKDOWN
{'─' * 55}
{df['severity'].value_counts().to_string()}

📈 MODEL PERFORMANCE
{'─' * 55}
Average Confidence:               {df['confidence'].mean():.4f}
High Score Anomalies (>70):       {len(df[df['anomaly_score'] > 70])}
Critical Severity Count:          {len(df[df['severity'] == 'critical'])}

🔝 TOP 5 HIGHEST SCORES
{'─' * 55}
"""
    
    top_5 = df.nlargest(5, 'anomaly_score')[['@timestamp', 'anomaly_type', 'anomaly_score', 'severity']]
    for idx, row in top_5.iterrows():
        report += f"{row['@timestamp'][:19]} | {row['anomaly_type']:20s} | Score: {row['anomaly_score']:6.2f} | {row['severity']}\n"
    
    report += "\n" + "═" * 57 + "\n"
    
    print(report)
    
    with open('ml_metrics_report.txt', 'w') as f:
        f.write(report)
    print("✅ Saved: ml_metrics_report.txt")

def main():
    """Main execution"""
    print("🤖 ML Model Metrics Visualization")
    print("=" * 60)
    
    # Fetch data
    print("\n📥 Fetching anomalies from Elasticsearch...")
    df = fetch_anomalies(hours=24, size=1000)
    
    if len(df) == 0:
        print("❌ No anomalies found in the last 24 hours")
        return
    
    print(f"✅ Fetched {len(df)} anomalies\n")
    
    # Generate visualizations
    print("📊 Generating visualizations...\n")
    
    plot_score_timeline(df)
    plot_type_distribution(df)
    plot_severity_heatmap(df)
    plot_score_distribution(df)
    plot_feature_correlation(df)
    plot_model_performance(df)
    
    # Generate report
    print("\n📝 Generating summary report...\n")
    generate_summary_report(df)
    
    print("\n✅ All visualizations completed!")
    print("📁 Files saved in current directory")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
