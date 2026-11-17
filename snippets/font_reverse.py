# 字体加密还原。
# 页面上挂着好几个 @font-face，只有 font-cxsecret（data:base64 的 ttf）是真的加密字体，
# 其它（icomoon / marking / din / 兰亭黑）解出来全是「冂」「口」这种垃圾 —— 所以要挑。

from fontTools.ttLib import TTFont


def cmap_codes(ttf_bytes):
    """这份字体「认领」了哪些码位（= 哪些字被劫持了）。"""
    import io
    font = TTFont(io.BytesIO(ttf_bytes))
    codes = set()
    for table in font["cmap"].tables:
        codes.update(table.cmap.keys())
    return codes


def decode(text, ttf_bytes, glyph_to_char):
    """只还原字体认领过的字；没被认领的原样保留。"""
    codes = cmap_codes(ttf_bytes)
    out = []
    for ch in text:
        if ord(ch) not in codes:
            out.append(ch)          # 没劫持 —— 硬凑会变成「冈」这种错字
            continue
        out.append(glyph_to_char.get(ch, ch))
    return "".join(out)


def choose_font(candidates, question_text):
    """从多个 @font-face 里挑真的那个。

    排序键：(family 名里有没有 secret, 命中题面汉字的个数, cmap 大小)
    —— 命中数是最硬的证据：能认出题面里 20 个字的字体，才是加密字体。
    """
    scored = []
    for cand in candidates:
        try:
            codes = cmap_codes(cand.ttf)
        except Exception:
            continue
        hits = sum(1 for ch in question_text if ord(ch) in codes)
        family = (cand.family or "").lower()
        secret = 1 if ("cxsecret" in family or "secret" in family) else 0
        scored.append((secret, hits, len(codes), cand))
    if not scored:
        return None
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    best = scored[0]
    return best[3] if best[1] > 0 else None      # 一个题面字都认不出就别用
