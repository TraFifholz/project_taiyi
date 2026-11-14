"""生成主角团 NAI 重绘请求。配方沿用 NPC 正式 run（同一 base caption、负面词与参数），只换人物块。
用法：python -I prepare-pc-runs.py <版本后缀> [slug ...]   写 runs/<日期>-pc-<slug>-<版本>/request.json
Danbooru MCP 不在本环境，标签未过 verified-tags，meta.designStatus 如实记录。人物外观取自旧 tokenizer 头像与 2026-09 群像提示词。"""
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
TEMPLATE = RUNS / "20261029-ls-npc-n4-v1/request.json"
DATE = "20261106"

COMMON_NEGATIVE = "sunglasses, crown, hat, helmet"

PCS = {
    "lihao": {
        "name": "李好",
        "assumptions": ["用户 2026-11-06 指定：普通银行职员服，墨镜换眼镜", "保留旧头像的肥胖球形剪影、圆脸与绿色挂绳工牌，去掉财神 cos 服"],
        "unblock": ["badge", "name tag", "id card"],
        "negative": "sunglasses, crown, hat, red clothes, gold, chinese clothes, jacket, muscular, slim, skinny, thin, tall, slender",
        "prompt": "1boy, solo, male focus, solo focus, adult, fat, fat man, obese, plump, double chin, thick neck, wide body, big belly, round face, chubby cheeks, black hair, short hair, side part, black eyes, glasses, black-framed eyewear, rectangular eyewear, gentle smile, looking at viewer, white shirt, collared shirt, long sleeves, navy necktie, black pants, belt, lanyard, green lanyard, id card, holding folder, standing, transparent background. A very fat, short, wide Chinese bank clerk in his late twenties with a round silhouette nearly as wide as he is tall, a thick neck melting into a double chin, heavy round cheeks and a huge belly straining his shirt, in a plain office uniform: white dress shirt, dark tie, black trousers, black-framed glasses, a green lanyard with a blank white staff badge, ordinary and slightly tired but kind.",
    },
    "yuko": {
        "name": "黑崎欲子",
        "assumptions": ["旧头像：银灰层次中长发、发尾淡粉、圆框眼镜、灰眼、黑衬衫黄领带、卡其工装背带裤"],
        "unblock": [],
        "negative": "sunglasses, crown, hat, smile, open mouth",
        "prompt": "1girl, solo, solo focus, adult, medium hair, layered hair, grey hair, gradient hair, pink hair tips, sidelocks, grey eyes, round eyewear, black-framed eyewear, glasses, expressionless, half-closed eyes, looking at viewer, black shirt, collared shirt, sleeves rolled up, yellow necktie, brown overalls, overall skirt pocket, work clothes, hand in pocket, standing, transparent background. A calm, dry-humoured street driver with shoulder-length ash-silver hair fading to faint pink, large round wire glasses, a black work shirt with rolled sleeves, a mustard tie and worn khaki bib overalls.",
    },
    "tangsuo": {
        "name": "唐索",
        "assumptions": ["旧头像：黑色短乱发、琥珀眼、黑灰机能兜帽外套、红色系带、右侧金属爪手套"],
        "unblock": [],
        "negative": "sunglasses, crown, long hair, smile",
        "prompt": "1girl, solo, solo focus, short hair, black hair, messy hair, hair between eyes, amber eyes, yellow eyes, serious, looking at viewer, techwear, black jacket, hooded jacket, open jacket, grey hoodie, grey shirt, harness, straps, red cord, red tassel, black pants, black gloves, mechanical hand, metal claws, one hand raised to neck, standing, transparent background. A compact young street brawler with a short messy black bob and amber eyes, in an oversized black and grey techwear hooded jacket with harness straps and a hanging red cord tassel, one hand in a steel clawed gauntlet.",
    },
    "leiwulong": {
        "name": "雷武龙",
        "assumptions": ["旧头像：黑发低马尾红绳、红棕眼、青绿立领盘扣练功服、橙色腰带、红裤"],
        "unblock": [],
        "negative": "sunglasses, crown, hat, muscular, topless",
        "prompt": "1boy, solo, male focus, solo focus, young man, lean, black hair, long hair, low ponytail, red hair tie, long bangs, sidelocks, red eyes, slight smile, looking at viewer, green jacket, chinese clothes, tangzhuang, mandarin collar, frog button, patterned sleeves, white trim, orange sash, red pants, fist in palm, standing, transparent background. A lean university martial artist with a black low ponytail tied by a red cord and reddish-brown eyes, in a dark teal-green Chinese martial jacket with red frog fasteners and white cuffs, an orange sash and red trousers, proud and a little dreamy.",
    },
    "kevlar": {
        "name": "凯芙拉·威尔森",
        "assumptions": ["旧头像：水青色大波浪高马尾、黑色机械发带、琥珀眼、白色和风罩衫配青黑机能装备、工具腰带"],
        "unblock": [],
        "negative": "sunglasses, crown, hat",
        "prompt": "1girl, solo, solo focus, long hair, wavy hair, aqua hair, high ponytail, ahoge, black hairband, mechanical hair ornament, amber eyes, orange eyes, light smile, looking at viewer, white kimono, open coat, teal trim, black harness, techwear, black gloves, fingerless gloves, tool belt, wrench, holding smartphone, standing, transparent background. A cheerful engineering student with voluminous wavy aqua hair in a high ponytail held by a black mechanical hairband and amber eyes, wearing a white kimono-style overcoat with teal and black technical harness, and a tool belt full of wrenches.",
    },
    "arkan": {
        "name": "阿尔坎·希耶尔",
        "assumptions": ["用户 2026-11-06 指定：关键是义体下巴", "旧头像：沙金发齐刘海、深蓝蝴蝶结低扎、金眼、虹彩外套、黄色背心、牛仔短裤、手机"],
        "unblock": [],
        "negative": "sunglasses, crown, hat, face mask, mouth mask, surgical mask, covered mouth, bandaid, mechanical hands, mechanical arms, prosthetic arm, robot hands, respirator, gas mask",
        "prompt": "1girl, solo, solo focus, blonde hair, ash blonde hair, medium hair, blunt bangs, low twintails, hair bow, dark blue bow, yellow eyes, metal jaw, prosthetic jaw, steel chin, looking at viewer, iridescent jacket, white jacket, open jacket, oversized jacket, yellow tank top, denim shorts, holding smartphone, standing, transparent background. Her entire lower jaw and chin are an exposed grey steel cybernetic prosthesis with panel seams and a visible hinge just under each ear, the metal replacing the skin of the lower face and forming her mouth, set flush into her cheeks, while her nose, cheeks, upper face, neck and both ordinary human hands remain natural skin.",
    },
}


