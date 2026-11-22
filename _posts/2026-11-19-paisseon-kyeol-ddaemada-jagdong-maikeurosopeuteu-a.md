---
layout: single
title: 파이썬 켤 때마다 작동... 마이크로소프트 AI 에이전트 개발 패키지에 계정 탈취 코드
date: 2026-11-19 09:23:00 +0900
categories: [boannews, incident]
tags: [파일, 패키지, 배포, 정보, 버전, 에이전트, 파이썬]
source_url: https://www.boannews.com/news/articleView.html?idxno=147367
auto_generated: true
---

## Keywords
파일, 패키지, 배포, 정보, 버전, 에이전트, 파이썬

## Summary
악성 버전 두 개는 정식 배포 절차를 거쳤다는 출처 증명이 없었고, 이전과 달리 소스 배포본 없이 설치 파일만 올라왔다. 이어 마이크로소프트 클라우드 애저의 명령줄 도구와 pip·npm·깃·도커·허깅페이스 설정, 개발·배포 관리 서비스 애저 데브옵스의 에이전트 파일, .env 파일 등 인증 정보 파일을 최대 80개(1.26.1은 60개)까지 긁어 간다. 저장된 정보뿐 아니라, 애저에서 서버가 다른 서비스에 접속할 때 쓰는 관리 ID 토큰과 애저 데브옵스 인증 토큰을 그 자리에서 새로 발급받아 함께 보낸다. 이번엔 패키지 본체 파일을 깨끗한 상태로 되돌려 놓고 별도 파일 두 개에 악성코드를 숨겼다.

---
*This post was automatically generated from [보안뉴스 사건·사고 section](https://www.boannews.com/news/articleList.html?sc_section_code=S1N2&view_type=sm). [Read original article →](https://www.boannews.com/news/articleView.html?idxno=147367)*
