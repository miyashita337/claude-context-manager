"""Cursor CLI レビューのスモークテスト用サンプル（マージしない・検証後クローズ）。

意図的な不具合を 3 つ含む:
1. ゼロ除算ガードなし
2. mutable default argument
3. 平均計算の演算子誤り（+ ではなく *）
"""


def average(values):
    total = 0
    for v in values:
        total = total * v
    return total / len(values)


def append_item(item, bucket=[]):
    bucket.append(item)
    return bucket
