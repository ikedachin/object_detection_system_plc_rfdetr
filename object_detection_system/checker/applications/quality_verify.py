from typing import Dict, Any

##################################################################
###################### 判定ロジックライブラリ ######################
##################################################################

def quality_verify_common(result_dict):
    if len(result_dict) == 0:
        return False
    else:
        return True


# thr17の判定ロジック
# result_dictは{'s': 8}のような形式で、keyは's'または'c'、valueは整数
# 's'の場合は8が合格、'c'の場合は9が合格
# それ以外は不合格
def quality_verify_thr17(result_dict):

    if len(result_dict) == 1:
        key, value = list(result_dict.items())[0]
        if key == "s":
            if value == 8:
                return True
            else:
                return False
        else:
            if value == 9:
                return True
            else:
                return False
    else:
        return False
