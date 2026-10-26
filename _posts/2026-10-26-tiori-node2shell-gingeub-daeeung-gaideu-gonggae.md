---
layout: single
title: 티오리, 'Node2Shell' 긴급 대응 가이드 공개
date: 2026-10-26 10:58:00 +0900
categories: [etnews, ai-sw]
tags: [취약점, 데이터, 압축, 오리, 과정, 메모리, 처리]
source_url: https://m.etnews.com/20261026000159
auto_generated: true
---

## Keywords
취약점, 데이터, 압축, 오리, 과정, 메모리, 처리

## Summary
티오리는 지난 21일 공개된 Node.js 보안 취약점 'Node2Shell(CVE-2026-111497)'을 자체 재현·검증하고 대응 가이드를 공개했다고 26일 밝혔다. 정상적인 압축 해제 과정에서는 잘못된 데이터 형식을 오류로 처리해야 하지만, 취약한 모듈은 일부 비정상 데이터를 제대로 걸러내지 못하고 처리를 계속하는 문제가 있다. 외부에서 전달된 악성 압축 데이터가 취약한 압축 해제 모듈까지 도달하는 경우에 공격이 성립할 수 있다. 임준오 티오리 AI & 사이버 리서치팀 총괄은 “개발자가 압축 기능을 직접 사용하지 않더라도 웹 프레임워크의 데이터 처리 과정에서 취약점에 노출될 수 있다”며 “임시 조치와 함께 최신 보안 패치를 적용해야 한다”고 말했다.

---
*This post was automatically generated from [ETNews AI/SW section](https://m.etnews.com/news/section.html?id1=04). [Read original article →](https://m.etnews.com/20261026000159)*
