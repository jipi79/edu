# 원고 작성 안내 (차시 원본 JSON)

한 차시를 만드는 순서:

```bash
python3 -I tools/plan/new_lesson.py <수업 ID>        # 계획에서 뼈대 생성(메타데이터·교육과정·선수 차시가 채워짐)
# lessons/…/<ID>.json 의 objectives·materials·boundary·misconceptions·checks·slides·worksheet 를 채운다
python3 -I .claude/skills/education-ppt/scripts/check_lesson.py <원본>   # 원고 검사
node tools/pptx/build_lesson.js <원본>               # PPTX 2벌 (글이 넘치면 실패)
tools/build.sh <원본>                                # 검사 + PPTX + 활동지·안내 PDF + 출력 검사 + 목차
```

뼈대의 `plan_objective` 는 계획의 목표 문장이다. 이를 관찰 가능한 목표 1~3개로 구체화한다.
`id`, `title`, `grade`, `unit_folder`, `sequence`, `file_stem`, `curriculum`, `prerequisites[].lesson` 은 고치지 않는다(계획과 다르면 검사가 실패한다).

## 차시의 기본 형태

**설명형(`format: ppt`)** 10~14장

| 장 | kind | role | 하는 일 |
|---|---|---|---|
| 1 | cover | intro | 오늘의 질문, 할 수 있게 될 것(goals) |
| 2 | choice / practice | prior | 선수 학습 확인 (흔들리면 보충 장으로) |
| 3~6 | concept / steps / compare | teach | 구체물·그림 → 말 → 식·기호. 한 장에 한 가지 생각 |
| 7~9 | practice | practice | 도움 받는 연습(hint), 오개념 비교(compare) |
| 10 | check | check | 혼자 하기 (학생용에도 남음) |
| 11 | answers (teacher_only) | feedback | 정답 예와 흔한 실수 |
| 12 | check / choice | check | 처음 보는 문제로 마무리 확인 |
| 13 | summary | review | 핵심 한 문장, ○/×, 다음 수업 첫 5분 복습 3문제, 다음 차시 |
| 14 | concept/practice + `layout: support` | support | 보충(필요할 때만), 마지막 절 "보충" |

**활동형(`format: act`)** 6~8장: cover → (prior) → concept(무엇을 왜) → activity(단계·안전·관찰 기준) → check(돌아보기 질문) → summary.
화면은 짧게, 실제 활동은 화면 밖에서 한다. 활동지는 관찰 기준표·실천 기록표로 만든다.

절(section) 이름: 도입 · 개념 · 연습 · 확인 · 정리 · 보충. 장 ID는 S01부터 차례로.

## 장의 공통 필드

```json
{ "id": "S03", "kind": "concept", "section": "개념", "purpose": "그림으로 설명", "role": "teach",
  "objectives": ["A"], "title": "선을 더 그어도 색칠한 양은 그대로",
  "notes": { "목적": "…", "시간": "약 4분", "말하기": ["“…”"], "예상답": ["…"], "정답": ["…"], "막히면": ["…"], "주의": ["…"] } }
```

- `title`: 한 줄(초1·2는 14자, 초3·4는 18자, 초5·6은 20자 이내 권장). 마침표 없음.
- `notes.말하기` 필수. practice·check·prior 장은 `정답` 또는 `예상답` 필수. 부모가 그대로 읽을 수 있는 말투로 쓴다.
- 학생에게 보이는 장에는 "정답:" 같은 정답 표기를 쓰지 않는다. 정답은 노트, answers 장(teacher_only), 안내서에만.
- 선택: `layout`(cover·content·closing·support, 기본은 kind에 따라), `teacher_only`.
- 차시 최상위 선택 필드 `break_after`: 이틀에 나눠도 되는 지점(장 ID). 부모용 안내에 표시된다.

## 장 종류(kind)

