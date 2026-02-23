"""
Priority Configuration - Single Source of Truth

優先度の定義をここで一元管理します。
GitHub Labels・Claude プロンプト・Projects Priority が全てここから生成されます。

変更・追加方法:
  1. PRIORITIES リストを編集する
  2. `make sync-labels` を実行して GitHub Labels を同期する
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Priority:
    name: str        # GitHub ラベル名 / Projects Priority 表示名
    description: str  # ラベルの説明
    color: str        # GitHub ラベルカラー (hex, # なし)
    definition: str   # Claude プロンプト用の定義文


PRIORITIES: List[Priority] = [
    Priority(
        name="Critical",
        description="Critical: 即時対応必須（障害・セキュリティ）",
        color="B60205",
        definition="本番障害・セキュリティ脆弱性・データ損失など即時対応必須",
    ),
    Priority(
        name="High",
        description="High: 主要機能の不具合・リリースブロッカー",
        color="D93F0B",
        definition="主要機能の不具合・リリースブロッカー（数日以内）",
    ),
    Priority(
        name="Medium",
        description="Medium: 軽微な不具合・機能改善",
        color="E4E669",
        definition="軽微な不具合・機能改善（次スプリント）",
    ),
    Priority(
        name="Low",
        description="Low: nice-to-have・将来検討",
        color="CFD3D7",
        definition="nice-to-have・将来検討",
    ),
]

# 便利なショートカット（他スクリプトから import して使う）
LABEL_NAMES: List[str] = [p.name for p in PRIORITIES]
DEFAULT_PRIORITY: str = "Medium"
