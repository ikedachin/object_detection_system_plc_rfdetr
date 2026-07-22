from typing import Dict, Any

##################################################################
###################### 判定ロジックライブラリ ######################
##################################################################

def quality_verify_common(result_dict):
    if len(result_dict) == 0:
        return False
    else:
        return True


# 判定ロジック
# result_dictは{'s': 8}のような形式で、keyはラベル名、valueは検出個数
# 検出されたラベル（key）の種類が1種類だけであれば合格
# 必要であれば、アノテーションの時につけたラベルを用いて、そのラベルのものが何個あるかで合否判定させることも可能です。
# 例：`book == 10`など
# 0種類（未検出）または2種類以上は不合格
def quality_verify(result_dict):
    if len(result_dict) == 1:
        return True
    else:
        return False



# =================================================================
# 判定ロジック例
# =================================================================
# book == 6の時に合格
def quality_verify_book(result_dict):
    if len(result_dict) != 1:
        return False
    label_name, count = list(result_dict.items())[0]
    return label_name == 'book' and count == 6


# 代表的な判定ロジック例
# ラベル「l」または「r」: 8個以上で合格
# その他のラベル: 9個以上で合格
# 未検出または複数種類検出時は不合格
def quality_verify_book_pen(result_dict: Dict[str, Any]) -> bool:
    if len(result_dict) != 1:
        return False

    label_name, count = list(result_dict.items())[0]
    threshold = 8 if label_name in {'book', 'pen'} else 9
    return count >= threshold