모든 kind에서 `text`(맨 위 안내 문장), `key`(맨 아래 핵심 카드)를 쓸 수 있는 곳이 많다. 카드는 문자열 또는 `{ "title": "…", "text": "…" }`.

| kind | 필드 | 배치 |
|---|---|---|
| `cover` | `question`, `goals`[2], `figure`? | 어두운 표지. 오른쪽 위 그림(선택) |
| `concept` | `text`?, `figure`/`figures`, `points`[1~3]?, `key`? | 넓은 그림(막대·수직선·표·흐름 등)이면 그림 위 + 카드 행 아래, 그 밖엔 그림 왼쪽 + 카드 오른쪽 |
| `steps` | `text`?, `problem`?(`{text}` 또는 `{eq}`), `steps`[2~5](문자열 또는 `{text, eq}`), `figure`?, `key`? | 번호 단계 왼쪽, 그림 오른쪽 |
| `practice` / `check` | `text`?, `problems`[1~6] (`{text}`·`{eq}`·`{figure}`), `figure`?(도움 그림), `aidTitle`?, `hint`? | 3개 이하는 한 줄씩, 4~6개는 두 열. 도움 그림이 있으면 오른쪽 |
| `choice` | `text`?, `options`[2~4] (`{figure}` 또는 `{text}`), `question`? | 가·나·다·라 이름표 자동 |
| `compare` | `claim`?, `left`/`right` (`{title, figure|eq|text, text?, mark?: "o"|"x"}`), `question`? | 두 칸 비교. mark를 쓰면 ○/× 표시(정답을 보여 주는 설명 장에서만) |
| `passage` | `text`?, `passage` (`{title?, paragraphs[], numbered?}`; 문단은 문자열 또는 `{text, align: "right"}`), `question`?, `figure`? | 읽기 지문 상자. 넘치면 지문을 줄이거나 두 장으로. 편지의 날짜·서명은 오른쪽 정렬 |
| `cards` | `text`?, `cards`[2~6], `key`? | 카드 격자 |
| `table` | `text`?, `table` (`{headers, rows, widths?}`), `key`? | 표 |
| `chart` | `text`?, `chart` (`{chart: bar|line|pie, labels, values, valueTitle?, max?}`), `question`? | PowerPoint 차트 |
| `activity` | `text`?, `steps`[2~5], `criteria`[2~4]?, `criteriaTitle`?, `safety`?, `figure`? | 단계 왼쪽, 관찰 기준 체크리스트 오른쪽, 안전 문구 아래 |
| `answers` | `good`[ {eq|text, note?} ], `bad`[ … ], `explain`? | 반드시 `teacher_only: true`, `role: feedback` |
| `summary` | `key`, `do`?, `dont`?, `review`[1~3] ({text} 또는 {eq}), `next`? | 어두운 정리 장 |
| `blocks` | `blocks`[…] | 좌표를 직접 주는 방식(특수한 경우만) |

## 그림(figure)

`figure` 하나 또는 `figures` 배열(가로로 나란히, 각각 `caption` 가능).

