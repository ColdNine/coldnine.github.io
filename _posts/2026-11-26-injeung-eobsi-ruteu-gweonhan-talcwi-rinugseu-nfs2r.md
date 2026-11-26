---
layout: single
title: 인증 없이 루트 권한 탈취... 리눅스 ‘NFS2ROOT’ 제로클릭 경보
date: 2026-11-26 11:45:00 +0900
categories: [boannews, incident]
tags: [커널, 서버, 공격, 실행, 바이트, 패치, 리눅스]
source_url: https://www.boannews.com/news/articleView.html?idxno=147562
auto_generated: true
---

## Keywords
커널, 서버, 공격, 실행, 바이트, 패치, 리눅스

## Summary
리눅스 커널 내장 네트워크 파일 시스템 서버(nfsd)에서 12년간 잠복해 온 원격 코드 실행 취약점 ‘NFS2ROOT’(CVE-2026-99362)가 공개됐다. 이 결함은 2014년 3월 코드 변경으로 리눅스 커널 3.16에 유입돼 12년간 장기지원(LTS)·배포판·어플라이언스 커널 전반에 남았다. 이에 오픈섹은 △운영 서버 커널 버전 △nfsd 모듈 적재 여부 △NFSv4.1·4.2 활성 상태 △2049 포트 개방 대역 등 4대 항목 점검을 권고했다. 오픈섹은 보안팀이 커널 로그의 nfsd4_check_resp_size 경고와 커널 워커의 비정상 셸 실행 흔적을 집중 감시해야 한다고 덧붙였다.

---
*This post was automatically generated from [보안뉴스 사건·사고 section](https://www.boannews.com/news/articleList.html?sc_section_code=S1N2&view_type=sm). [Read original article →](https://www.boannews.com/news/articleView.html?idxno=147562)*
