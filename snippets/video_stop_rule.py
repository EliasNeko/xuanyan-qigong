# 视频达标判定：91% 先问一次，96% 再问一轮，都没认才播到尾。
# 节选：watch() 主循环里的一段（省略了弹题、保活、日志格式）。

STOP_PCT = 91.0                       # 配置项 playback.stop_percent
MARKS = [STOP_PCT, min(97.0, STOP_PCT + 5.0)]   # 91% -> 96%


def _video_done(page):
    """问系统：这个视频任务点算完成了吗？

    两种信号：
      1. 任务点图标外层有没有 ans-job-finished（快、准）；
      2. 页面里 #_studystate 的 unfinishCount 有没有变小（兜底，常常读不到）。
    读不到任何信号时一律按「没完成」处理，宁可多播几十秒也不早退。
    """
    point = pick_video_point(read_task_points(page))
    if point is None:
        return False
    if point["finished"]:
        return True
    state = fresh_unfinish_count(page)      # 可能返回 None
    if state is None:
        return False                        # 读不到就别下结论
    return state[0] < state[1]              # 现在 < 开播前


def check_marks(page, t, d, hits):
    """t / d 是当前播放秒数与总时长；hits 记录已经问过几个百分点。"""
    if d <= 5 or t <= 0:
        return None
    pct = t / d * 100.0
    if hits >= len(MARKS) or pct < MARKS[hits]:
        return None
    for _ in range(3):                      # 服务端记账有延迟，连续问 3 次
        if _video_done(page):
            return ("done", pct)
        page.wait_for_timeout(6000)
    hits += 1
    return ("retry", pct)                   # 到 96% 会再进这里一次