| type | 필드 | 쓰임 |
|---|---|---|
| `bars` | `bars`[ {parts, shaded(개수 또는 칸 번호 배열), label?: [분자,분모] 또는 글자, widths?} ], `guide`? | 분수 막대. `guide: true` 이면 첫 막대의 색칠 끝에 점선(같은 양 비교) |
| `grid` | `rows`, `cols`, `shaded`(개수 또는 [[행,열]…]), `light`?([[행,열]…] 옅은 색), `axis`?: v/h | 넓이·배열·대칭. (분수)×(분수)는 첫 분수 부분을 `light`, 겹친 부분을 `shaded`로(검산 count는 shaded만 센다) |
| `pie` | `parts`, `shaded` | 원 분수 |
| `eq` | `items` (분수는 [분자,분모], 대분수는 [자연수,분자,분모], 빈칸은 null 또는 "□", 기호는 문자열) 또는 `lines`[…] | 식. 분수가 없으면 한 줄 글자 |
| `eqx` | `from`, `to`, `op`("×2"), `join`?("="·"→") | 분수 변환 화살표 |
| `numberline` | `min`, `max`, `step`?, `labels`?("all"·"ends"·[값]), `marks`?[{at,label,open?}](open: 속이 빈 ○), `jumps`?[{from,to,label}] | 수직선, 뛰어 세기 |
| `array` | `rows`, `cols`, `count`?, `group`?("row"·"col"), `crossed`?(뒤에서부터 × 표시할 개수), `cell`?(점 칸 크기, in) | 세기·곱셈·나눗셈 묶음, 덜어 내기(crossed). 양을 나란히 비교할 때는 모든 배열에 같은 `cell` 을 준다 |
| `tenframe` | `count`, `frames`? | 10의 보수, 가르기·모으기 |
| `blocks10` | `hundreds`?, `tens`, `ones`, `unit`?(한 칸 크기, in) | 자릿값(수 모형). 여러 개를 나란히 둘 때는 같은 `unit` |
| `bond` | `whole`, `parts`[2] (빈칸은 null), `merge`? | 가르기(전체 위)·모으기(merge: 부분 위) |
| `placevalue` | `headers`, `rows` | 자릿값 표 |
| `table` | `headers`, `rows`, `widths`?(열 너비 비율, 합 1), `width`?(표 전체 너비 in), `size`?(pt), `firstColHead`? | 표 |
| `clock` | `h`, `m`(시곗바늘 없이 그리려면 h 생략) | 시각 |
| `shapes` | `items`[ {shape, label?, shaded?} ] — circle·triangle·rtriangle·square·rect·pentagon·hexagon·parallelogram·trapezoid·rhombus·cube·cuboid·cylinder·sphere·cone | 평면·입체 도형 |
| `angle` | `deg`, `label`? | 각도 |
| `geo` | `points`{이름:[x,y]} (y는 위가 +, `_`로 시작하는 이름은 표시 안 함), `polygons`[ {pts, fill?(tint·accent·good·info·yellow·none), dash?, open?, sides?[ {label?, ticks?} 또는 null — 변 순서 pts[i]→pts[i+1]] } ], `segments`[ {from, to, extend?(end·start·both: 반직선·직선), arrow?, dash?, label?, ticks?} ], `circles`[ {center, r, fill?} ], `angles`[ {at, from, to, label?} ], `rights`[[A,B,C]](B에 직각 표시), `dots`?(true·[이름]), `texts`[ {at, text} ], `grid`?("square" 모눈·"dot" 점판), `grid_margin`?(정수, 기본 1칸), `name_dir`?{이름: up·down·left·right·ul·ur·dl·dr}, `names`?(false면 점 이름 숨김), `ws_unit`?(활동지 1칸 mm, 기본 10) | 선분·반직선·직선, 각, 직각, 삼각형·사각형·다각형, 원(중심·반지름·지름), 수직·평행, 대각선, 모눈 위 넓이·이동·대칭, 합동. 좌표가 곧 모양이므로 길이·각·평행·직각이 실제로 맞게 좌표를 고른다(이름표의 길이·각도와 모양이 어긋나지 않게) |
| (geo 공통 선택) | `max_unit`(슬라이드 1단위의 최대 인치 — 같은 도형을 여러 장에서 같은 크기로 그릴 때), `angles`의 `r`(부채꼴 반지름)·`label_dist`, 선분의 `color`·`width` | |
| `ruler` | `cm`(길이), `mm`?(false면 5 mm 눈금까지만), `start`?(첫 눈금 수), `objects`[ {from, to, label?} ](cm 단위, 자 위에 막대로) | 길이 재기(cm·mm). 활동지에서는 실제 크기(1 cm = 10 mm)로 인쇄된다 |
| `protractor` | `deg`?(잴 각), `base`?(밑변 방향, 기본 0), `scales`?(both·inner·outer), `step`?, `ray`?(변 길이, 기본 1.2), `mark`?(false면 각 표시 없음), `ws_radius`?(활동지 반지름 mm, 기본 45 — 두 개를 나란히 두려면 33) | 각도기로 각 재기. 안쪽(주황) 눈금은 오른쪽 0°, 바깥(파랑) 눈금은 왼쪽 0°. 넓은 자리(점 카드 없는 concept, `wide` 연습)에 두어야 10°마다 숫자가 나온다 |
| `chart` | `chart`, `labels`, `values`, `title`?, `valueTitle`?, `max`?, `min`?, `step`?(눈금 한 칸) | 그래프. 눈금 한 칸을 말하는 차시는 `step`을 꼭 준다. 물결선·칸 단위 그림이 필요하면 `geo`로 그린다 |
| `flow` | `items`[2~6], `cycle`?, `highlight`? | 과정·한살이·순환 |
| `timeline` | `events`[ {label, sub?} ] | 역사 흐름 |
| `letters` | `items`(글자), `sub`?(읽는 소리), `perRow`?, `highlight`? | 한글 자모·알파벳 |
| `words` | `items`[ {word, sub?, highlight?} ], `perRow`? | 낱말 카드(영어 낱말과 뜻 등) |
| `text` | `text`, `size`? | 큰 글자 하나(예: 오늘의 낱말) |

