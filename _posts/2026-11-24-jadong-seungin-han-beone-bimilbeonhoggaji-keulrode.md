---
layout: single
title: 자동 승인 한 번에 비밀번호까지... 클로드 코드 설정 파일 1122개서 비밀 값 무더기 노출
date: 2026-11-24 13:30:00 +0900
categories: [boannews, incident]
tags: [파일, 장소, 명령, 구진, 클로드, 비밀번호, 저장]
source_url: https://www.boannews.com/news/articleView.html?idxno=147091
auto_generated: true
---

## Keywords
파일, 장소, 명령, 구진, 클로드, 비밀번호, 저장

## Summary
앤트로픽의 AI 코딩 도구 클로드 코드가 사용자가 승인한 명령을 비밀번호째 프로젝트 파일에 저장하고, 이 파일이 공개 깃허브 저장소로 올라가 비밀번호와 접속 키 같은 비밀 값 1379개가 노출됐다. 연구진이 추적한 저장소 1105곳 가운데 539곳에선 클로드가 공동 작성자로 표시된 커밋이 이 파일을 변경했다. 연구진은 파일을 정리하기 전에 그 파일에 담겼던 비밀 값부터 모두 교체하라고 권고했다. 저장소와 깃 기록에서 이 파일을 찾아내고, 로컬 파일을 추적에서 빼 .gitignore에 넣어야 한다.

---
*This post was automatically generated from [보안뉴스 사건·사고 section](https://www.boannews.com/news/articleList.html?sc_section_code=S1N2&view_type=sm). [Read original article →](https://www.boannews.com/news/articleView.html?idxno=147091)*
