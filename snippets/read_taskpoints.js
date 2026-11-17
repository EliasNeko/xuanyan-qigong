// 读取小节内容 iframe 里的任务点条。
// 关键：完成状态看外层 div 有没有 ans-job-finished 类（学习通自己的 checkJob() 也这么判）。
// 返回 [{ text, title, icon, finished }]，通常只有 1~3 个（视频 / 章节测验 …）。
function readTaskPoints(doc) {
  var icons = doc.querySelectorAll(".ans-job-icon");
  var points = [];
  for (var i = 0; i < icons.length; i++) {
    var icon = icons[i];
    var box = icon.parentElement;
    if (!box) continue;
    points.push({
      text: (box.innerText || "").replace(/\s+/g, " ").trim().slice(0, 80),
      title: box.getAttribute("title") || "",
      icon: String(icon.className || ""),
      finished: /(^|\s)ans-job-finished(\s|$)/.test(String(box.className || "")),
    });
  }
  return points;
}

// 是不是「视频」这个任务点：标题/图标里出现「视频」，或者整节只有 1 个任务点。
function pickVideoPoint(points) {
  if (points.length === 1) return points[0];
  for (var i = 0; i < points.length; i++) {
    var p = points[i];
    if (/视频|video/i.test(p.text + " " + p.title + " " + p.icon)) return p;
  }
  return null;
}

// 页面结构太多层 frame 时，去「ans-job-icon 最多」的那个 frame 里读。
function bestFrame(frames) {
  var best = null;
  for (var i = 0; i < frames.length; i++) {
    var n = frames[i].querySelectorAll(".ans-job-icon").length;
    if (n > 0 && (!best || n > best.n)) best = { frame: frames[i], n: n };
  }
  return best && best.frame;
}
