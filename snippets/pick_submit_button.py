# 弹题「提交」按钮的选择器打分选优。
# 起因：容器 .tkTopic_oper 的 innerText 也是「提交」（其它按钮被 CSS 藏着），
#       按文档序取第一个「提交」会点到容器 -> 等于没点 -> 每 1.3 秒重交一次 -> 视频永远不动。

SUBMIT_WORDS = ("提交", "确定", "submit")
CONTAINER_HINT = ("提交", "继续", "回答正确", "回答错误")   # 容器里会同时出现这些


def _score(el):
    """给候选元素打分；<0 直接淘汰。"""
    tag = (el.tag_name or "").lower()
    cls = (el.get_attribute("class") or "").lower()
    eid = (el.get_attribute("id") or "").lower()
    text = (el.inner_text() or "").strip()

    if tag not in ("a", "button", "input"):
        # div / span 只有当它真的带点击行为时才算按钮
        if not (el.get_attribute("onclick") or "btn" in cls or "submit" in cls):
            return -1
        score = 0
    else:
        score = 10

    if any(w in text for w in SUBMIT_WORDS):
        score += 6
    if "submit" in cls or "submit" in eid or "提交" in text:
        score += 4
    if el.get_attribute("onclick"):
        score += 2

    # 后代里还有别的按钮文字 = 这是容器，不是按钮
    kids = el.query_selector_all("a, button")
    if len(kids) >= 2:
        return -1
    return score


def pick_submit(frame):
    best, best_score = None, 0
    for el in frame.query_selector_all("a, button, input, div, span"):
        s = _score(el)
        if s > best_score:
            best, best_score = el, s
    return best
