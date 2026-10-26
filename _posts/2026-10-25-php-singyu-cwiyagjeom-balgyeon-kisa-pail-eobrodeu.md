---
layout: single
title: PHP 신규 취약점 발견…KISA, 파일 업로드 추적 기능 차단 권고
date: 2026-10-25 16:40:00 +0900
categories: [etnews, ai-sw]
tags: [취약점, 보안, 업데이트, 해결, 서버, 적용, 추가]
source_url: https://m.etnews.com/20261025000092
auto_generated: true
---

## Keywords
취약점, 보안, 업데이트, 해결, 서버, 적용, 추가

## Summary
25일 업계에 따르면 KISA는 지난 24일 보호나라를 통해 PHP 신규 취약점(CVE-2026-115560)에 대한 보안 권고문을 발표했다. PHP 개발팀은 지난 21일 취약점 2건을 해결하기 위해 버전별 보안 업데이트를 긴급 배포했다. 문제는 지난 21일 배포된 보안 업데이트(8.5.12·8.4.27·8.3.36·8.2.35)를 적용했더라도 신규 취약점은 해결되지 않는다는 점이다. KISA는 보안 업데이트가 나오기 전까지 PHP 설정에서 파일 업로드 진행 상황 추적 기능인 'session.upload_progress.enabled' 값을 0으로 변경하고, 모든 PHP 작업 프로세스를 재시작하도록 권고했다.

---
*This post was automatically generated from [ETNews AI/SW section](https://m.etnews.com/news/section.html?id1=04). [Read original article →](https://m.etnews.com/20261025000092)*
