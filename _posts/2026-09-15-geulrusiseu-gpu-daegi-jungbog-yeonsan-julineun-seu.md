---
layout: single
title: 글루시스, GPU 대기·중복 연산 줄이는 스토리지 기술 공개
date: 2026-09-15 09:20:00 +0900
categories: [etnews, ai-sw]
tags: [데이터, 스토리, 경로, 활용, 작업, 캐시, 반복]
source_url: https://m.etnews.com/20260915000034
auto_generated: true
---

## Keywords
데이터, 스토리, 경로, 활용, 작업, 캐시, 반복

## Summary
글루시스는 이에 따라 AI 스토리지를 GPU 뒤에서 데이터를 보관하는 장치가 아니라 AI 작업의 특성과 데이터 생명주기를 이해하는 데이터 인프라로 확장해야 한다고 강조했다. 대규모 학습 데이터셋과 체크포인트는 Lustre 기반 병렬 파일 데이터 경로(File Data Plane)를 적용하고, LLM 추론 과정에서 생성되는 KV 캐시와 상태 데이터는 DAOS 기반 분산 객체 데이터 경로(Object State Plane)를 적용하는 방식이다. 글루시스는 이번 결과가 단순한 저장장치 자체의 속도 차이가 아니라 KV 캐시 재사용과 다중 요청의 병렬 처리, 네트워크 및 스토리지 전송 경로 등 전체 소프트웨어 데이터 경로의 차이에서 나타난 것이라며, 향후 RAG, 다중 문서 질의응답, AI 에이전트 등 동일한 대규모 문맥(Context)을 여러 사용자와 GPU가 반복적으로 활용하는 AI 서비스에서 활용 가능성이 높을 것으로 기대했다. 글루시스 관계자는 “AI 인프라의 투자 효과를 높이려면 GPU가 데이터를 기다리는 시간과 같은 계산을 반복하는 부담을 함께 줄여야 한다”며 “글로벌 AI·HPC 생태계와 호환되는 데이터 경로 기술을 기반으로 고객이 기존 AI 인프라를 활용하면서 학습과 추론 성능을 단계적으로 높일 수 있는 AI 스토리지 플랫폼을 제공하겠다”고 말했다.

---
*This post was automatically generated from [ETNews AI/SW section](https://m.etnews.com/news/section.html?id1=04). [Read original article →](https://m.etnews.com/20260915000034)*