그림은 정확해야 한다. 칸 수·색칠 수·눈금·시각은 설명·정답과 같아야 하며, 분수 표기가 붙은 막대는 검사기가 색칠 비율을 대조한다.
사진·삽화는 쓰지 않는다(생성형 이미지는 수량·글자를 보장하지 못한다). 필요한 장면은 말과 도형으로 나타내고, 실물은 준비물로 쓴다.

영어 표현이 좁은 칸에서 중간에 줄이 바뀌지 않게 하려면 낱말 사이에 줄바꿈 없는 공백(`\u00a0`)을 쓴다(예: `"I'm\u00a0fine."`). 한글 없이 영어로만 된 글은 빌드할 때 영어(en-US)로 표시된다.

## 글의 양

빌드는 글이 상자에 들어가는지 계산하고 넘치면 실패한다. 처음부터 짧게 쓴다.

| 학년군 | 본문 | 한 줄 글자 수(본문, 전체 폭) | 카드 한 장 |
|---|---|---|---|
| 초1·2 (E12) | 32pt | 약 26자 | 1~2문장, 문장당 15자 안팎 |
| 초3·4 (E34) | 30pt | 약 28자 | 1~2문장 |
| 초5·6 (E56) | 28pt | 약 30자 | 2문장 이내 |

- 아이에게 보이는 문장은 해요체로, 짧게. 어려운 낱말은 쉬운 말로 풀거나 처음 나올 때 뜻을 함께 쓴다.
- 숫자와 단위가 줄바꿈으로 갈라지지 않게 문장을 고르거나 `\n` 으로 줄을 나눈다.
- 같은 내용을 화면과 노트에 반복하지 않는다. 화면은 아이용, 노트는 부모용이다.

## 정답 검산(checks)

수학 설명형 차시는 3개 이상 필수. 다른 과목도 계산이 있으면 넣는다.

