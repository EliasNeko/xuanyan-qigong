# 从豆包回复里取答案。
# 回复长得像：
#   「…题目：从雷诺阿的《包厢》… A. 色彩 B. 光线 C. 空间 D. 线条 今天 22:11 答案 = B 免费 …」
# 坑一：提问本身被回显在页面上，前面也会出现「答案」字样的选项长文本；
# 坑二：页面尾部还有「展开全部」「推荐问题」，会把它们当答案；
# 坑三：模型有时回「答案是 B」有时「答案：B」有时「答案=B」。

import re

PAT_STRICT = re.compile(r"答案\s*[:：=＝]\s*([A-Ja-j]{1,6})(?![a-zA-Z])")
PAT_LOOSE = re.compile(r"(?:答案|正确的是|应选|选择)\s*[:：是为]*\s*([A-Ja-j]{1,6})(?![a-zA-Z])")


def parse_letters(answer_text, option_count):
    """返回选项下标列表，比如 [1] 表示 B。取最后一处「答案=」，因为前面那处是回显。"""
    found = PAT_STRICT.findall(answer_text) or PAT_LOOSE.findall(answer_text)
    if not found:
        return []
    letters = found[-1].upper()
    idx = []
    for ch in letters:
        i = ord(ch) - ord("A")
        if 0 <= i < option_count:
            idx.append(i)
    return sorted(set(idx))


def parse_judge(answer_text):
    """判断题：先说「先讲依据」的那句话，再单独一行给结论，所以优先匹配结论词。"""
    m = re.search(r"答案\s*[:：=＝]?\s*(.{0,6})", answer_text)
    if not m:
        return ""
    seg = m.group(1)
    if re.search(r"不正确|不对|错误|^错", seg):
        return "错"
    if re.search(r"正确|^对|^是|√", seg):
        return "对"
    return ""       # 判不出来就退回字母解析
