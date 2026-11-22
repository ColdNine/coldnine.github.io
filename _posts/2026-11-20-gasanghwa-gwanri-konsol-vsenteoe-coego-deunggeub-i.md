---
layout: single
title: 가상화 관리 콘솔 v센터에 최고 등급 인증 우회 결함... 브로드컴, 긴급 업데이트 권고
date: 2026-11-20 11:25:00 +0900
categories: [boannews, incident]
tags: [결함, 센터, 공격, 브로드컴, 웨어, 인증, 업데이트]
source_url: https://www.boannews.com/news/articleView.html?idxno=147404
auto_generated: true
---

## Keywords
결함, 센터, 공격, 브로드컴, 웨어, 인증, 업데이트

## Summary
브로드컴이 VM웨어 v센터(vCenter)에서 인증을 건너뛸 수 있는 최고 등급 결함(CVE-2026-123890)을 고친 업데이트를 19일(현지시각) 내놨다. 브로드컴은 보안 권고에서 v센터의 VM웨어 디렉터리 서비스에 인증 우회 결함이 있어, 네트워크로 접근할 수 있는 공격자가 인증 없이 무단 접근할 수 있다고 밝혔다. 가상화 서버인 ESX 자체는 영향을 받지 않고, 이번 권고의 결함 어느 것도 가상머신 안에서 ESX 호스트의 코드를 실행하게 해 주지는 않는다. 모두 인증을 받았거나 이미 권한을 가진 공격자여야 악용할 수 있고, VM웨어 툴즈 결함은 게스트 별칭(Guest Alias) 매핑을 설정한 환경에서만 통한다.

---
*This post was automatically generated from [보안뉴스 사건·사고 section](https://www.boannews.com/news/articleList.html?sc_section_code=S1N2&view_type=sm). [Read original article →](https://www.boannews.com/news/articleView.html?idxno=147404)*
