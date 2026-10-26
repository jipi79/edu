# 차시 묶음 제작 안내 (여러 작업자가 동시에 만들 때)

맥락: 학교 수업을 따라가기 어려운 아이를 부모가 집에서 1:1로 가르친다. 한 차시는 약 40분이다.
원본 JSON 하나에서 수업용 PPTX(부모용 노트 포함), 학생용 PPTX(정답 제거), 활동지 PDF, 부모용 안내 PDF가 만들어진다.
화면과 노트의 글은 모두 한국어다(영어 차시의 영어 표현은 제외).

## 먼저 읽을 것 (순서대로)

1. `SKILL.md`
2. `references/authoring.md` — 원본 형식(장 종류, 그림, 글의 양, 정답 검산, 활동지). 그대로 따른다.
3. `references/home-tutoring.md`, `references/lesson-design.md`
4. `references/subjects/` 의 해당 과목 파일
5. 맡은 차시 바로 앞의 완성된 차시(없으면 받은 견본). 구조, 아이용 화면 말투(짧은 해요체), 부모용 노트의 자세함을 맞춘다.
6. `plans/elementary/plan.json` 의 맡은 차시와 그 다음 차시(정리 장의 `next` 는 계획상 다음 차시 제목)

## 차시마다

1. `python3 -I tools/plan/new_lesson.py <ID>` — 뼈대 생성. id·title·grade·unit_folder·sequence·file_stem·curriculum·prerequisites는 고치지 않는다.
2. 작업 폴더에 내용 JSON(objectives, materials, boundary, misconceptions, checks, slides, worksheet, break_after(선택), `"status": "제작 완료"`)을 쓰고 `python3 -I tools/plan/fill_lesson.py <뼈대> <내용>` 으로 합친다.
3. `SOFFICE="<받은 명령>" tools/build_one.sh <원본>` — 실패하면 원고를 고쳐 통과할 때까지 다시 돌린다(글 넘침 → 줄이거나 장을 나눔).
4. `SOFFICE="<받은 명령>" python3 -I tools/preview.py <원본> <작업 폴더>/prev` — 미리보기 이미지를 모두 Read 도구로 본다. 넘침·겹침·잘림·숫자와 단위가 갈라진 줄바꿈·그림과 글/정답의 불일치를 고치고 다시 빌드한다.

## 지킬 것

- `tools/build.sh` 를 돌리지 않는다(목차·계획 현황은 묶음이 끝난 뒤 한 번에 갱신). 자기 차시 원본과 그 dist 출력 밖의 파일을 고치지 않는다. 도구·스킬 파일을 고치지 않는다. 커밋·푸시하지 않는다. 도구 문제는 원고로 우회하고 보고한다.
- 정확성이 먼저다. 해당 학년의 2022 개정 교육과정 수준, 계산 가능한 답은 모두 `checks`(수학은 3개 이상: blank·count·compare·bond·equiv), 그림의 수량은 글·정답과 같아야 한다.
- 목표 1~3개, 목표마다 teach·practice·check 장(검사기가 확인).
- 모든 장에 부모가 그대로 읽을 수 있는 노트: 목적, 시간, 말하기(따옴표 발문), 예상답/정답, 막히면, 주의. 시간 합계 약 40분.
- 선수 확인 장(role prior)과 보충 장(layout support, 절 "보충"). 보충 노트에 계획의 선수 차시 이름을 적는다.
- 아이가 보는 화면에는 정답을 쓰지 않는다. 정답 장(answers)은 teacher_only. 쓰기·말하기 과제는 정답 하나 대신 기준을 준다.
- 활동지 4문항 이상, 마지막은 새 쪽의 "다음 수업을 시작할 때" 복습, 문항마다 answer, 부모용 record 줄.
- 사진·삽화를 쓰지 않는다. 노래 가사·교과서·동화·시·작품 등 저작물을 옮기지 않는다(지문은 직접 쓴다). 집에 있는 물건(바둑돌, 단추, 종이 띠, 컵)을 준비물로 쓴다.
- 양을 나란히 비교하는 점 배열은 같은 `cell`, 수 모형은 같은 `unit` 을 준다. 가르기·모으기는 `bond` 그림을 쓴다.

## 보고

짧게: 완성한 ID(빌드 통과 + 미리보기 확인), 못 한 것과 이유, 부딪힌 도구 문제, 확인이 필요한 내용(계획의 빈틈, 사실 확인이 필요한 부분).
