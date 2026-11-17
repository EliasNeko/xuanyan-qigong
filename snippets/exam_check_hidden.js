// 章节测验提交前自检。
// 新版学习通的选项不是 radio：
//   <li qid="211740917" onclick="addChoice(this);"><label><span data="B">B</span></label><a>光线</a></li>
//   <input type="hidden" name="answer211740917" value="">
// 点中选项的后果是：hidden 的 value 被写成 "B"（判断题写 "true"），选项 span 多一个 check_answer 类。
// 所以「选上没有」只能看 hidden，不能看 :checked。
function checkFilled(doc) {
  var filled = {};
  var inputs = doc.querySelectorAll("input[type=hidden][name^=answer]");
  for (var i = 0; i < inputs.length; i++) {
    var qid = inputs[i].name.slice("answer".length);
    var v = (inputs[i].value || "").trim();
    if (v) filled[qid] = v;
  }

  // 题目顺序 -> qid（按 li[qid] 出现顺序去重）
  var order = [];
  var seen = {};
  var lis = doc.querySelectorAll("li[qid]");
  for (var j = 0; j < lis.length; j++) {
    var q = lis[j].getAttribute("qid");
    if (q && !seen[q]) { seen[q] = 1; order.push(q); }
  }

  var miss = [];
  for (var k = 0; k < order.length; k++) {
    if (!filled[order[k]]) miss.push(k + 1);   // 第几题没选上（1 起）
  }

  return {
    total: order.length,
    filled: filled,
    missing: miss,             // 空数组 = 全部选上，可以提交
  };
}

// 提交前的三道闸：
// 1) missing 非空        -> 不交（有题没选上，交上去就是丢分）
// 2) 一题都没答上        -> 不交（0 分是永久记录）
// 3) 蒙的题 > 50%        -> 不交（留着下次再答）
