"""
ML Model Precision Evaluation Tool
Provides comprehensive metrics and evaluation for anomaly detection model
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import precision_recall_curve, roc_curve, auc, confusion_matrix

ES_HOST = "http://localhost:9200"
ML_INDEX = "firefox-ml-anomalies-*"

class ModelEvaluator:
    """Evaluate ML model precision and performance"""
    
    def __init__(self):
        self.es_host = ES_HOST
        self.ml_index = ML_INDEX
    
    def fetch_verified_anomalies(self, days=7):
        """Fetch anomalies with verification labels"""
        query = {
            "size": 10000,
            "query": {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": f"now-{days}d"}}},
                        {"exists": {"field": "is_verified"}}
                    ]
                }
            }
        }
        
        response = requests.post(f"{self.es_host}/{self.ml_index}/_search", json=query)
        data = response.json()
        
        anomalies = []
        for hit in data['hits']['hits']:
            src = hit['_source']
            anomalies.append({
                'timestamp': src['@timestamp'],
                'score': src['anomaly_score'],
                'raw_score': src.get('raw_score', src['anomaly_score'] / 100),
                'type': src['anomaly_type'],
                'severity': src['severity'],
                'is_true_positive': src.get('is_true_positive', False),
                'is_verified': src.get('is_verified', False)
            })
        
        return pd.DataFrame(anomalies)
    
    def calculate_metrics(self, df):
        """Calculate comprehensive performance metrics"""
        if len(df) == 0:
            print("⚠️  No verified data available")
            return {}
        
        y_true = df['is_true_positive'].astype(int)
        y_scores = df['score']
        
        # Basic metrics
        tp = sum((df['is_true_positive'] == True))
        fp = sum((df['is_true_positive'] == False))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        
        metrics = {
            'total_verified': len(df),
            'true_positives': int(tp),
            'false_positives': int(fp),
            'precision': round(precision, 4),
            'false_positive_rate': round(fp / (fp + tp), 4) if (fp + tp) > 0 else 0,
            'avg_tp_score': round(df[df['is_true_positive'] == True]['score'].mean(), 2) if tp > 0 else 0,
            'avg_fp_score': round(df[df['is_true_positive'] == False]['score'].mean(), 2) if fp > 0 else 0
        }
        
        return metrics
    
    def plot_precision_metrics(self, df):
        """Plot comprehensive precision visualizations"""
        if len(df) == 0:
            print("⚠️  No data to plot")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. Score distribution by label
        tp_scores = df[df['is_true_positive'] == True]['score']
        fp_scores = df[df['is_true_positive'] == False]['score']
        
        ax1.hist(tp_scores, bins=20, alpha=0.7, label='True Positives', color='green')
        ax1.hist(fp_scores, bins=20, alpha=0.7, label='False Positives', color='red')
        ax1.set_xlabel('Anomaly Score')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Score Distribution: True vs False Positives')
        ax1.legend()
        ax1.grid(alpha=0.3)
        
        # 2. Precision by score threshold
        thresholds = np.linspace(df['score'].min(), df['score'].max(), 50)
        precisions = []
        counts = []
        
        for thresh in thresholds:
            subset = df[df['score'] >= thresh]
            if len(subset) > 0:
                tp = sum(subset['is_true_positive'] == True)
                precision = tp / len(subset)
                precisions.append(precision)
                counts.append(len(subset))
            else:
                precisions.append(0)
                counts.append(0)
        
        ax2.plot(thresholds, precisions, marker='o', color='blue')
        ax2.axhline(y=0.85, color='r', linestyle='--', label='Target Precision (85%)')
        ax2.set_xlabel('Score Threshold')
        ax2.set_ylabel('Precision')
        ax2.set_title('Precision vs Score Threshold')
        ax2.legend()
        ax2.grid(alpha=0.3)
        
        # 3. Anomaly type accuracy
        type_accuracy = df.groupby('type').agg({
            'is_true_positive': ['sum', 'count']
        })
        type_accuracy.columns = ['tp', 'total']
        type_accuracy['precision'] = type_accuracy['tp'] / type_accuracy['total']
        
        type_accuracy['precision'].plot(kind='barh', ax=ax3, color='skyblue')
        ax3.set_xlabel('Precision')
        ax3.set_ylabel('Anomaly Type')
        ax3.set_title('Precision by Anomaly Type')
        ax3.grid(axis='x', alpha=0.3)
        
        # 4. Confusion matrix style
        labels = ['False Positive', 'True Positive']
        cm = [[sum(df['is_true_positive'] == False), 0],
              [0, sum(df['is_true_positive'] == True)]]
        
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=labels, yticklabels=labels, ax=ax4)
        ax4.set_title('Detection Results')
        ax4.set_ylabel('Actual')
        ax4.set_xlabel('Predicted')
        
        plt.tight_layout()
        plt.savefig('ml_precision_evaluation.png', dpi=300, bbox_inches='tight')
        print("✅ Saved: ml_precision_evaluation.png")
        plt.show()
    
    def generate_precision_report(self, df, metrics):
        """Generate detailed precision report"""
        report = f"""