def main():
    version = sys.argv[1]
    slugs = sys.argv[2:] or list(PCS)
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    for slug in slugs:
        pc = PCS[slug]
        doc = json.loads(json.dumps(template))
        run_id = f"{DATE}-pc-{slug}-{version}"
        meta, params = doc["meta"], doc["payload"]["parameters"]
        seed = random.randrange(1, 2**32 - 1)
        meta.update(runId=run_id, characterId=f"LS-PC-{slug}", characterName=pc["name"], promptVersion=1,
                    designStatus="pc-redraw-20261106; tags not MCP-verified", designAssumptions=pc["assumptions"],
                    humanInitiated=True, humanInitiatedAt=datetime.now(timezone.utc).isoformat())
        params["seed"] = seed
        caption = params["v4_prompt"]["caption"]["char_captions"][0]
        caption["char_caption"] = pc["prompt"]
        negative = params["negative_prompt"]
        for tag in pc["unblock"]:
            negative = negative.replace(f", {tag}", "")
        negative = f"{negative}, {pc['negative']}"
        params["negative_prompt"] = negative
        params["v4_negative_prompt"]["caption"]["base_caption"] = negative
        run = RUNS / run_id
        run.mkdir(exist_ok=True)
        (run / "request.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(run_id, seed)


if __name__ == "__main__":
    main()
