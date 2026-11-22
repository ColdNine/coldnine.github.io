---
layout: single
title: PHP 치명적 결함 패치...특정 웹서버 설정 시 코드 실행 가능
date: 2026-11-20 10:02:00 +0900
categories: [boannews, incident]
tags: [결함, 설정, 요청, 업데이트, 버전, 개발, 연결]
source_url: https://www.boannews.com/news/articleView.html?idxno=147402
auto_generated: true
---

## Keywords
결함, 설정, 요청, 업데이트, 버전, 개발, 연결

## Summary
가장 심각한 결함은 웹서버 설정에 따라 로그인하지 않은 공격자가 요청 하나로 서버에서 PHP 코드를 실행할 수 있는 문제다. 앱이 요청 본문을 끝까지 읽지 않는 경우가 겹치면 공격자가 요청 하나로 PHP 코드를 실행할 수 있다. 변경 기록엔 세션 처리와 날짜·시간대, DOM, SOAP, CGI, PHAR 등 여러 구성 요소의 결함 수정도 함께 올라 있다. PHP 개발진은 당시 이 결함이 흔치 않은 설정과 앱 코드 조합에서만 나타난다며, 다음 정기 업데이트 전까지 session.upload_progress.enabled 값을 0으로 바꾸라고 권고했다.

---
*This post was automatically generated from [보안뉴스 사건·사고 section](https://www.boannews.com/news/articleList.html?sc_section_code=S1N2&view_type=sm). [Read original article →](https://www.boannews.com/news/articleView.html?idxno=147402)*