╔════════════════════════════════════════════════════════╗
║         ML MODEL PRECISION EVALUATION REPORT           ║
╚════════════════════════════════════════════════════════╝

📊 OVERALL METRICS
{'─' * 56}
Total Verified Anomalies:       {metrics['total_verified']}
True Positives:                  {metrics['true_positives']} ({metrics['true_positives']/metrics['total_verified']*100:.1f}%)
False Positives:                 {metrics['false_positives']} ({metrics['false_positives']/metrics['total_verified']*100:.1f}%)

🎯 PERFORMANCE SCORES
{'─' * 56}
Precision:                       {metrics['precision']:.2%}
False Positive Rate:             {metrics['false_positive_rate']:.2%}

Target Precision:                85%
Status:                          {'✅ MET' if metrics['precision'] >= 0.85 else '❌ BELOW TARGET'}

📈 SCORE ANALYSIS
{'─' * 56}
Avg True Positive Score:         {metrics['avg_tp_score']:.2f}
Avg False Positive Score:        {metrics['avg_fp_score']:.2f}
Score Separation:                {abs(metrics['avg_tp_score'] - metrics['avg_fp_score']):.2f} points

🔍 BREAKDOWN BY TYPE
{'─' * 56}
"""
        
        if len(df) > 0:
            type_stats = df.groupby('type').agg({
                'is_true_positive': ['sum', 'count', 'mean']
            }).round(3)
            
            for idx, row in type_stats.iterrows():
                report += f"{idx:25s} | TP: {int(row['is_true_positive']['sum']):3d} / {int(row['is_true_positive']['count']):3d} | Precision: {row['is_true_positive']['mean']:.1%}\n"
        
        report += "\n" + "═" * 58 + "\n"
        
        # Recommendations
        report += "\n💡 RECOMMENDATIONS\n" + "─" * 56 + "\n"
        
        if metrics['precision'] < 0.85:
            report += "❗ Increase anomaly score threshold to reduce false positives\n"
            report += f"❗ Current FPR: {metrics['false_positive_rate']:.1%} - Target: <5%\n"
        
        if metrics['avg_fp_score'] > 60:
            report += "⚠️  High false positive scores detected\n"
            report += "   Consider additional feature engineering\n"
        
        if metrics['precision'] >= 0.85:
            report += "✅ Model meets precision target\n"
            report += "✅ Consider deploying to production\n"
        
        print(report)
        
        with open('ml_precision_report.txt', 'w') as f:
            f.write(report)
        print("\n✅ Saved: ml_precision_report.txt")
    
    def suggest_optimal_threshold(self, df):
        """Suggest optimal score threshold"""
        print("\n🎯 OPTIMAL THRESHOLD ANALYSIS\n" + "─" * 56)
        
        thresholds = np.linspace(df['score'].min(), df['score'].max(), 100)
        
        for target_precision in [0.90, 0.85, 0.80]:
            for thresh in thresholds:
                subset = df[df['score'] >= thresh]
                if len(subset) > 0:
                    tp = sum(subset['is_true_positive'] == True)
                    precision = tp / len(subset)
                    
                    if precision >= target_precision:
                        print(f"For {target_precision:.0%} precision:")
                        print(f"  Threshold: {thresh:.2f}")
                        print(f"  Detections: {len(subset)}")
                        print(f"  Actual Precision: {precision:.2%}\n")
                        break
    
    def run_evaluation(self):
        """Run complete evaluation"""
        print("🔍 ML Model Precision Evaluation\n" + "═" * 56)
        
        # Fetch data
        print("\n📥 Fetching verified anomalies...")
        df = self.fetch_verified_anomalies(days=7)
        
        if len(df) == 0:
            print("\n❌ No verified anomalies found.")
            print("💡 Use the feedback system to mark anomalies as true/false positives")
            return
        
        print(f"✅ Found {len(df)} verified anomalies\n")
        
        # Calculate metrics
        metrics = self.calculate_metrics(df)
        
        # Generate report
        self.generate_precision_report(df, metrics)
        
        # Plot visualizations
        print("\n📊 Generating visualizations...")
        self.plot_precision_metrics(df)
        
        # Suggest thresholds
        self.suggest_optimal_threshold(df)
        
        print("\n✅ Evaluation complete!")

if __name__ == '__main__':
    evaluator = ModelEvaluator()
    evaluator.run_evaluation()
