# SmartInvestor/AI_Sentiment_Engine.py
from transformers import pipeline
import torch

class InstitutionalSentiment:
    def __init__(self):
        print("⚡ 初始化机构级情感引擎 (Loading FinBERT)...")
        # 使用 ProsusAI 的 FinBERT，这是金融界目前的开源标杆
        self.device = 0 if torch.cuda.is_available() else -1
        self.pipe = pipeline("text-classification", model="ProsusAI/finbert", device=self.device)

    def analyze_text(self, text):
        """
        输入一段文本（推文/新闻），返回：
        1. 情感标签 (positive, negative, neutral)
        2. 确信度分数 (0-1)
        3. 机构评分 (-1 到 1, 用于量化模型)
        """
        try:
            # FinBERT 接受的 token 有限，截取前 512 字符通常够了
            result = self.pipe(text[:512])[0]
            label = result['label']
            score = result['score']

            # 将标签转化为量化分数 (-1: 极度看空, 1: 极度看多)
            quant_score = 0
            if label == 'positive':
                quant_score = score
            elif label == 'negative':
                quant_score = -score
            
            return {
                "label": label,
                "confidence": round(score, 4),
                "quant_score": round(quant_score, 4)  # 这是一个 Alpha 因子
            }
        except Exception as e:
            print(f"NLP Error: {e}")
            return None

# --- 单元测试 ---
if __name__ == "__main__":
    ai = InstitutionalSentiment()
    # 测试一句很难的话（反讽/暗语）
    # NLTK 可能会因为 'low' 判负，但 FinBERT 知道 'inflation lower' 是好事
    text = "The CEO has resigned amid a major fraud investigation." 
    print(ai.analyze_text(text))