```json
{ "type": "blank", "expr": "15 ÷ 5 = □", "answer": 3, "where": "S05 ①" }
{ "type": "blank", "expr": "2/3 = □/6", "answer": 4, "where": "S09 ①" }
{ "type": "equiv", "values": ["1/2", "2/4"], "where": "S06" }       // 대분수는 "2 3/5", 자연수는 "4"
{ "type": "compare", "values": ["3 + 1/5 − (1 + 3/5)", "1 + 3/5"], "rel": "=", "where": "S08" }   // 식 비교(− × ÷ 사용 가능)
{ "type": "not_equiv", "values": ["1/2", "2/3"], "where": "S10" }
{ "type": "bar", "slide": "S02", "parts": 4, "shaded": 1, "value": "1/4", "where": "S02 가" }
{ "type": "count", "slide": "S08", "value": 8, "where": "S08 ① 점 8개" }   // 점 배열·십 칸·격자·수 모형이 그 수를 나타내는지
{ "type": "compare", "values": ["58", "64"], "rel": "<", "where": "S09 ②" }   // 크기 비교(<, >, =)
{ "type": "bond", "whole": 7, "parts": [4, 3], "where": "S05 가르기" }
```

`blank` 의 식에는 정수·소수·분수(a/b)와 + − × ÷ ( ) 만 쓴다. □는 어디에 있어도 되며 정확한 분수 계산으로 검산한다(예: `"36 + 47 = □"`, `"0.3 + 0.45 = □"`, `"1/2 + 1/4 = □/4"`). 나머지가 있는 나눗셈은 `"□ × 4 + 3 = 23"` 처럼 곱셈식으로 쓴다.

## 활동지(worksheet)

`items`(2개 이상)마다 `no`, `prompt`, `answer`(부모용 정답·기준, 활동지에는 인쇄되지 않음)가 필수다.

| 필드 | 내용 |
|---|---|
| `eq` / `eqs` | 식(빈칸 있는 분수 포함) 하나 / 여러 개 |
| `bars` | 분수 막대 [ {parts, shaded, label?} ] |
| `clock`, `numberline`, `grid`, `array`, `pie`, `table`(`size`? pt), `tenframe`, `bond`, `geo`, `ruler`, `protractor` | 그림(시계는 h 없이 주면 아이가 바늘을 그린다, bond의 null은 빈 동그라미, geo·ruler·protractor는 슬라이드와 같은 필드이며 `type`은 쓰지 않는다. 그리기 문제는 `geo`에 `grid`와 `grid_range`[x0,y0,x1,y1]만 주어 빈 모눈·점판을 준다) |
| `read` | 읽을 글(상자) |
| `choices`, `choices_size`?(pt, 기본 12) | 고르기 보기(☐). 영어 낱말 읽기는 16 이상 |
| `big`, `big_size`?, `big_spacing`?(mm) | 큰 글자(따라 쓰기 낱말 등, 기본 26pt). 한글은 글자 사이를 4 mm 띄우고 영어는 붙여 쓴다. 한글 낱말 사이는 전각 공백(　)으로 띄운다 |
| `eng` | {`trace`[영어 문장…](흐린 글씨로 따라 쓰기), `blank`(빈 네 줄 수), `height`?(mm, 기본 15)} | 영어 네 줄 공책(셋째 줄이 기준선) |
| `lines` / `line_label` | 쓰기 줄 수 / 줄 앞 안내 |
| `box` | 그리기 칸 높이(mm) |
| `new_page`, `heading` | 새 쪽에서 시작, 쪽 제목(예: "다음 수업을 시작할 때") |

`record`: 부모용 안내 끝의 기록표 문장(예: "S10 혼자 해 보기: 모두 맞힘 □ 도움을 받아 해결 □").

## 견본

- 수학 설명형(좌표 블록): `lessons/G05_초5/MAT_수학/분수의성질/KR22-G05-MAT-FRAC-EQUIV-L01.json`
- 수학 설명형(kind): `lessons/G01_초1/MAT_수학/수와연산/KR22-G01-MAT-NUM9-L01.json`
- 국어 읽기(passage): `lessons/G03_초3/KOR_국어/읽기와어휘/KR22-G03-KOR-MAINIDEA-L01.json`
- 활동형(act): `lessons/G03_초3/ART_음악·미술/음악표현/KR22-G03-ART-BEATRHYTHM-L01.json`
